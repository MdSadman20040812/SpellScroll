import json
from django.conf import settings
from agents.state import AgentState
from agents.nodes.preference_cleaner import call_cerebras_api
from apps.webtoons.models import Webtoon
from apps.feed.models import FeedCycle
from vector_store.chroma_client import chroma_client

def calculate_local_ranking(prefs: dict, candidates: list) -> list:
    """
    Fallback deterministic ranking algorithm.
    Calculates score based on genre overlap, popularity, and color rating.
    """
    preferred_genres = set([g.lower() for g in prefs.get('cleaned_genres', [])])
    disliked_themes = set([d.lower() for d in prefs.get('disliked_themes', [])])
    
    ranked_list = []
    for item in candidates:
        item_genres = [g.lower() for g in (item.genres if isinstance(item.genres, list) else [])]
        item_genres_set = set(item_genres)
        
        # Genre match score (Jaccard similarity)
        intersection = preferred_genres.intersection(item_genres_set)
        union = preferred_genres.union(item_genres_set)
        genre_score = len(intersection) / len(union) if union else 0.0
        
        # Disliked check
        penalty = 0.0
        if disliked_themes.intersection(item_genres_set):
            penalty = 0.8
            
        # Color rating and popularity scores
        # popularity_rank: lower is better (e.g. 1 is best)
        pop_score = max(0, 1.0 - (item.popularity_rank / 100.0))
        color_score = item.colour_rating
        
        # Combined score
        final_score = (genre_score * 0.5) + (pop_score * 0.2) + (color_score * 0.3) - penalty
        
        # Match reason
        genre_matches = list(intersection)
        if genre_matches:
            reason = f"Matches your interest in {', '.join(genre_matches[:2])}. Highly rated for its vibrant colorful styling."
        else:
            reason = "A highly popular colorful webtoon that matches the tone of your preferred styles."
            
        ranked_list.append({
            "id": str(item.id),
            "score": final_score,
            "reason": reason
        })
        
    # Sort descending by score
    ranked_list = sorted(ranked_list, key=lambda x: x["score"], reverse=True)
    
    # Format with ranks
    output = []
    for idx, r in enumerate(ranked_list):
        output.append({
            "id": r["id"],
            "rank": idx + 1,
            "reason": r["reason"]
        })
    return output

def _llm_rank(prefs: dict, candidates: list) -> list:
    """Ask the model to rank candidates, returning [{id, rank, reason}, ...].

    Candidates are addressed by a small integer index, never by their UUID.
    Models garble or invent long opaque identifiers, and the previous version
    trusted whatever ``id`` string came back - so rationales were keyed to
    non-existent webtoons and ended up displayed against the wrong series.
    Indices are cheap to echo correctly, and anything unrecognised is dropped
    rather than guessed at.
    """
    listing = [
        {
            "i": index,
            "title": item.title,
            "genres": (item.genres or [])[:5],
            "synopsis": (item.synopsis_200w or "")[:150],
        }
        for index, item in enumerate(candidates)
    ]

    system_prompt = (
        "You are a well-read friend recommending webtoons — someone with real "
        "opinions, not a blurb generator.\n"
        "\n"
        "You get a reader's taste profile and a numbered list of candidates. "
        "Rank them and say why each one fits.\n"
        "\n"
        "How to write a reason:\n"
        "- Talk TO the reader, in second person. \"You'll like...\", \"This one earns...\"\n"
        "- One or two sentences, under 30 words. No preamble.\n"
        "- Be specific to THIS story — its premise, tone or art. Never generic "
        "praise like \"a highly rated colourful webtoon\".\n"
        "- Connect it to something they actually said they wanted, and name that "
        "thing in plain words rather than echoing their profile back verbatim.\n"
        "- If it only partly fits, say so honestly — \"lighter than your usual, "
        "but the art is worth it\" beats overselling.\n"
        "- Vary how you open. Do not start every reason the same way.\n"
        "- No markdown, no emoji, no quotation marks around the whole reason.\n"
        "\n"
        "Return JSON: {\"rankings\": [{\"i\": <the candidate's integer index>, "
        "\"rank\": <1 = best>, \"reason\": <your sentence>}]}. "
        "Include every candidate exactly once. Never invent an index. "
        "Each reason must describe the title at that index and name no other title."
    )
    user_prompt = "Taste profile: {0}\nCandidates: {1}".format(
        json.dumps(prefs), json.dumps(listing)
    )

    content = call_cerebras_api(system_prompt, user_prompt, json_mode=True)
    data = json.loads(content)
    rows = data.get("rankings") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError("Malformed ranker response")

    ranked = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            index = int(row.get("i"))
        except (TypeError, ValueError):
            continue
        # Only indices the model was actually given, and only once each.
        if index < 0 or index >= len(candidates) or index in seen:
            continue
        seen.add(index)
        reason = str(row.get("reason") or "").strip()
        ranked.append(
            {
                "id": str(candidates[index].id),
                "rank": row.get("rank", len(ranked) + 1),
                "reason": reason or "Matched to your taste signature.",
            }
        )

    if not ranked:
        raise ValueError("Ranker returned no usable rows")
    return ranked


