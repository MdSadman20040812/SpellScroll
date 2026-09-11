"""Build and refresh the webtoon catalogue from live provider APIs.

This replaces the previous hand-maintained ``WEBTOON_SEED_DATA`` block, whose
cover URLs pinned specific MangaDex filenames that go stale, and whose IDs had
drifted onto the wrong series in a few cases.

Usage::

    python manage.py sync_catalog                 # discover + refresh (default 80)
    python manage.py sync_catalog --limit 40
    python manage.py sync_catalog --refresh-only  # only re-sync existing rows
    python manage.py sync_catalog --covers-only   # only re-mirror artwork
    python manage.py sync_catalog --force         # ignore cover cache
"""
from __future__ import annotations

import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.webtoons.models import Webtoon
from services import catalog, covers
from services.metadata import SeriesMetadata, colour_rating_from
from services.providers.mangadex import search as mangadex_search


def _normalise(value: str) -> str:
    return "".join(ch for ch in (value or "").lower() if ch.isalnum())


def _titles_agree(webtoon: Webtoon, meta: SeriesMetadata) -> bool:
    ours = {_normalise(webtoon.title)} | {
        _normalise(t) for t in (webtoon.alt_titles or [])
    }
    theirs = {_normalise(meta.title)} | {_normalise(t) for t in meta.alt_titles}
    return bool({t for t in ours if t} & {t for t in theirs if t})

# Titles the discovery pass should always include even if they fall outside the
# popularity window on a given day.  Everything about them is still fetched
# live; this list only pins *which* series, never their data.
CURATED_TITLES = [
    "Lore Olympus",
    "Solo Leveling",
    "Tower of God",
    "Omniscient Reader",
    "The Beginning After the End",
    "Sweet Home",
    "Bastard",
    "True Beauty",
    "Eleceed",
    "Lookism",
]


