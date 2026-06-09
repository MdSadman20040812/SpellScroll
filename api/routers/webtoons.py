from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from api.auth import get_current_user
from apps.webtoons.models import Webtoon, UserWebtoonStatus

router = APIRouter()

@router.get("/")
async def get_webtoons_list(
    genre: Optional[str] = Query(None, description="Filter catalog by genre keyword"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(12, ge=1, le=50, description="Items per page"),
    user = Depends(get_current_user)
):
    queryset = Webtoon.objects.filter(is_active=True)
    
    if genre:
        # Check if the genre matches list elements in sqlite json
        # Since we use JSONField in SQLite, we filter inside list
        # A simple check: search for the genre text inside the JSON field string or filter programmatically
        # Let's retrieve all and filter to guarantee cross-DB compatibility
        filtered = []
        for item in queryset:
            genres = [g.lower() for g in (item.genres if isinstance(item.genres, list) else [])]
            if genre.lower() in genres:
                filtered.append(item)
        queryset_list = filtered
    else:
        queryset_list = list(queryset.order_by('popularity_rank'))
        
    # Manual Pagination
    total = len(queryset_list)
    start = (page - 1) * limit
    end = start + limit
    paginated = queryset_list[start:end]
    
    serialized = []
    for w in paginated:
        serialized.append({
            "id": str(w.id),
            "title": w.title,
            "slug": w.slug,
            "genres": w.genres,
            "colour_rating": w.colour_rating,
            "mangadex_id": w.mangadex_id,
            "synopsis": w.synopsis_200w,
            "cover_url": w.cover_url,
            "source_url": w.source_url
        })
        
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "results": serialized
    }

@router.get("/{webtoon_id}")
async def get_webtoon_detail(webtoon_id: str, user = Depends(get_current_user)):
    try:
        w = Webtoon.objects.get(id=webtoon_id)
    except (Webtoon.DoesNotExist, ValueError):
        raise HTTPException(status_code=404, detail="Webtoon not found")
        
    user_status = UserWebtoonStatus.objects.filter(user=user, webtoon=w).first()
    
    return {
        "id": str(w.id),
        "title": w.title,
        "slug": w.slug,
        "genres": w.genres,
        "colour_rating": w.colour_rating,
        "mangadex_id": w.mangadex_id,
        "synopsis": w.synopsis_200w,
        "cover_url": w.cover_url,
        "source_url": w.source_url,
        "user_status": {
            "status": user_status.status if user_status else None,
            "rating": user_status.user_rating if user_status else None,
            "note": user_status.feedback_note if user_status else None
        }
    }
