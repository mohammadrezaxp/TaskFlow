from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from .views import KanbanView, TaskCommentViewSet, TaskViewSet

router = DefaultRouter()
router.register(r"tasks", TaskViewSet, basename="task")
router.register(r"task-comments", TaskCommentViewSet, basename="taskcomment")

urlpatterns = [
    path("api/v1/", include(router.urls)),
    path(
        "tasks/",
        TemplateView.as_view(template_name="tasks/list.html"),
        name="task-list",
    ),
    path("tasks/kanban/", KanbanView.as_view(), name="task-kanban"),
    path(
        "tasks/new/",
        TemplateView.as_view(template_name="tasks/form.html"),
        name="task-create",
    ),
    path(
        "tasks/<uuid:pk>/",
        TemplateView.as_view(template_name="tasks/detail.html"),
        name="task-detail",
    ),
    path(
        "tasks/<uuid:pk>/comments/",
        TemplateView.as_view(template_name="tasks/comments.html"),
        name="task-comments",
    ),
]
