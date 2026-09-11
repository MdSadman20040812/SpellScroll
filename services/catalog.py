"""Metadata resolution across providers.

Resolution order is AniList -> MangaDex -> Kitsu.  AniList leads because it is
the only one of the three that reliably supplies a cover *and* a banner *and* a
dominant colour, which is what the redesigned photocards render.  Whichever
provider answers first is then topped up from the others for any field it left
blank, so a series with an AniList entry but no banner can still borrow one.
"""
from __future__ import annotations

import logging
from typing import Callable, List, Optional, Sequence

from services.metadata import SeriesMetadata
from services.providers import anilist, kitsu, mangadex

logger = logging.getLogger(__name__)

#: Provider search functions in preference order.
SEARCH_CHAIN: Sequence[tuple] = (
    ("anilist", anilist.search),
    ("mangadex", mangadex.search),
    ("kitsu", kitsu.search),
)


def resolve(
    title: str,
    *,
    anilist_id: Optional[int] = None,
    mangadex_id: str = "",
    enrich: bool = True,
) -> Optional[SeriesMetadata]:
    """Resolve one series to a :class:`SeriesMetadata`.

    Known provider IDs are tried before falling back to a title search, since a
    title search can drift onto a spin-off (which is exactly how the old seed
    ended up with *Solo Leveling: Ragnarok* filed under *Solo Leveling*).
    """
    primary: Optional[SeriesMetadata] = None
    used = ""

    if anilist_id:
        primary = anilist.fetch_by_id(anilist_id)
        used = "anilist"
    if primary is None and mangadex_id:
        primary = mangadex.fetch_by_id(mangadex_id)
        used = "mangadex"

    if primary is None:
        for name, search_fn in SEARCH_CHAIN:
            try:
                primary = search_fn(title)
            except Exception as exc:  # provider bug must not break a sync
                logger.warning("provider %s raised for %r: %s", name, title, exc)
                continue
            if primary is not None:
                used = name
                break

    if primary is None:
        logger.info("no provider matched %r", title)
        return None

    if enrich:
        _enrich(primary, skip=used)
    return primary


def _enrich(meta: SeriesMetadata, *, skip: str) -> SeriesMetadata:
    """Fill blanks on ``meta`` from the providers that were not used first."""
    # Banners are an AniList-only field, so they are deliberately not part of
    # this test - waiting on providers that can never supply one would make
    # every sync three times slower for nothing.
    needs_more: Callable[[], bool] = lambda: not (
        meta.cover_url and meta.synopsis and meta.genres
    )
    for name, search_fn in SEARCH_CHAIN:
        if name == skip or not needs_more():
            continue
        try:
            other = search_fn(meta.title)
        except Exception:
            continue
        if other and _same_series(meta, other):
            meta.merge(other)
            if name == "mangadex" and not meta.mangadex_id:
                meta.mangadex_id = other.provider_id
    return meta


def _same_series(a: SeriesMetadata, b: SeriesMetadata) -> bool:
    """Cheap title-equivalence check to avoid merging an unrelated match."""

    def keys(meta: SeriesMetadata) -> set:
        values = [meta.title] + list(meta.alt_titles)
        return {
            "".join(ch for ch in v.lower() if ch.isalnum())
            for v in values
            if v
        }

    return bool(keys(a) & keys(b))


def browse_webtoons(
    *,
    limit: int = 80,
    countries: Sequence[str] = ("KR", "CN"),
    sort: str = "POPULARITY_DESC",
) -> List[SeriesMetadata]:
    """Discover popular full-colour webtoons to bootstrap the catalogue.

    Korean (manhwa) and Chinese (manhua) series are full colour by production
    convention, which is what SpellScroll is about; Japanese manga is excluded
    for that reason rather than by any judgement of quality.
    """
    collected: List[SeriesMetadata] = []
    seen_ids: set = set()
    per_country = max(1, limit // max(1, len(countries)))

    for country in countries:
        try:
            batch = anilist.browse(country=country, limit=per_country, sort=sort)
        except Exception as exc:
            logger.warning("AniList browse failed for %s: %s", country, exc)
            continue
        for meta in batch:
            if meta.anilist_id in seen_ids or not meta.title or not meta.cover_url:
                continue
            seen_ids.add(meta.anilist_id)
            collected.append(meta)

    return collected[:limit]


def search_providers(query: str, *, limit: int = 24) -> List[SeriesMetadata]:
    """Live search across providers, for series not yet in the catalogue.

    The local database only holds what has been synced, which is a tiny slice
    of what exists.  This lets the Archive reach the rest of the catalogue at
    request time: AniList answers most queries, and MangaDex fills in series
    AniList does not carry.
    """
    if not query or not query.strip():
        return []

    results: List[SeriesMetadata] = []
    seen: set = set()

    def _key(meta: SeriesMetadata) -> str:
        return "".join(ch for ch in meta.title.lower() if ch.isalnum())

    try:
        for meta in anilist.search_many(query, limit=limit):
            key = _key(meta)
            if key and key not in seen and meta.cover_url:
                seen.add(key)
                results.append(meta)
    except Exception as exc:
        logger.warning("AniList search failed for %r: %s", query, exc)

    if len(results) < 4:
        try:
            fallback = mangadex.search(query)
        except Exception as exc:
            logger.warning("MangaDex search failed for %r: %s", query, exc)
            fallback = None
        if fallback and _key(fallback) not in seen and fallback.cover_url:
            results.append(fallback)

    return results[:limit]
