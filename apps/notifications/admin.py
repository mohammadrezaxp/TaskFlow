from django.contrib import admin

from .models import Notification, NotificationPreference, TeamMessage

admin.site.register(Notification)
admin.site.register(NotificationPreference)
admin.site.register(TeamMessage)