class Command(BaseCommand):
    help = "Sync the webtoon catalogue and artwork from AniList/MangaDex/Kitsu."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=80, help="Target catalogue size.")
        parser.add_argument(
            "--refresh-only",
            action="store_true",
            help="Re-sync existing rows without discovering new series.",
        )
        parser.add_argument(
            "--covers-only",
            action="store_true",
            help="Only re-mirror artwork and re-derive accent colours.",
        )
        parser.add_argument(
            "--force", action="store_true", help="Re-download artwork already cached."
        )
        parser.add_argument(
            "--no-images",
            action="store_true",
            help="Skip the image mirroring pass (metadata only).",
        )
        parser.add_argument(
            "--no-chapters",
            action="store_true",
            help="Skip resolving MangaDex IDs used for chapter listings.",
        )

    def handle(self, *args, **options):
        started = time.monotonic()

        if options["covers_only"]:
            cached, placeheld = self._sync_images(
                Webtoon.objects.filter(is_active=True), force=options["force"]
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "Artwork pass complete: {0} cached, {1} unavailable.".format(
                        cached, placeheld
                    )
                )
            )
            return

        created = updated = 0

        if not options["refresh_only"]:
            self.stdout.write("Discovering popular full-colour webtoons via AniList...")
            discovered = catalog.browse_webtoons(limit=options["limit"])
            self.stdout.write("  found {0} series".format(len(discovered)))

            known = {m.title.lower() for m in discovered}
            for title in CURATED_TITLES:
                if title.lower() in known:
                    continue
                meta = catalog.resolve(title)
                if meta:
                    discovered.append(meta)
                    self.stdout.write("  + curated: {0}".format(meta.title))
                else:
                    self.stderr.write("  ! could not resolve curated title: " + title)

            for rank, meta in enumerate(discovered, start=1):
                was_created = self._upsert(meta, rank=rank)
                created += int(was_created)
                updated += int(not was_created)
        else:
            existing = Webtoon.objects.filter(is_active=True)
            self.stdout.write("Refreshing {0} existing series...".format(existing.count()))
            for webtoon in existing:
                meta = catalog.resolve(
                    webtoon.title,
                    anilist_id=webtoon.anilist_id,
                    mangadex_id=webtoon.mangadex_id,
                )
                if meta:
                    self._upsert(meta, rank=webtoon.popularity_rank)
                    updated += 1
                else:
                    self.stderr.write("  ! no provider match: " + webtoon.title)

        self.stdout.write(
            self.style.SUCCESS(
                "Metadata: {0} created, {1} updated.".format(created, updated)
            )
        )

        if not options["no_chapters"]:
            linked = self._link_mangadex(
                Webtoon.objects.filter(is_active=True, mangadex_id="")
            )
            self.stdout.write("Chapter sources: {0} series linked to MangaDex.".format(linked))

        if not options["no_images"]:
            self.stdout.write("Mirroring artwork and deriving accent colours...")
            cached, placeheld = self._sync_images(
                Webtoon.objects.filter(is_active=True), force=options["force"]
            )
            self.stdout.write(
                "  {0} covers cached, {1} falling back to placeholders".format(
                    cached, placeheld
                )
            )

        total = Webtoon.objects.filter(is_active=True).count()
        self.stdout.write(
            self.style.SUCCESS(
                "Catalogue now holds {0} active series ({1:.1f}s).".format(
                    total, time.monotonic() - started
                )
            )
        )

    # ------------------------------------------------------------------ #

    def _upsert(self, meta: SeriesMetadata, *, rank: int) -> bool:
        """Insert or update one series.  Returns True when newly created."""
        webtoon = None
        if meta.anilist_id:
            webtoon = Webtoon.objects.filter(anilist_id=meta.anilist_id).first()
        if webtoon is None and meta.mangadex_id:
            webtoon = Webtoon.objects.filter(mangadex_id=meta.mangadex_id).first()
        if webtoon is None:
            webtoon = Webtoon.objects.filter(title__iexact=meta.title).first()

        created = webtoon is None
        if created:
            webtoon = Webtoon(title=meta.title)

        webtoon.title = meta.title or webtoon.title
        webtoon.genres = meta.genres
        webtoon.tags = meta.tags
        webtoon.alt_titles = meta.alt_titles
        webtoon.colour_rating = colour_rating_from(meta)
        webtoon.popularity_rank = rank
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

        # A changed artwork URL invalidates the mirrored copy and the accent.
        if meta.cover_url and meta.cover_url != webtoon.cover_url:
            webtoon.cover_url = meta.cover_url
            webtoon.cover_cached = False
            webtoon.accent_color = meta.accent_color or ""
        elif meta.accent_color and not webtoon.accent_color:
            webtoon.accent_color = meta.accent_color

        if meta.banner_url:
            webtoon.banner_url = meta.banner_url

        webtoon.cover_source = meta.provider
        webtoon.cover_synced_at = timezone.now()
        webtoon.save()
        return created

    def _link_mangadex(self, queryset) -> int:
        """Attach a MangaDex ID to AniList-sourced rows.

        AniList has no chapter feed, so the detail page needs a MangaDex handle
        to list chapters.  A match is only accepted when the titles agree, so a
        near-miss cannot silently point a series at someone else's chapters.
        """
        linked = 0
        for webtoon in queryset:
            candidates = [webtoon.title] + list(webtoon.alt_titles or [])[:2]
            for candidate in candidates:
                match = mangadex_search(candidate)
                if match and _titles_agree(webtoon, match):
                    webtoon.mangadex_id = match.provider_id
                    webtoon.save(update_fields=["mangadex_id"])
                    linked += 1
                    break
        return linked

    def _sync_images(self, queryset, *, force: bool):
        cached = placeheld = 0
        for webtoon in queryset:
            path = None
            if webtoon.cover_url:
                path = covers.cache_image(webtoon.cover_url, force=force)

            if path is None and webtoon.cover_url:
                # AniList/MangaDex disagreed or the host is down; try the other
                # providers for a usable cover before giving up on the image.
                alternate = catalog.resolve(
                    webtoon.title,
                    anilist_id=webtoon.anilist_id,
                    mangadex_id=webtoon.mangadex_id,
                    enrich=True,
                )
                if alternate and alternate.cover_url != webtoon.cover_url:
                    path = covers.cache_image(alternate.cover_url, force=force)
                    if path:
                        webtoon.cover_url = alternate.cover_url
                        webtoon.cover_source = alternate.provider

            if path is None:
                webtoon.cover_cached = False
                webtoon.save(update_fields=["cover_cached"])
                placeheld += 1
                self.stderr.write("  ! no cover for " + webtoon.title)
                continue

            accent = webtoon.accent_color or covers.dominant_colour(path) or ""
            webtoon.accent_color = accent
            webtoon.cover_cached = True
            webtoon.save(
                update_fields=["accent_color", "cover_cached", "cover_url", "cover_source"]
            )
            cached += 1

            if webtoon.banner_url:
                covers.cache_image(webtoon.banner_url, force=force)

        return cached, placeheld
