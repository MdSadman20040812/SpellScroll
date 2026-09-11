"""Catalogue expansion node.

The previous version of this module carried a 150-line literal
``WEBTOON_SEED_DATA`` block whose ``cover_url`` values pinned specific MangaDex
filenames.  Those filenames change when a series' primary cover is replaced, so
the links rotted, and a few of the IDs pointed at the wrong series outright.

Everything is now fetched live through :mod:`services.catalog`, which resolves
AniList first and falls back to MangaDex and Kitsu.
"""
from __future__ import annotations

import logging

from django.utils import timezone

from apps.webtoons.models import Webtoon
from services import catalog, covers
from services.metadata import SeriesMetadata, colour_rating_from

logger = logging.getLogger(__name__)


def _upsert(meta: SeriesMetadata, rank: int) -> bool:
    """Insert or refresh one series.  Returns True when newly created."""
    webtoon = None
    if meta.anilist_id:
        webtoon = Webtoon.objects.filter(anilist_id=meta.anilist_id).first()
    if webtoon is None and meta.mangadex_id:
        webtoon = Webtoon.objects.filter(mangadex_id=meta.mangadex_id).first()
    if webtoon is None:
        webtoon = Webtoon.objects.filter(title__iexact=meta.title).first()

    created = webtoon is None
    if created:
        webtoon = Webtoon(title=meta.title, popularity_rank=rank)

    webtoon.genres = meta.genres or webtoon.genres
    webtoon.tags = meta.tags or webtoon.tags
    webtoon.alt_titles = meta.alt_titles or webtoon.alt_titles
    webtoon.colour_rating = colour_rating_from(meta)
    webtoon.synopsis_200w = meta.synopsis or webtoon.synopsis_200w
    webtoon.source_url = meta.source_url or webtoon.source_url
    webtoon.external_links = meta.external_links or webtoon.external_links
    webtoon.average_score = meta.average_score
    webtoon.chapter_count = meta.chapters
    webtoon.release_year = meta.release_year
    webtoon.publication_status = meta.status
    webtoon.country = meta.country
    webtoon.authors = meta.authors or webtoon.authors
    webtoon.is_active = True

    if meta.anilist_id:
        webtoon.anilist_id = meta.anilist_id
    if meta.mangadex_id:
        webtoon.mangadex_id = meta.mangadex_id

    if meta.cover_url and meta.cover_url != webtoon.cover_url:
        webtoon.cover_url = meta.cover_url
        webtoon.cover_cached = False
        webtoon.accent_color = meta.accent_color or ""
    if meta.banner_url:
        webtoon.banner_url = meta.banner_url

    webtoon.cover_source = meta.provider
    webtoon.cover_synced_at = timezone.now()
    webtoon.save()

    # Mirror the artwork so the very first card render is served locally.
    if webtoon.cover_url and not webtoon.cover_cached:
        path = covers.cache_image(webtoon.cover_url)
        if path:
            webtoon.cover_cached = True
            if not webtoon.accent_color:
                webtoon.accent_color = covers.dominant_colour(path) or ""
            webtoon.save(update_fields=["cover_cached", "accent_color"])

    return created


def scrape_and_update_universe(limit: int = 80) -> int:
    """Discover and refresh the catalogue. Returns the active series count."""
    try:
        discovered = catalog.browse_webtoons(limit=limit)
    except Exception as exc:
        logger.warning("catalogue discovery failed: %s", exc)
        discovered = []

    if not discovered:
        # Providers unreachable: leave whatever is already catalogued in place
        # rather than wiping or duplicating it.
        logger.info("no series discovered; keeping the existing catalogue")
        return Webtoon.objects.filter(is_active=True).count()

    highest = (
        Webtoon.objects.filter(is_active=True)
        .order_by("-popularity_rank")
        .values_list("popularity_rank", flat=True)
        .first()
        or 0
    )

    created = 0
    for offset, meta in enumerate(discovered):
        try:
            if _upsert(meta, rank=highest + offset + 1):
                created += 1
        except Exception as exc:
            logger.warning("failed to upsert %r: %s", meta.title, exc)

    logger.info("catalogue expansion added %s new series", created)
    return Webtoon.objects.filter(is_active=True).count()


#: Below this many active series the catalogue is too thin to recommend from,
#: so an expansion is worth the wait even on a user-facing request.
MIN_HEALTHY_CATALOGUE = 25


def webtoon_scraper_node(state: dict) -> dict:
    """LangGraph node wrapper.

    This node sits on the main graph path, so it must not perform a full
    provider crawl on every feed request - that would put roughly two minutes
    of network I/O in front of each page load.  It expands only when the
    catalogue is genuinely thin, or when the user explicitly asked to expand
    discovery.
    """
    current = Webtoon.objects.filter(is_active=True).count()
    explicit = bool(state.get("expansion_count")) and state.get("feed_cycle_number", 1) > 1

    if current >= MIN_HEALTHY_CATALOGUE and not explicit:
        state["universe_size"] = current
        state["scrape_expansion_triggered"] = False
        return state

    state["universe_size"] = scrape_and_update_universe()
    state["scrape_expansion_triggered"] = True
    return state
