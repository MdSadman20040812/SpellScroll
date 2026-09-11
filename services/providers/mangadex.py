"""MangaDex provider - fallback metadata and the chapter feed.

The previous implementation stored fully-resolved cover URLs
(``uploads.mangadex.org/covers/<manga-id>/<file>.jpg``) directly in the
database.  Those filenames change whenever a series' primary cover is replaced,
so the links silently rotted, and several seeded IDs pointed at the wrong
series entirely.  This module never hardcodes a filename: it resolves the
current ``cover_art`` relationship on every sync.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from services.http import RateLimiter, request_json
from services.metadata import SeriesMetadata

logger = logging.getLogger(__name__)

API = "https://api.mangadex.org"
UPLOADS = "https://uploads.mangadex.org"
PROVIDER = "mangadex"

# MangaDex asks for at most 5 requests/second across an IP.
_limiter = RateLimiter(min_interval=0.25)

_DEMOGRAPHIC_TO_GENRE = {"shounen": "action", "shoujo": "romance"}


def _localised(value: Any, prefer: str = "en") -> str:
    """MangaDex returns ``{"en": "...", "ja": "..."}`` maps for most text."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if value.get(prefer):
            return value[prefer]
        for key in ("en", "ja-ro", "ko-ro", "ja", "ko"):
            if value.get(key):
                return value[key]
        for candidate in value.values():
            if candidate:
                return candidate
    return ""


def cover_url_for(manga_id: str, filename: str, width: int = 512) -> str:
    """Build a cover URL, using MangaDex's pre-generated downscaled variants."""
    if width in (256, 512):
        return "{0}/covers/{1}/{2}.{3}.jpg".format(UPLOADS, manga_id, filename, width)
    return "{0}/covers/{1}/{2}".format(UPLOADS, manga_id, filename)


def _to_metadata(item: Dict[str, Any]) -> SeriesMetadata:
    manga_id = item.get("id") or ""
    attrs = item.get("attributes") or {}
    relationships = item.get("relationships") or []

    cover_file = ""
    authors: List[str] = []
    for rel in relationships:
        rel_attrs = rel.get("attributes") or {}
        if rel.get("type") == "cover_art" and rel_attrs.get("fileName"):
            cover_file = rel_attrs["fileName"]
        elif rel.get("type") in ("author", "artist") and rel_attrs.get("name"):
            if rel_attrs["name"] not in authors:
                authors.append(rel_attrs["name"])

    genres: List[str] = []
    for tag in attrs.get("tags") or []:
        tag_attrs = tag.get("attributes") or {}
        if tag_attrs.get("group") in ("genre", "theme"):
            name = _localised(tag_attrs.get("name"))
            if name:
                genres.append(name)
    demographic = (attrs.get("publicationDemographic") or "").lower()
    if demographic in _DEMOGRAPHIC_TO_GENRE:
        genres.append(_DEMOGRAPHIC_TO_GENRE[demographic])

    links = attrs.get("links") or {}
    source_url = links.get("engtl") or links.get("raw") or "https://mangadex.org/title/" + manga_id

    last_chapter = str(attrs.get("lastChapter") or "")

    return SeriesMetadata(
        title=_localised(attrs.get("title")).strip(),
        provider=PROVIDER,
        provider_id=manga_id,
        mangadex_id=manga_id,
        alt_titles=[_localised(t) for t in (attrs.get("altTitles") or [])][:4],
        genres=genres,
        synopsis=_localised(attrs.get("description")),
        cover_url=cover_url_for(manga_id, cover_file) if cover_file else "",
        source_url=source_url,
        external_links={
            k: v for k, v in links.items() if isinstance(v, str) and v.startswith("http")
        },
        chapters=int(last_chapter) if last_chapter.isdigit() else None,
        release_year=attrs.get("year"),
        status=(attrs.get("status") or "").lower(),
        country=(attrs.get("originalLanguage") or "").upper()[:2],
        authors=authors[:3],
    )


def fetch_by_id(manga_id: str) -> Optional[SeriesMetadata]:
    """Fetch one series, resolving its *current* cover filename."""
    if not manga_id or manga_id == "mock":
        return None
    data = request_json(
        "GET",
        API + "/manga/" + manga_id,
        limiter=_limiter,
        params={"includes[]": ["cover_art", "author", "artist"]},
    )
    item = (data or {}).get("data")
    return _to_metadata(item) if item else None


def search(title: str) -> Optional[SeriesMetadata]:
    if not title:
        return None
    data = request_json(
        "GET",
        API + "/manga",
        limiter=_limiter,
        params={
            "title": title,
            "limit": 1,
            "includes[]": ["cover_art", "author", "artist"],
            "order[relevance]": "desc",
            "contentRating[]": ["safe", "suggestive"],
        },
    )
    items = (data or {}).get("data") or []
    return _to_metadata(items[0]) if items else None


def fetch_chapters(manga_id: str, limit: int = 8, language: str = "en") -> List[dict]:
    """Latest translated chapters, for the series detail page."""
    if not manga_id or manga_id == "mock":
        return []
    data = request_json(
        "GET",
        API + "/manga/" + manga_id + "/feed",
        limiter=_limiter,
        params={
            "limit": limit,
            "order[chapter]": "desc",
            "translatedLanguage[]": [language],
            "contentRating[]": ["safe", "suggestive"],
        },
    )
    chapters = []
    for item in (data or {}).get("data") or []:
        attrs = item.get("attributes") or {}
        number = attrs.get("chapter")
        chapters.append(
            {
                "id": item.get("id"),
                "number": number,
                "title": attrs.get("title") or ("Chapter " + number if number else "Oneshot"),
                "published_at": attrs.get("publishAt") or attrs.get("readableAt"),
                "external_url": "https://mangadex.org/chapter/" + str(item.get("id")),
            }
        )
    return chapters
