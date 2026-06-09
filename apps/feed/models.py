import uuid
from django.db import models
from django.conf import settings

class FeedCycle(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='feed_cycles')
    cycle_number = models.IntegerField(default=1)
    webtoons_suggested = models.JSONField(default=list)  # List of Webtoon UUID strings
    all_skipped = models.BooleanField(default=False)
    fallback_triggered = models.BooleanField(default=False)
    scrape_expansion_triggered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - Cycle {self.cycle_number} ({self.created_at})"


class AppOperatingCycle(models.Model):
    PHASE_CHOICES = [
        ('onboarding', 'Onboarding'),
        ('scraping', 'Scraping'),
        ('embedding', 'Embedding'),
        ('feeding', 'Feeding'),
        ('feedback', 'Feedback'),
        ('expanding', 'Expanding'),
    ]

    cycle_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    phase = models.CharField(max_length=30, choices=PHASE_CHOICES)
    langgraph_run_id = models.CharField(max_length=150, blank=True)
    langsmith_trace_url = models.URLField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.phase} - {self.cycle_id} ({self.timestamp})"
