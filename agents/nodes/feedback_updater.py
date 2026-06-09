import os
import json
import datetime
from django.conf import settings
from agents.state import AgentState
from agents.nodes.preference_cleaner import call_cerberus_api
from vector_store.chroma_client import chroma_client
from apps.webtoons.models import Webtoon

def local_feedback_merge(prefs: dict, title: str, genres: list, rating: int, note: str) -> dict:
    """
    Fallback deterministic feedback merger.
    Reinforces preferences if high rating, adds warnings if low rating.
    """
    cleaned_genres = prefs.get('cleaned_genres', [])
    disliked_themes = prefs.get('disliked_themes', [])
    tone_preferences = prefs.get('tone_preferences', [])
    
    # Rating: 4 or 5 is positive, 1 or 2 is negative
    if rating >= 4:
        # Reinforce genres
        for g in genres:
            if g not in cleaned_genres:
                cleaned_genres.append(g)
        # Parse potential tone words from note
        note_lower = note.lower()
        for tone in ["slow burn", "dark", "wholesome", "intense", "plot twists", "action-packed"]:
            if tone in note_lower and tone not in tone_preferences:
                tone_preferences.append(tone)
    elif rating <= 2:
        # Add primary genre to dislikes if user strongly disliked it
        if genres:
            primary_genre = genres[0]
            if primary_genre not in disliked_themes:
                disliked_themes.append(primary_genre)
                
    return {
        "cleaned_genres": cleaned_genres,
        "tone_preferences": tone_preferences,
        "art_style_preferences": prefs.get('art_style_preferences', ["vibrant"]),
        "disliked_themes": disliked_themes
    }

def update_user_feedback(user_id: str, webtoon_id: str, rating: int, note: str) -> dict:
    """
    Loads preferences.json, submits to Cerberus or local merge, saves, and re-embeds.
    """
    # 1. Load preferences
    user_dir = os.path.join(settings.MEDIA_ROOT, 'users', user_id)
    pref_filepath = os.path.join(user_dir, 'preferences.json')
    
    prefs = {}
    if os.path.exists(pref_filepath):
        try:
            with open(pref_filepath, 'r', encoding='utf-8') as f:
                prefs = json.load(f)
        except Exception as e:
            print(f"Error reading preference file: {e}")
            
    if not prefs:
        prefs = {
            "user_id": user_id,
            "cleaned_genres": ["fantasy"],
            "tone_preferences": ["adventurous"],
            "art_style_preferences": ["vibrant"],
            "disliked_themes": []
        }
        
    # Get webtoon details
    try:
        webtoon = Webtoon.objects.get(id=webtoon_id)
        webtoon_title = webtoon.title
        webtoon_genres = webtoon.genres if isinstance(webtoon.genres, list) else []
        webtoon_synopsis = webtoon.synopsis_200w
    except Exception as e:
        print(f"Webtoon not found: {e}")
        return prefs
        
    # 2. Build prompts
    system_prompt = (
        "You are a user profiling intelligence node. "
        "Update the user taste profile based on their interaction with a webtoon. "
        "Review the rating (1-5) and comment, adjust preferred genres, tones, art styles, and disliked themes. "
        "Return a JSON object containing keys: cleaned_genres (array), tone_preferences (array), "
        "art_style_preferences (array), disliked_themes (array)."
    )
    user_prompt = (
        f"Current Taste Profile: {json.dumps(prefs)}\n"
        f"Interacted Webtoon: '{webtoon_title}' (Genres: {webtoon_genres}, Synopsis: {webtoon_synopsis})\n"
        f"User feedback rating: {rating}/5, Note: \"{note}\""
    )
    
    updated_profile = {}
    try:
        content = call_cerberus_api(system_prompt, user_prompt, json_mode=True)
        updated_profile = json.loads(content)
    except Exception as e:
        print(f"Feedback updater error: {e}. Executing rule-based reinforcement merge.")
        updated_profile = local_feedback_merge(prefs, webtoon_title, webtoon_genres, rating, note)
        
    # Merge back into pref object
    prefs["cleaned_genres"] = updated_profile.get("cleaned_genres", prefs.get("cleaned_genres", ["fantasy"]))
    prefs["tone_preferences"] = updated_profile.get("tone_preferences", prefs.get("tone_preferences", ["adventurous"]))
    prefs["art_style_preferences"] = updated_profile.get("art_style_preferences", prefs.get("art_style_preferences", ["vibrant"]))
    prefs["disliked_themes"] = updated_profile.get("disliked_themes", prefs.get("disliked_themes", []))
    prefs["last_updated"] = datetime.datetime.utcnow().isoformat()
    
    # Save back to file
    os.makedirs(user_dir, exist_ok=True)
    with open(pref_filepath, 'w', encoding='utf-8') as f:
        json.dump(prefs, f, indent=2)
        
    # Re-embed in ChromaDB context memory
    chroma_client.upsert_context_memory(
        doc_id=f"pref_{user_id}",
        text=json.dumps(prefs),
        metadata={"user_id": user_id, "type": "preference"}
    )
    
    return prefs
