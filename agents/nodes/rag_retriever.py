from django.conf import settings
from agents.state import AgentState
from vector_store.chroma_client import chroma_client
from apps.webtoons.models import Webtoon, UserWebtoonStatus
from apps.feed.models import FeedCycle

def retrieve_nearest_webtoons(state: AgentState) -> dict:
    user_id = state.get('user_id')
    prefs = state.get('cleaned_preferences_json', {})
    
    # 1. Build a text query from cleaned preference tokens
    genres_str = ", ".join(prefs.get('cleaned_genres', []))
    tones_str = ", ".join(prefs.get('tone_preferences', []))
    arts_str = ", ".join(prefs.get('art_style_preferences', []))
    dislikes_str = ", ".join(prefs.get('disliked_themes', []))
    
    query_text = (
        f"Prefer genres: {genres_str}. Tones: {tones_str}. "
        f"Art style: {arts_str}. Avoid themes: {dislikes_str}."
    )
    
    # 2. Query ChromaDB webtoon collection (get top 20 candidates)
    # We will expand limit dynamically if state's expansion_count is set
    expansion_factor = state.get('expansion_count', 0)
    top_k = 20
    if expansion_factor == 1:
        top_k = 40
    elif expansion_factor >= 2:
        top_k = 80
        
    candidates = chroma_client.query_webtoons(query_text, top_k=top_k)
    
    # Extract IDs of candidates
    candidate_ids = [c['id'] for c in candidates]
    
    # If ChromaDB returned empty or too few records, load active ones from database
    if len(candidate_ids) < 10:
        db_items = Webtoon.objects.filter(is_active=True).order_by('popularity_rank')[:top_k]
        candidate_ids = list(set(candidate_ids + [str(item.id) for item in db_items]))
        
    # Exclude webtoons that the user has already skipped/completed/read
    # Get user's logged statuses
    already_interacted = UserWebtoonStatus.objects.filter(
        user_id=user_id,
        status__in=['completed', 'skipped', 'reading']
    ).values_list('webtoon_id', flat=True)
    
    interacted_str_ids = [str(uid) for uid in already_interacted]
    filtered_ids = [cid for cid in candidate_ids if cid not in interacted_str_ids]
    
    # If filtered set is too small, fallback and allow skipped ones, or retrieve all active
    if len(filtered_ids) < 5:
        filtered_ids = candidate_ids[:20]
        
    print(f"RAG Retriever Node: Fetched {len(filtered_ids)} candidates (Expansion Factor: {expansion_factor}).")
    
    # Return top 20 candidate UUIDs to pass to the ranker
    return {
        "top_20_ids": filtered_ids[:20]
    }
