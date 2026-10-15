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
    path('organizations/', TemplateView.as_view(template_name='organizations/list.html'), name='organization-list'),
    path('organizations/new/', TemplateView.as_view(template_name='organizations/form.html'), name='organization-create'),
    path('organizations/<int:pk>/', TemplateView.as_view(template_name='organizations/detail.html'), name='organization-detail'),
    path('organizations/<int:pk>/members/', TemplateView.as_view(template_name='organizations/members.html'), name='organization-members'),
    path('organizations/<int:pk>/invitations/', TemplateView.as_view(template_name='organizations/invitations.html'), name='organization-invitations'),

    # Projects
    path('projects/', TemplateView.as_view(template_name='projects/list.html'), name='project-list'),
    path('projects/new/', TemplateView.as_view(template_name='projects/form.html'), name='project-create'),
    path('projects/<int:pk>/', TemplateView.as_view(template_name='projects/detail.html'), name='project-detail'),

    # Tasks
    path('tasks/', TemplateView.as_view(template_name='tasks/list.html'), name='task-list'),
    path('tasks/kanban/', TemplateView.as_view(template_name='tasks/kanban.html'), name='task-kanban'),
    path('tasks/new/', TemplateView.as_view(template_name='tasks/form.html'), name='task-create'),
    path('tasks/<int:pk>/', TemplateView.as_view(template_name='tasks/detail.html'), name='task-detail'),
    path('tasks/<int:pk>/comments/', TemplateView.as_view(template_name='tasks/comments.html'), name='task-comments'),

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
