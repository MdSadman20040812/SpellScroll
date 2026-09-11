"""Series browsing plus the cover image proxy.

The proxy is the reason covers stop breaking: templates and API payloads point
at ``/cover/<uuid>/`` on our own origin, and this module decides at request
time whether that resolves to a locally cached file, a freshly mirrored
download, or a generated placeholder.  A dead upstream degrades to a styled
gradient instead of a broken-image icon.
"""
from __future__ import annotations

import logging
import os
from collections import Counter

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.http import http_date
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from services import catalog, covers
from services.metadata import colour_rating_from
from services.providers import mangadex

from .models import UserWebtoonStatus, Webtoon

logger = logging.getLogger(__name__)

# Cached covers are content-addressed by upstream URL, so they can be cached
# hard by the browser; a re-sync changes the URL and busts it naturally.
COVER_MAX_AGE = 60 * 60 * 24 * 14
# A placeholder means the upstream was missing or down, so keep that short.
PLACEHOLDER_MAX_AGE = 60 * 10

_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".gif": "image/gif",
}


def _placeholder_response(title: str, *, width: int, height: int) -> HttpResponse:
    svg = covers.placeholder_svg(title, width=width, height=height)
    response = HttpResponse(svg, content_type="image/svg+xml")
    response["Cache-Control"] = "public, max-age={0}".format(PLACEHOLDER_MAX_AGE)
    response["X-Cover-Source"] = "placeholder"
    return response


def _serve_image(path: str, source: str) -> HttpResponse:
    ext = os.path.splitext(path)[1].lower()
    with open(path, "rb") as handle:
        payload = handle.read()

    # Read into memory rather than streaming: covers are a few hundred KB at
    # most, and Django's FileResponse warns (and blocks the event loop) when a
    # synchronous file iterator is consumed under ASGI.
    response = HttpResponse(payload, content_type=_CONTENT_TYPES.get(ext, "image/jpeg"))
    response["Cache-Control"] = "public, max-age={0}, immutable".format(COVER_MAX_AGE)
    response["Last-Modified"] = http_date(os.path.getmtime(path))
    response["Content-Length"] = str(len(payload))
    response["X-Cover-Source"] = source
    return response


def _image_proxy(webtoon: Webtoon, *, banner: bool) -> HttpResponse:
    url = webtoon.banner_url if banner else webtoon.cover_url
    width, height = (1200, 400) if banner else (400, 600)

    if not url:
        return _placeholder_response(webtoon.title, width=width, height=height)

    path = covers.cached_path(url)
    if path is None:
        # First request for this cover: mirror it now so the next one is local.
        path = covers.cache_image(url)
        if path and not banner and not webtoon.cover_cached:
            updates = {"cover_cached": True}
            if not webtoon.accent_color:
                accent = covers.dominant_colour(path)
                if accent:
                    updates["accent_color"] = accent
            Webtoon.objects.filter(pk=webtoon.pk).update(**updates)

    if path is None:
        return _placeholder_response(webtoon.title, width=width, height=height)

    return _serve_image(path, webtoon.cover_source or "cache")


@require_GET
@cache_control(public=True)
def webtoon_cover_view(request, webtoon_id):
    webtoon = get_object_or_404(Webtoon, id=webtoon_id)
    return _image_proxy(webtoon, banner=False)


@require_GET
@cache_control(public=True)
def webtoon_banner_view(request, webtoon_id):
    webtoon = get_object_or_404(Webtoon, id=webtoon_id)
    return _image_proxy(webtoon, banner=True)


def webtoon_detail_view(request, slug):
    webtoon = get_object_or_404(Webtoon, slug=slug)

    user_status = None
    if request.user.is_authenticated:
        user_status = UserWebtoonStatus.objects.filter(
            user=request.user, webtoon=webtoon
        ).first()

    chapters = mangadex.fetch_chapters(webtoon.mangadex_id, limit=8)

    # Series sharing at least one genre, ranked by overlap.
    related = []
    if webtoon.genres:
        candidates = (
            Webtoon.objects.filter(is_active=True)
            .exclude(pk=webtoon.pk)
            .only("id", "title", "slug", "genres", "accent_color", "cover_url", "average_score")
        )
        scored = []
        wanted = set(webtoon.genres)
        for candidate in candidates:
            overlap = len(wanted & set(candidate.genres or []))
            if overlap:
                scored.append((overlap, candidate.average_score or 0, candidate))
        scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
        related = [row[2] for row in scored[:6]]

    return render(
        request,
        "webtoon_detail.html",
        {
            "webtoon": webtoon,
            "user_status": user_status,
            "chapters": chapters,
            "related": related,
            "has_live_chapters": bool(chapters),
        },
    )


