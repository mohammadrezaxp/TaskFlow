from rest_framework import viewsets, permissions
from .models import Project
from .serializers import ProjectSerializer, TaskSerializer, TaskCommentSerializer
from apps.tasks.models import Task, TaskComment
from apps.organizations.models import Membership

class IsProjectMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        org = obj.organization if hasattr(obj, 'organization') else obj.project.organization
        return Membership.objects.filter(organization=org, user=request.user).exists()

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get_queryset(self):
        return Project.objects.filter(organization__memberships__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Task.objects.filter(project__organization__memberships__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class TaskCommentViewSet(viewsets.ModelViewSet):
    serializer_class = TaskCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TaskComment.objects.filter(task__project__organization__memberships__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
