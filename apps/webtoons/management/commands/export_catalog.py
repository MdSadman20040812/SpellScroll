"""Export the catalogue as JSON for the static Next.js frontend.

``spellscroll-web`` ships without a database, so it reads a snapshot of the
catalogue from ``app/api/catalog/data.json``.  Regenerating that file from the
Django catalogue is what keeps the two frontends showing the same series rather
than drifting apart, which is what happened with the previous hand-edited file.

Cover URLs are exported as the upstream provider addresses (AniList's CDN
hotlinks cleanly) because the static app has no proxy of its own; the accent
colour travels with each record so cards look identical in both frontends.

Usage::

    python manage.py export_catalog
    python manage.py export_catalog --output some/other/path.json
"""
from __future__ import annotations

import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.webtoons.models import Webtoon

DEFAULT_OUTPUT = os.path.join(
    settings.BASE_DIR, "spellscroll-web", "app", "api", "catalog", "data.json"
)


class Command(BaseCommand):
    help = "Write the active catalogue to the Next.js app's data.json snapshot."

    def add_arguments(self, parser):
        parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Target JSON path.")
        parser.add_argument(
            "--limit", type=int, default=0, help="Cap the number of series exported."
        )

    def handle(self, *args, **options):
        queryset = Webtoon.objects.filter(is_active=True).order_by("popularity_rank")
        if options["limit"]:
            queryset = queryset[: options["limit"]]

        records = [
            {
                "id": str(w.id),
                "slug": w.slug,
                "title": w.title,
                "genres": w.genres or [],
                "tags": (w.tags or [])[:6],
                "synopsis": w.synopsis_200w,
                "cover_url": w.cover_url,
                "banner_url": w.banner_url,
                "accent_color": w.display_accent,
                "colour_rating": w.colour_rating,
                "popularity_rank": w.popularity_rank,
                "average_score": w.average_score,
                "chapter_count": w.chapter_count,
                "release_year": w.release_year,
                "publication_status": w.publication_status,
                "country": w.country,
                "authors": w.authors or [],
                "source_url": w.source_url,
                "anilist_id": w.anilist_id,
                "mangadex_id": w.mangadex_id,
            }
            for w in queryset
        ]

        missing_covers = sum(1 for record in records if not record["cover_url"])

        output = options["output"]
        os.makedirs(os.path.dirname(output), exist_ok=True)
        with open(output, "w", encoding="utf-8") as handle:
            json.dump(records, handle, indent=2, ensure_ascii=False)

        self.stdout.write(
            self.style.SUCCESS(
                "Exported {0} series to {1}".format(len(records), output)
            )
        )
        if missing_covers:
            self.stderr.write(
                "  ! {0} series have no upstream cover; the web app will show "
                "its generated placeholder for them.".format(missing_covers)
            )
