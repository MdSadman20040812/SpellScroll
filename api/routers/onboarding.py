import logging

from asgiref.sync import sync_to_async
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from agents.graph import get_agent_graph
from api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class PreferenceRequest(BaseModel):
    preferences: str = Field(min_length=10, max_length=2000)


@router.post("/preferences")
async def submit_preferences(req: PreferenceRequest, user=Depends(get_current_user)):
    """Turn free-text preferences into a stored taste signature and first feed.

    The graph runs Django ORM queries and blocking provider calls, so it must
    be handed to a worker thread.  Calling ``graph.invoke`` directly from this
    async route raised ``SynchronousOnlyOperation`` and every onboarding
    attempt failed with "You cannot call this from an async context".
    """
    try:
        result = await sync_to_async(get_agent_graph().invoke)(
            {
                "user_id": str(user.id),
                "raw_preferences": req.preferences.strip(),
                "feed_cycle_number": 1,
            }
        )
    except Exception as exc:
        logger.exception("onboarding pipeline failed")
        raise HTTPException(
            status_code=503,
            detail="Could not build your taste signature: {0}".format(exc),
        )

    return {
        "status": "success",
        "message": "Preferences processed successfully.",
        "preferences": result.get("cleaned_preferences_json", {}),
        "suggested_count": len(result.get("top_20_ids", [])),
    }