def genre_list_view(request):
    """The Archive: genre facets plus a searchable, filterable catalogue."""
    query = (request.GET.get("q") or "").strip()
    active_genre = (request.GET.get("genre") or "").strip().lower()
    sort = request.GET.get("sort") or "popular"

    catalogue = Webtoon.objects.filter(is_active=True)

    counter: Counter = Counter()
    for genres in catalogue.values_list("genres", flat=True):
        for genre in genres or []:
            counter[genre.strip().lower()] += 1
    genre_facets = [
        {"name": name, "count": count, "hue": covers.hue_from_title(name)}
        for name, count in counter.most_common(24)
    ]

    if query:
        catalogue = catalogue.filter(
            Q(title__icontains=query) | Q(synopsis_200w__icontains=query)
        )
    if active_genre:
        catalogue = catalogue.filter(genres__icontains=active_genre)

    sort_map = {
        "popular": ["popularity_rank", "title"],
        "score": ["-average_score", "popularity_rank"],
        "colour": ["-colour_rating", "popularity_rank"],
        "newest": ["-release_year", "popularity_rank"],
        "title": ["title"],
    }
    catalogue = catalogue.order_by(*sort_map.get(sort, sort_map["popular"]))

    results = list(catalogue[:120])

    # The local catalogue is only what has been synced. When a search finds
    # little or nothing locally, reach straight out to the providers so the
    # Archive can browse the wider catalogue instead of dead-ending.
    remote = []
    if query and len(results) < 6:
        known = {
            "".join(ch for ch in title.lower() if ch.isalnum())
            for title in Webtoon.objects.filter(is_active=True).values_list("title", flat=True)
        }
        for meta in catalog.search_providers(query, limit=18):
            key = "".join(ch for ch in meta.title.lower() if ch.isalnum())
            if key not in known:
                remote.append(meta)

    return render(
        request,
        "genres.html",
        {
            "genres": genre_facets,
            "results": results,
            "result_count": len(results),
            "remote": remote,
            "total_count": Webtoon.objects.filter(is_active=True).count(),
            "query": query,
            "active_genre": active_genre,
            "sort": sort,
        },
    )


@login_required
@require_POST
def import_webtoon_view(request):
    """Pull a provider search result into the local catalogue on demand.

    This is what makes the Archive's reach match the providers' reach: a
    reader can search for anything, and the series they pick becomes a real
    catalogue entry the recommendation agents can rank.
    """
    title = (request.POST.get("title") or "").strip()
    anilist_id = request.POST.get("anilist_id") or None
    mangadex_id = request.POST.get("mangadex_id") or ""

    meta = catalog.resolve(
        title,
        anilist_id=int(anilist_id) if str(anilist_id).isdigit() else None,
        mangadex_id=mangadex_id,
    )
    if meta is None:
        messages.error(request, "Could not find “{0}” at any provider.".format(title))
        return redirect("genre_list")

    existing = None
    if meta.anilist_id:
        existing = Webtoon.objects.filter(anilist_id=meta.anilist_id).first()
    if existing is None:
        existing = Webtoon.objects.filter(title__iexact=meta.title).first()

    webtoon = existing or Webtoon(title=meta.title)
    webtoon.genres = meta.genres
    webtoon.tags = meta.tags
    webtoon.alt_titles = meta.alt_titles
    webtoon.colour_rating = colour_rating_from(meta)
    webtoon.synopsis_200w = meta.synopsis or webtoon.synopsis_200w
    webtoon.source_url = meta.source_url or webtoon.source_url
    webtoon.external_links = meta.external_links
    webtoon.average_score = meta.average_score
    webtoon.chapter_count = meta.chapters
    webtoon.release_year = meta.release_year
    webtoon.publication_status = meta.status
    webtoon.country = meta.country
    webtoon.authors = meta.authors
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
    if not webtoon.popularity_rank or webtoon.popularity_rank == 9999:
        webtoon.popularity_rank = (
            Webtoon.objects.filter(is_active=True).count() + 1
        )
    webtoon.cover_source = meta.provider
    webtoon.cover_synced_at = timezone.now()
    webtoon.save()

    messages.success(
        request, "Added “{0}” to the archive.".format(webtoon.title)
    )
    return redirect("webtoon_detail", slug=webtoon.slug)
