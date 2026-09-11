import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Webtoon(models.Model):
    """A single series in the catalogue.

    Provider-derived fields (``anilist_id``, ``cover_url``, ``banner_url``,
    ``accent_color`` ...) are refreshed by ``manage.py sync_catalog`` rather
    than hand-maintained, which is what keeps cover links from going stale.
    """

    STATUS_CHOICES = [
        ("releasing", "Releasing"),
        ("finished", "Finished"),
        ("hiatus", "On Hiatus"),
        ("cancelled", "Cancelled"),
        ("not_yet_released", "Upcoming"),
        ("", "Unknown"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    genres = models.JSONField(default=list)  # normalised lowercase strings
    tags = models.JSONField(default=list, blank=True)  # finer-grained descriptors
    alt_titles = models.JSONField(default=list, blank=True)
    colour_rating = models.FloatField(default=0.0)  # 0-1, how full-colour the art is
    popularity_rank = models.IntegerField(default=9999)

    # Provider identity
    anilist_id = models.IntegerField(null=True, blank=True, unique=True, db_index=True)
    mangadex_id = models.CharField(max_length=100, blank=True, db_index=True)

    synopsis_200w = models.TextField(blank=True)

    # Artwork.  ``cover_url``/``banner_url`` hold the upstream address; the app
    # always renders them through the caching proxy in apps.webtoons.views.
    cover_url = models.URLField(max_length=500, blank=True)
    banner_url = models.URLField(max_length=500, blank=True)
    accent_color = models.CharField(max_length=9, blank=True)  # #rrggbb
    cover_source = models.CharField(max_length=32, blank=True)  # anilist/mangadex/kitsu
    cover_synced_at = models.DateTimeField(null=True, blank=True)
    cover_cached = models.BooleanField(default=False)

    source_url = models.URLField(max_length=500, blank=True)
    external_links = models.JSONField(default=dict, blank=True)

    average_score = models.IntegerField(null=True, blank=True)  # 0-100
    chapter_count = models.IntegerField(null=True, blank=True)
    release_year = models.IntegerField(null=True, blank=True)
    publication_status = models.CharField(
        max_length=32, choices=STATUS_CHOICES, blank=True
    )
    country = models.CharField(max_length=2, blank=True)
    authors = models.JSONField(default=list, blank=True)

    scraped_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["popularity_rank", "title"]
        indexes = [
            models.Index(fields=["is_active", "popularity_rank"]),
            models.Index(fields=["-average_score"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or "webtoon"
            self.slug = base
            count = 1
            while Webtoon.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = "{0}-{1}".format(base, count)
                count += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("webtoon_detail", kwargs={"slug": self.slug})

    @property
    def cover_proxy_url(self):
        """Always-renderable cover address for templates and API payloads."""
        return reverse("webtoon_cover", kwargs={"webtoon_id": self.id})

    @property
    def banner_proxy_url(self):
        return reverse("webtoon_banner", kwargs={"webtoon_id": self.id})

    @property
    def display_accent(self):
        return self.accent_color or "#a78bfa"

    @property
    def score_percent(self):
        return self.average_score if self.average_score is not None else None


class UserWebtoonStatus(models.Model):
    STATUS_CHOICES = [
        ("suggested", "Suggested"),
        ("reading", "Reading"),
        ("completed", "Completed"),
        ("skipped", "Skipped"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="webtoon_statuses"
    )
    webtoon = models.ForeignKey(
        Webtoon, on_delete=models.CASCADE, related_name="user_statuses"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="suggested")
    user_rating = models.IntegerField(null=True, blank=True)  # 1-5
    feedback_note = models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "webtoon")
        indexes = [models.Index(fields=["user", "status"])]

    def __str__(self):
        return "{0} - {1} ({2})".format(
            self.user.username, self.webtoon.title, self.status
        )
