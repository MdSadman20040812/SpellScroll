import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

class SpellUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_name = models.CharField(max_length=150, blank=True)
    preference_json_path = models.CharField(max_length=500, blank=True)
    onboarding_complete = models.BooleanField(default=False)
    is_admin_user = models.BooleanField(default=False)  # Custom admin flag, distinct from is_superuser
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.display_name:
            self.display_name = self.username
        if not self.preference_json_path:
            self.preference_json_path = f"media/users/{self.id}/preferences.json"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.display_name})"