def rank_webtoons_node(state: AgentState) -> dict:
    user_id = state.get('user_id')
    top_20_ids = state.get('top_20_ids', [])
    prefs = state.get('cleaned_preferences_json', {})
    cycle_num = state.get('feed_cycle_number', 1)

    if not top_20_ids:
        return {"top_20_ids": []}

    # Preserve the retriever's ordering; a queryset does not guarantee it.
    by_id = {str(w.id): w for w in Webtoon.objects.filter(id__in=top_20_ids)}
    candidates = [by_id[wid] for wid in top_20_ids if wid in by_id]
    if not candidates:
        return {"top_20_ids": []}

    try:
        ranked_results = _llm_rank(prefs, candidates)
    except Exception as e:
        print(f"LLM ranker unavailable ({e}); using local scoring.")
        ranked_results = calculate_local_ranking(prefs, candidates)

    # Anything the model omitted keeps its retrieval order at the tail, and is
    # given the local explanation rather than a generic placeholder.
    covered = {r["id"] for r in ranked_results}
    if len(covered) < len(candidates):
        local = {r["id"]: r for r in calculate_local_ranking(prefs, candidates)}
        next_rank = len(ranked_results) + 1
        for webtoon in candidates:
            wid = str(webtoon.id)
            if wid not in covered:
                fallback = local.get(wid, {})
                ranked_results.append(
                    {
                        "id": wid,
                        "rank": next_rank,
                        "reason": fallback.get("reason", "Matched to your taste signature."),
                    }
                )
                next_rank += 1

    ranked_ids = [r["id"] for r in sorted(ranked_results, key=lambda x: x.get("rank", 99))]

    # Rationale per webtoon, persisted alongside the cycle.
    reasons = {
        r["id"]: r.get("reason", "Recommended for your taste signature.")
        for r in ranked_results
        if r.get("id")
    }

    # Save FeedCycle record in SQL
    try:
        FeedCycle.objects.create(
            user_id=user_id,
            cycle_number=cycle_num,
            webtoons_suggested=ranked_ids,
            reasons=reasons,
            all_skipped=False,
            fallback_triggered=(len(candidates) == 0)
        )
    except Exception as e:
        print(f"Error saving FeedCycle: {e}")
        
    # Inject reasons into context memory to query in details view
    for r in ranked_results:
        # Cache recommendation reasons in vector context window DB for instant lookup
        chroma_client.upsert_context_memory(
            doc_id=f"reason_{user_id}_{r['id']}",
            text=r.get("reason", "Highly recommended colorful webtoon."),
            metadata={"user_id": user_id, "webtoon_id": r['id'], "type": "reason"}
        )
        
    return {
        "top_20_ids": ranked_ids
    }
