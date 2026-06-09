from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from api.auth import get_current_user
from agents.graph import get_agent_graph

router = APIRouter()

class PreferenceRequest(BaseModel):
    preferences: str

@router.post("/preferences")
async def submit_preferences(req: PreferenceRequest, user = Depends(get_current_user)):
    try:
        graph = get_agent_graph()
        result = graph.invoke({
            "user_id": str(user.id),
            "raw_preferences": req.preferences,
            "feed_cycle_number": 1
        })
        return {
            "status": "success",
            "message": "Preferences processed successfully.",
            "preferences": result.get("cleaned_preferences_json", {})
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Onboarding error: {str(e)}")
