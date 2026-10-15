from rest_framework import viewsets, permissions
from .models import Task, TaskComment
from .serializers import TaskSerializer, TaskCommentSerializer
from apps.organizations.models import Membership

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from .models import Task, TaskComment
from .serializers import TaskSerializer, TaskCommentSerializer
from apps.organizations.models import Membership

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Task.objects.filter(project__organization__memberships__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['patch'])
    def reorder(self, request, pk=None):
        task = self.get_object()
        new_position = request.data.get('position')
        if new_position is None:
            return Response({'error': 'Position required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Simple reordering logic: shift positions of other tasks
        # Ponytail: O(n) scan, okay for small task counts.
        Task.objects.filter(project=task.project).exclude(id=task.id).filter(position__gte=new_position).update(position=models.F('position') + 1)
        task.position = new_position
        task.save()
        return Response({'status': 'reordered'})


class TaskCommentViewSet(viewsets.ModelViewSet):
    serializer_class = TaskCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TaskComment.objects.filter(task__project__organization__memberships__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
