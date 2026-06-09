import os
import json
import datetime
import requests
from django.conf import settings
from agents.state import AgentState
from vector_store.chroma_client import chroma_client

def call_cerberus_api(system_prompt: str, user_prompt: str, json_mode: bool = True) -> str:
    api_key = getattr(settings, 'CERBERUS_API_KEY', 'mock_key')
    if api_key == 'mock_key' or not api_key:
        raise ValueError("Cerberus API Key is mock or unset.")
        
    url = "https://api.cerberusai.io/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "cerberus-l3-8b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2
    }
    if json_mode:
        data["response_format"] = {"type": "json_object"}
        
    resp = requests.post(url, headers=headers, json=data, timeout=15)
    if resp.status_code == 200:
        return resp.json()['choices'][0]['message']['content']
    else:
        raise Exception(f"Cerberus API returned {resp.status_code}: {resp.text}")

def extract_preferences_fallback(raw_input: str) -> dict:
    genres = ["action", "fantasy", "romance", "comedy", "slice of life", "thriller", "historical", "isekai", "sci-fi", "horror", "drama", "mystery", "superhero"]
    tones = ["slow burn", "dark", "comedy", "fluffy", "intense", "wholesome", "plot twists", "angst", "action-packed"]
    art_styles = ["vibrant", "detailed", "webtoon style", "sketchy", "pastel", "minimalist"]
    dislikes = ["gore", "mecha", "harem", "tragedy"]
    
    raw_lower = raw_input.lower()
    cleaned_genres = [g for g in genres if g in raw_lower]
    if not cleaned_genres:
        # Default fallback set
        cleaned_genres = ["fantasy", "romance"]
        
    tone_pref = [t for t in tones if t in raw_lower]
    art_pref = [a for a in art_styles if a in raw_lower]
    disliked = [d for d in dislikes if d in raw_lower]
    
    return {
        "cleaned_genres": cleaned_genres,
        "tone_preferences": tone_pref if tone_pref else ["adventurous"],
        "art_style_preferences": art_pref if art_pref else ["vibrant"],
        "disliked_themes": disliked
    }

def clean_onboarding_preferences(state: AgentState) -> dict:
    user_id = state.get('user_id')
    raw_input = state.get('raw_preferences')
    
    system_prompt = (
        "Extract genre, tone, art style, and disliked themes from the user's raw interest description. "
        "Return a JSON object with keys: cleaned_genres (array of strings), tone_preferences (array of strings), "
        "art_style_preferences (array of strings), disliked_themes (array of strings)."
    )
    user_prompt = f"User preference raw text: \"{raw_input}\""
    
    cleaned_data = {}
    try:
        content = call_cerberus_api(system_prompt, user_prompt, json_mode=True)
        cleaned_data = json.loads(content)
    except Exception as e:
        print(f"Cerberus onboarding preference cleaner error: {e}. Executing rule-based fallback.")
        cleaned_data = extract_preferences_fallback(raw_input)
        
    # Standardize output preferences payload
    preferences_obj = {
        "user_id": user_id,
        "raw_input": raw_input,
        "cleaned_genres": cleaned_data.get("cleaned_genres", ["fantasy"]),
        "tone_preferences": cleaned_data.get("tone_preferences", ["vibrant"]),
        "art_style_preferences": cleaned_data.get("art_style_preferences", ["webtoon"]),
        "disliked_themes": cleaned_data.get("disliked_themes", []),
        "vector_embedding_id": f"pref_{user_id}",
        "last_updated": datetime.datetime.utcnow().isoformat()
    }
    
    # Save preferences.json to media/users/{user_id}/
    user_dir = os.path.join(settings.MEDIA_ROOT, 'users', user_id)
    os.makedirs(user_dir, exist_ok=True)
    pref_filepath = os.path.join(user_dir, 'preferences.json')
    with open(pref_filepath, 'w', encoding='utf-8') as f:
        json.dump(preferences_obj, f, indent=2)
        
    # Write to database (context memory collection in ChromaDB)
    chroma_client.upsert_context_memory(
        doc_id=f"pref_{user_id}",
        text=json.dumps(preferences_obj),
        metadata={"user_id": user_id, "type": "preference"}
    )
    
    # Update Django User onboarding status
    from apps.auth_core.models import SpellUser
    try:
        user = SpellUser.objects.get(id=user_id)
        user.onboarding_complete = True
        user.save()
    except Exception as e:
        print(f"Error updating User onboarding status: {e}")
        
    return {
        "cleaned_preferences_json": preferences_obj
    }
