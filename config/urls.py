from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.views.generic import TemplateView

def health_check(request):
    return JsonResponse({"status": "ok", "app": "TaskFlow"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health-check'),
    
    # Dashboard
    path('', TemplateView.as_view(template_name='dashboard/index.html'), name='dashboard'),

    # Accounts
    path('accounts/', include('apps.accounts.urls')),
    path('login/', include('django.contrib.auth.urls')),
    path('password_reset/', include('django.contrib.auth.urls')),

    # Organizations
    path('', include('apps.organizations.urls')),


    # Projects
    path('', include('apps.projects.urls')),

    # Tasks
    path('', include('apps.tasks.urls')),

    # Other Modules
    path('notifications/', TemplateView.as_view(template_name='notifications/list.html'), name='notification-list'),
    path('activity/', TemplateView.as_view(template_name='activity/list.html'), name='activity-list'),
    path('analytics/', TemplateView.as_view(template_name='analytics/index.html'), name='analytics'),
    path('calendar/', TemplateView.as_view(template_name='calendar/index.html'), name='calendar'),
    path('messages/', TemplateView.as_view(template_name='messages/index.html'), name='messages'),
    path('team/', TemplateView.as_view(template_name='team/list.html'), name='team-list'),

    # Settings
    path('settings/', TemplateView.as_view(template_name='settings/index.html'), name='settings-index'),
    path('settings/security/', TemplateView.as_view(template_name='settings/security.html'), name='settings-security'),
    path('settings/notifications/', TemplateView.as_view(template_name='settings/notifications.html'), name='settings-notifications'),

    # API placeholder
    path('api/v1/', include([])),
]
