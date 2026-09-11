"""Catalogue endpoints.

Listing is filtered, sorted and paginated in the database rather than by
materialising the whole table into Python, which is what the previous
implementation did on every request just to filter by genre.
"""
from __future__ import annotations

from typing import Optional

from asgiref.sync import sync_to_async
from django.db.models import Q
from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import get_current_user
from api.serializers import webtoon_card, webtoon_detail
from apps.webtoons.models import UserWebtoonStatus, Webtoon

router = APIRouter()

SORT_FIELDS = {
    "popular": ["popularity_rank", "title"],
    "score": ["-average_score", "popularity_rank"],
    "colour": ["-colour_rating", "popularity_rank"],
    "newest": ["-release_year", "popularity_rank"],
    "title": ["title"],
}


def _list_catalogue(genre: Optional[str], search: Optional[str], sort: str, page: int, limit: int):
    queryset = Webtoon.objects.filter(is_active=True)

    if genre:
        # genres is a JSON list of normalised lowercase strings; icontains over
        # the serialised column is exact enough for a single-token genre.
        queryset = queryset.filter(genres__icontains=genre.strip().lower())
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) | Q(synopsis_200w__icontains=search)
        )

    queryset = queryset.order_by(*SORT_FIELDS.get(sort, SORT_FIELDS["popular"]))

    total = queryset.count()
    offset = (page - 1) * limit
    results = [webtoon_card(w) for w in queryset[offset : offset + limit]]
    return total, results


@router.get("/")
async def get_webtoons_list(
    genre: Optional[str] = Query(None, description="Filter by a single genre"),
    search: Optional[str] = Query(None, description="Match title or synopsis"),
    sort: str = Query("popular", pattern="^(popular|score|colour|newest|title)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=60),
    user=Depends(get_current_user),
):
    total, results = await sync_to_async(_list_catalogue)(genre, search, sort, page, limit)
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, -(-total // limit)),
        "results": results,
    }


@router.get("/genres")
async def get_genre_facets(user=Depends(get_current_user)):
    """Genre names with counts, for building filter controls."""

    def _facets():
        counts = {}
        for genres in Webtoon.objects.filter(is_active=True).values_list("genres", flat=True):
            for genre in genres or []:
                key = genre.strip().lower()
                if key:
                    counts[key] = counts.get(key, 0) + 1
        return [
            {"name": name, "count": count}
            for name, count in sorted(counts.items(), key=lambda pair: -pair[1])
        ]

    return {"genres": await sync_to_async(_facets)()}


@router.get("/{webtoon_id}")
async def get_webtoon_detail(webtoon_id: str, user=Depends(get_current_user)):
    def _fetch():
        try:
            webtoon = Webtoon.objects.get(id=webtoon_id)
        except (Webtoon.DoesNotExist, ValueError, TypeError):
            return None
        status = UserWebtoonStatus.objects.filter(user=user, webtoon=webtoon).first()
        return webtoon_detail(webtoon, user_status=status)

    payload = await sync_to_async(_fetch)()
    if payload is None:
        raise HTTPException(status_code=404, detail="Webtoon not found")
    return payload


@router.get("/{webtoon_id}/chapters")
async def get_webtoon_chapters(
    webtoon_id: str,
    limit: int = Query(8, ge=1, le=30),
    user=Depends(get_current_user),
):
    """Latest translated chapters, fetched live from MangaDex."""
    from services.providers import mangadex

    def _mangadex_id():
        try:
            return Webtoon.objects.values_list("mangadex_id", flat=True).get(id=webtoon_id)
        except (Webtoon.DoesNotExist, ValueError, TypeError):
            return None

    manga_id = await sync_to_async(_mangadex_id)()
    if manga_id is None:
        raise HTTPException(status_code=404, detail="Webtoon not found")
    if not manga_id:
        return {"chapters": [], "source": None}

    chapters = await sync_to_async(mangadex.fetch_chapters)(manga_id, limit)
    return {"chapters": chapters, "source": "mangadex"}
