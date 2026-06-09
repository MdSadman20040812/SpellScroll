import json
from django.conf import settings
from agents.state import AgentState
from agents.nodes.preference_cleaner import call_cerberus_api
from apps.webtoons.models import Webtoon
from apps.feed.models import FeedCycle

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

def rank_webtoons_node(state: AgentState) -> dict:
    user_id = state.get('user_id')
    top_20_ids = state.get('top_20_ids', [])
    prefs = state.get('cleaned_preferences_json', {})
    cycle_num = state.get('feed_cycle_number', 1)
    
    if not top_20_ids:
        return {"top_20_ids": []}
        
    candidates = Webtoon.objects.filter(id__in=top_20_ids)
    
    system_prompt = (
        "You are an expert webtoon personalization ranker. "
        "Your task is to rank the webtoons based on user interests. "
        "Return a JSON array of objects, each with 'id' (string), 'rank' (integer), "
        "and 'reason' (string, maximum 50 words explaining how it fits the user profile)."
    )
    
    webtoons_to_rank_list = []
    for item in candidates:
        webtoons_to_rank_list.append({
            "id": str(item.id),
            "title": item.title,
            "genres": item.genres,
            "synopsis": item.synopsis_200w[:150]
        })
        
    user_prompt = f"User Interests: {json.dumps(prefs)}\nWebtoons list to rank: {json.dumps(webtoons_to_rank_list)}"
    
    ranked_results = []
    try:
        content = call_cerberus_api(system_prompt, user_prompt, json_mode=True)
        # Verify JSON
        data = json.loads(content)
        if isinstance(data, dict) and "rankings" in data:
            ranked_results = data["rankings"]
        elif isinstance(data, list):
            ranked_results = data
        else:
            raise ValueError("Malformed response format")
    except Exception as e:
        print(f"Cerberus Ranker Node error: {e}. Executing local fallback scoring.")
        ranked_results = calculate_local_ranking(prefs, candidates)
        
    # Map ranked IDs
    ranked_ids = [item["id"] for item in sorted(ranked_results, key=lambda x: x.get("rank", 99))]
    
    # Make sure we didn't miss any IDs in output
    for cid in top_20_ids:
        if cid not in ranked_ids:
            ranked_ids.append(cid)
            
    # Save FeedCycle record in SQL
    try:
        FeedCycle.objects.create(
            user_id=user_id,
            cycle_number=cycle_num,
            webtoons_suggested=ranked_ids,
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
