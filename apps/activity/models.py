from django.conf import settings
from django.db import models

from apps.organizations.models import Organization


class ActivityEvent(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    verb = models.CharField(max_length=100)
    label = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
