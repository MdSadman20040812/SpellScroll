from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Optional
from api.auth import get_current_admin
from apps.auth_core.models import SpellUser
from apps.webtoons.models import Webtoon
from apps.feed.models import FeedCycle, AppOperatingCycle
from vector_store.chroma_client import reset_chroma_collections
from agents.nodes.webtoon_scraper import scrape_and_update_universe
from asgiref.sync import sync_to_async

router = APIRouter()

def _get_users():
    return list(SpellUser.objects.all().order_by('-created_at'))

def _get_webtoons_admin():
    return list(Webtoon.objects.all().order_by('popularity_rank')[:50])

def _get_cycles():
    return list(FeedCycle.objects.all().order_by('-created_at'))

def _get_op_cycles():
    return list(AppOperatingCycle.objects.all().order_by('-timestamp')[:20])

def _get_webtoon(pk):
    return Webtoon.objects.get(pk=pk)

def _update_webtoon_sync(w, **kwargs):
    for field, value in kwargs.items():
        if value is not None:
            setattr(w, field, value)
    w.save()

@router.get("/users")
async def get_users_list(admin = Depends(get_current_admin)):
    users = await sync_to_async(_get_users)()
    return [{
        "id": str(u.id),
        "username": u.username,
        "email": u.email,
        "display_name": u.display_name,
        "onboarding_complete": u.onboarding_complete,
        "created_at": u.created_at
    } for u in users]

@router.post("/scrape/trigger")
async def trigger_full_scrape(admin = Depends(get_current_admin)):
    try:
        count = await sync_to_async(scrape_and_update_universe)()
        return {"status": "success", "message": f"Universe updated with {count} active webtoons."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping error: {str(e)}")

@router.patch("/webtoons/{webtoon_id}")
async def edit_webtoon_record(
    webtoon_id: str,
    title: Optional[str] = Body(None),
    genres: Optional[List[str]] = Body(None),
    colour_rating: Optional[float] = Body(None),
    synopsis: Optional[str] = Body(None),
    is_active: Optional[bool] = Body(None),
    admin = Depends(get_current_admin),
):
    try:
        w = await sync_to_async(_get_webtoon)(webtoon_id)
    except Webtoon.DoesNotExist:
        raise HTTPException(status_code=404, detail="Webtoon not found")
        
    await sync_to_async(_update_webtoon_sync)(
        w,
        title=title,
        genres=genres,
        colour_rating=colour_rating,
        synopsis_200w=synopsis,
        is_active=is_active,
    )
    return {"status": "success", "message": f"Webtoon {w.title} updated successfully."}

@router.get("/cycles")
async def get_operating_cycles(admin = Depends(get_current_admin)):
    cycles = await sync_to_async(_get_cycles)()
    return [{
        "id": c.id,
        "user": c.user.username,
        "cycle_number": c.cycle_number,
        "webtoons_suggested": c.webtoons_suggested,
        "created_at": c.created_at
    } for c in cycles]

@router.delete("/chroma/reset")
async def reset_chroma_store(admin = Depends(get_current_admin)):
    try:
        await sync_to_async(reset_chroma_collections)()
        return {"status": "success", "message": "ChromaDB collections reset successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset error: {str(e)}")
