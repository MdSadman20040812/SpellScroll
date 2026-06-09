import os
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from api.auth import get_current_user
from apps.webtoons.models import Webtoon, UserWebtoonStatus
from apps.feed.models import FeedCycle
from django.conf import settings
from channels.layers import get_channel_layer
from agents.nodes.feedback_updater import update_user_feedback
from agents.graph import get_agent_graph

router = APIRouter()

class FeedbackRequest(BaseModel):
    webtoon_id: str
    status: str  # suggested/reading/completed/skipped
    rating: Optional[int] = None  # 1-5 rating
    feedback_note: Optional[str] = ""

def serialize_webtoons(webtoon_ids: List[str], user_id: str) -> List[dict]:
    """
    Serializer helper that pulls Webtoon objects and constructs the card payload.
    Includes custom reason cached in context memory if available.
    """
    from vector_store.chroma_client import chroma_client
    
    webtoons = Webtoon.objects.filter(id__in=webtoon_ids)
    # Maintain the order of webtoon_ids
    webtoons_map = {str(w.id): w for w in webtoons}
    
    serialized = []
    for wid in webtoon_ids:
        w = webtoons_map.get(wid)
        if not w:
            continue
            
        # Try to retrieve recommendation reason from vector context store
        reason = "Recommended for you."
        try:
            contexts = chroma_client.query_context_memory(f"reason_{user_id}_{wid}", top_k=1)
            if contexts:
                reason = contexts[0]['document']
        except Exception:
            pass
            
        # Get active status if exists
        user_status = UserWebtoonStatus.objects.filter(user_id=user_id, webtoon_id=wid).first()
        status_val = user_status.status if user_status else "suggested"
        
        serialized.append({
            "id": str(w.id),
            "title": w.title,
            "slug": w.slug,
            "genres": w.genres,
            "colour_rating": w.colour_rating,
            "mangadex_id": w.mangadex_id,
            "synopsis": w.synopsis_200w,
            "cover_url": w.cover_url,
            "source_url": w.source_url,
            "reason": reason,
            "status": status_val
        })
    return serialized

@router.get("/current")
async def get_current_feed(user = Depends(get_current_user)):
    user_id_str = str(user.id)
    
    # Get latest FeedCycle for the user
    latest_cycle = FeedCycle.objects.filter(user=user).order_by('-created_at').first()
    
    if not latest_cycle:
        # If no cycle, run the LangGraph pipeline to generate recommendations on-the-fly
        # We read raw_preferences from the saved preferences.json
        pref_filepath = os.path.join(settings.MEDIA_ROOT, 'users', user_id_str, 'preferences.json')
        raw_text = "I like colorful stories."
        if os.path.exists(pref_filepath):
            try:
                with open(pref_filepath, 'r', encoding='utf-8') as f:
                    raw_text = json.load(f).get('raw_input', raw_text)
            except Exception:
                pass
                
        try:
            graph = get_agent_graph()
            result = graph.invoke({
                "user_id": user_id_str,
                "raw_preferences": raw_text,
                "feed_cycle_number": 1
            })
            suggested_ids = result.get("top_20_ids", [])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate feed: {str(e)}")
    else:
        suggested_ids = latest_cycle.webtoons_suggested
        
    webtoon_cards = serialize_webtoons(suggested_ids, user_id_str)
    return {"cycle_number": latest_cycle.cycle_number if latest_cycle else 1, "webtoons": webtoon_cards}

@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest, user = Depends(get_current_user)):
    user_id_str = str(user.id)
    
    try:
        webtoon = Webtoon.objects.get(id=req.webtoon_id)
    except Webtoon.DoesNotExist:
        raise HTTPException(status_code=404, detail="Webtoon not found")
        
    # 1. Update/create UserWebtoonStatus
    status_obj, created = UserWebtoonStatus.objects.update_or_create(
        user=user,
        webtoon=webtoon,
        defaults={
            "status": req.status,
            "user_rating": req.rating,
            "feedback_note": req.feedback_note
        }
    )
    
    # 2. Trigger taste profile updates (LangGraph preference cleaner feedback loop)
    updated_prefs = update_user_feedback(
        user_id=user_id_str,
        webtoon_id=req.webtoon_id,
        rating=req.rating or 3,
        note=req.feedback_note or ""
    )
    
    # 3. Broadcast status update through Django Channels Group
    channel_layer = get_channel_layer()
    if channel_layer:
        try:
            await channel_layer.group_send(
                f"feed_{user_id_str}",
                {
                    "type": "preference.updated",
                    "preferences": updated_prefs
                }
            )
        except Exception as ws_err:
            print(f"WS broadcast warning: {ws_err}")
            
    return {
        "status": "success",
        "message": f"Feedback updated for {webtoon.title}",
        "preferences": updated_prefs
    }

@router.post("/expand")
async def trigger_feed_expansion(user = Depends(get_current_user)):
    user_id_str = str(user.id)
    
    # Query current cycle number
    latest_cycle = FeedCycle.objects.filter(user=user).order_by('-created_at').first()
    next_cycle_num = (latest_cycle.cycle_number + 1) if latest_cycle else 1
    
    # Re-retrieve preferences raw input
    pref_filepath = os.path.join(settings.MEDIA_ROOT, 'users', user_id_str, 'preferences.json')
    raw_text = "I like colorful stories."
    if os.path.exists(pref_filepath):
        try:
            with open(pref_filepath, 'r', encoding='utf-8') as f:
                raw_text = json.load(f).get('raw_input', raw_text)
        except Exception:
            pass
            
    try:
        # Run graph execution, incrementing expansion count
        graph = get_agent_graph()
        result = graph.invoke({
            "user_id": user_id_str,
            "raw_preferences": raw_text,
            "feed_cycle_number": next_cycle_num,
            "expansion_count": (latest_cycle.cycle_number if latest_cycle else 1)
        })
        suggested_ids = result.get("top_20_ids", [])
        
        webtoon_cards = serialize_webtoons(suggested_ids, user_id_str)
        
        # Broadcast the new feed to WebSocket channel
        channel_layer = get_channel_layer()
        if channel_layer:
            await channel_layer.group_send(
                f"feed_{user_id_str}",
                {
                    "type": "feed.update",
                    "webtoons": webtoon_cards
                }
            )
            
        return {"status": "success", "cycle_number": next_cycle_num, "webtoons": webtoon_cards}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to expand feed: {str(e)}")
