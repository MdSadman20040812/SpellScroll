import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify

class Webtoon(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    genres = models.JSONField(default=list)  # list of strings
    colour_rating = models.FloatField(default=0.0)  # Float 0-1
    popularity_rank = models.IntegerField(default=9999)
    mangadex_id = models.CharField(max_length=100, blank=True)
    synopsis_200w = models.TextField(blank=True)
    cover_url = models.URLField(max_length=500, blank=True)
    source_url = models.URLField(max_length=500, blank=True)
    scraped_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            # handle possible collision
            original_slug = self.slug
            count = 1
            while Webtoon.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{count}"
                count += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class UserWebtoonStatus(models.Model):
    STATUS_CHOICES = [
        ('suggested', 'Suggested'),
        ('reading', 'Reading'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='webtoon_statuses')
    webtoon = models.ForeignKey(Webtoon, on_delete=models.CASCADE, related_name='user_statuses')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='suggested')
    user_rating = models.IntegerField(null=True, blank=True)  # 1-5 rating
    feedback_note = models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'webtoon')

    def __str__(self):
        return f"{self.user.username} - {self.webtoon.title} ({self.status})"
