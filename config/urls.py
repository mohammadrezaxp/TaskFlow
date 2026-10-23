from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter

from apps.core import views
from apps.core.api import (
    OrganizationViewSet,
    ProjectViewSet,
    TaskCommentViewSet,
    TaskViewSet,
)

router = DefaultRouter()
for prefix, view, name in [
    ("organizations", OrganizationViewSet, "organization"),
    ("projects", ProjectViewSet, "project"),
    ("tasks", TaskViewSet, "task"),
    ("task-comments", TaskCommentViewSet, "taskcomment"),
]:
    router.register(prefix, view, basename="api-" + name)
urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", views.health, name="health-check"),
    path("", views.dashboard, name="dashboard"),
    path("dashboard/", views.dashboard, name="dashboard-page"),
    path("accounts/", include("apps.accounts.urls")),
    path(
        "password-reset/",
        auth.PasswordResetView.as_view(
            template_name="shared/auth_form.html",
            email_template_name="registration/password_reset_email.html",
            success_url="/password-reset/done/",
            extra_context={"title": "Reset password"},
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth.PasswordResetConfirmView.as_view(
            template_name="shared/auth_form.html",
            extra_context={"title": "Choose new password"},
            success_url="/reset/complete/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/complete/",
        auth.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path(
        "organizations/", views.OrganizationListView.as_view(), name="organization-list"
    ),
    path(
        "organizations/new/",
        views.OrganizationCreateView.as_view(),
        name="organization-create",
    ),
    path(
        "organizations/<uuid:pk>/",
        views.OrganizationDetailView.as_view(),
        name="organization-detail",
    ),
    path(
        "organizations/<uuid:pk>/members/",
        views.OrganizationMembersView.as_view(),
        name="organization-members",
    ),
    path(
        "organizations/<uuid:pk>/invitations/",
        views.OrganizationInvitationsView.as_view(),
        name="organization-invitations",
    ),
    path(
        "organizations/<uuid:pk>/delete/",
        views.delete_resource,
        {"kind": "organization"},
        name="organization-delete",
    ),
    path("invitations/<str:token>/", views.invitation_accept, name="invitation-accept"),
    path("projects/", views.project_list, name="project-list"),
    path("projects/new/", views.project_form, name="project-create"),
    path("projects/<uuid:pk>/", views.project_detail, name="project-detail"),
    path("projects/<uuid:pk>/edit/", views.project_form, name="project-edit"),
    path(
        "projects/<uuid:pk>/delete/",
        views.delete_resource,
        {"kind": "project"},
        name="project-delete",
    ),
    path("tasks/", views.task_list, name="task-list"),
    path("tasks/new/", views.task_form, name="task-create"),
    path("tasks/kanban/", views.KanbanView.as_view(), name="task-kanban"),
    path("tasks/<uuid:pk>/", views.task_detail, name="task-detail"),
    path("tasks/<uuid:pk>/edit/", views.task_form, name="task-edit"),
    path("tasks/<uuid:pk>/comments/", views.task_detail, name="task-comments"),
    path(
        "tasks/<uuid:pk>/delete/",
        views.delete_resource,
        {"kind": "task"},
        name="task-delete",
    ),
    path("notifications/", views.notifications, name="notification-list"),
    path("activity/", views.activity, name="activity-list"),
    path("team/", views.team, name="team-list"),
    path("messages/", views.messaging, name="messages"),
    path("analytics/", views.analytics, name="analytics"),
    path("calendar/", views.calendar_view, name="calendar"),
    path("settings/", views.settings_index, name="settings-index"),
    path("settings/notifications/", views.preferences, name="settings-notifications"),
    path(
        "settings/security/",
        auth.PasswordChangeView.as_view(
            template_name="shared/form.html",
            extra_context={"title": "Change password"},
            success_url="/settings/",
        ),
        name="settings-security",
    ),
    path("api/v1/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

handler403 = "apps.core.errors.forbidden"
handler404 = "apps.core.errors.not_found"
handler500 = "apps.core.errors.server_error"
