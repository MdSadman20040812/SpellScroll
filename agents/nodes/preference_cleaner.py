import os
import json
import datetime
import requests
from django.conf import settings
from agents.state import AgentState
from vector_store.chroma_client import chroma_client

def call_cerebras_api(system_prompt: str, user_prompt: str, json_mode: bool = True) -> str:
    """Call the configured LLM provider.

    Kept under its original name because several nodes import it. The Cerebras
    endpoint is no longer hardcoded: services.llm dispatches to whichever
    free-tier provider is configured (Groq, Gemini, OpenRouter, Cerebras), and
    raises when none is, so callers drop to their local fallback.
    """
    from services.llm import LLMUnavailable, chat

    try:
        return chat(system_prompt, user_prompt, json_mode=json_mode)
    except LLMUnavailable as exc:
        # Callers catch broad exceptions and fall back to local ranking.
        raise ValueError(str(exc))


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
    
    # The vocabulary is constrained on purpose: these values are matched against
    # normalised provider genres (services/metadata.py) and rendered as chips on
    # the profile page, so free-form phrasing like "murim cultivation vibes"
    # would neither match nor read well as a tag.
    system_prompt = (
        "You read a description of what someone likes to read and turn it into "
        "a structured taste profile.\n"
        "\n"
        "Return JSON with exactly these keys, each an array of short lowercase "
        "strings:\n"
        "  cleaned_genres        - standard genre words only: action, adventure, "
        "romance, fantasy, drama, comedy, horror, thriller, mystery, "
        "psychological, supernatural, sci-fi, historical, sports, "
        "slice of life, isekai, martial arts\n"
        "  tone_preferences      - how it should feel: slow burn, dark, "
        "wholesome, intense, emotional, lighthearted, tense, hopeful\n"
        "  art_style_preferences - how it should look: vibrant, detailed, "
        "high contrast, soft, painterly, clean, expressive\n"
        "  disliked_themes       - anything they said they avoid or dislike\n"
        "\n"
        "Rules:\n"
        "- Infer, do not just keyword-match. \"cultivation\" and \"murim\" imply "
        "martial arts and fantasy; \"gets under my skin\" implies psychological.\n"
        "- 2-5 entries per array. Prefer the words above; only invent one when "
        "nothing fits.\n"
        "- Put anything they dislike ONLY in disliked_themes, never in the "
        "positive arrays. This is the most common mistake — read the sentence "
        "for negation (\"I bounce off\", \"I hate\", \"not into\") carefully.\n"
        "- Leave an array empty rather than padding it with guesses."
    )
    user_prompt = f'In their own words: "{raw_input}"'
    
    cleaned_data = {}
    try:
        content = call_cerebras_api(system_prompt, user_prompt, json_mode=True)
        cleaned_data = json.loads(content)
    except Exception as e:
        print(f"Cerebras onboarding preference cleaner error: {e}. Executing rule-based fallback.")
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
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
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
