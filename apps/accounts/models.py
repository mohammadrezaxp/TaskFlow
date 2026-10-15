from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom User model for TaskFlow.
    Extends Django's AbstractUser for future extensibility (e.g. avatar, role, bio).
    """
    email = models.EmailField(unique=True, blank=False, null=False)

    def __str__(self):
        return self.username
