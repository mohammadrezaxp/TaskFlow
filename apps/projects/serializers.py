from rest_framework import serializers
from .models import Project
from apps.tasks.models import Task, TaskComment

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'organization', 'name', 'slug', 'description', 'status', 'start_date', 'due_date', 'created_by']
        read_only_fields = ['id', 'slug', 'created_by']

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'project', 'title', 'description', 'status', 'priority', 'assignee', 'created_by', 'due_date', 'position']
        read_only_fields = ['id', 'created_by']

class TaskCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskComment
        fields = ['id', 'task', 'author', 'content', 'created_at']
        read_only_fields = ['id', 'author', 'created_at']
