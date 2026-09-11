"""Shared response shapes for the REST API.

Every payload exposes ``cover_url`` as an address on *our* origin
(``/cover/<id>/``) rather than the upstream CDN link.  Clients therefore never
deal with a dead provider link, a hotlink block, or a CORS failure - the proxy
resolves those server-side and falls back to a generated placeholder.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from apps.webtoons.models import Webtoon


def webtoon_card(webtoon: Webtoon, *, reason: str = "", status: str = "suggested") -> Dict[str, Any]:
    """Compact shape used by feed grids and catalogue listings."""
    return {
        "id": str(webtoon.id),
        "title": webtoon.title,
        "slug": webtoon.slug,
        "genres": webtoon.genres or [],
        "cover_url": webtoon.cover_proxy_url,
        "banner_url": webtoon.banner_proxy_url if webtoon.banner_url else "",
        "accent_color": webtoon.display_accent,
        "colour_rating": webtoon.colour_rating,
        "average_score": webtoon.average_score,
        "chapter_count": webtoon.chapter_count,
        "release_year": webtoon.release_year,
        "publication_status": webtoon.publication_status,
        "detail_url": "/webtoon/{0}/".format(webtoon.slug),
        "reason": reason,
        "status": status,
    }


def webtoon_detail(
    webtoon: Webtoon, *, user_status: Optional[object] = None
) -> Dict[str, Any]:
    """Full shape used by the series endpoint."""
    payload = webtoon_card(webtoon)
    payload.update(
        {
            "alt_titles": webtoon.alt_titles or [],
            "tags": webtoon.tags or [],
            "synopsis": webtoon.synopsis_200w,
            "authors": webtoon.authors or [],
            "country": webtoon.country,
            "source_url": webtoon.source_url,
            "external_links": webtoon.external_links or {},
            "anilist_id": webtoon.anilist_id,
            "mangadex_id": webtoon.mangadex_id,
            "cover_source": webtoon.cover_source,
            "user_status": {
                "status": getattr(user_status, "status", None),
                "rating": getattr(user_status, "user_rating", None),
                "note": getattr(user_status, "feedback_note", None),
            },
        }
    )
    return payload
