"""Kitsu provider - last upstream fallback before the generated placeholder.

Kitsu is a plain JSON:API service with no key and no Cloudflare gate, which
makes it a useful safety net for the rare title that AniList and MangaDex both
miss, and for the case where both are unreachable.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from services.http import RateLimiter, request_json
from services.metadata import SeriesMetadata

API = "https://kitsu.io/api/edge"
PROVIDER = "kitsu"

_limiter = RateLimiter(min_interval=0.3)

_SUBTYPE_TO_COUNTRY = {"manhwa": "KR", "manhua": "CN", "manga": "JP"}


def _to_metadata(item: Dict[str, Any]) -> SeriesMetadata:
    attrs = item.get("attributes") or {}
    poster = attrs.get("posterImage") or {}
    cover = attrs.get("coverImage") or {}
    titles = attrs.get("titles") or {}
    subtype = (attrs.get("subtype") or "").lower()
    slug = attrs.get("slug") or ""

    score = attrs.get("averageRating")
    try:
        average_score = int(round(float(score))) if score else None
    except (TypeError, ValueError):
        average_score = None

    start_date = attrs.get("startDate") or ""

    return SeriesMetadata(
        title=(attrs.get("canonicalTitle") or titles.get("en") or "").strip(),
        provider=PROVIDER,
        provider_id=str(item.get("id") or ""),
        alt_titles=[v for v in titles.values() if v][:4],
        synopsis=attrs.get("synopsis") or attrs.get("description") or "",
        cover_url=poster.get("original") or poster.get("large") or "",
        banner_url=cover.get("original") or cover.get("large") or "",
        source_url=("https://kitsu.io/manga/" + slug) if slug else "",
        average_score=average_score,
        chapters=attrs.get("chapterCount"),
        release_year=int(start_date[:4]) if start_date[:4].isdigit() else None,
        status=(attrs.get("status") or "").lower(),
        country=_SUBTYPE_TO_COUNTRY.get(subtype, ""),
    )


def search(title: str) -> Optional[SeriesMetadata]:
    if not title:
        return None
    data = request_json(
        "GET",
        API + "/manga",
        limiter=_limiter,
        params={"filter[text]": title, "page[limit]": 1},
        headers={"Accept": "application/vnd.api+json"},
    )
    items = (data or {}).get("data") or []
    return _to_metadata(items[0]) if items else None
