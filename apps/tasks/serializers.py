from rest_framework import serializers
from apps.tasks.models import Task, TaskComment

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'project', 'title', 'description', 'status', 'priority', 'assignee', 'created_by', 'due_date', 'position']
        read_only_fields = ['id', 'created_by']

    def validate_assignee(self, value):
        if value is not None:
            project = self.initial_data.get('project')
            if not project and self.instance:
                project = self.instance.project_id
            if project:
                from apps.projects.models import Project
                try:
                    proj = Project.objects.get(pk=project)
                    if not proj.organization.memberships.filter(user=value).exists():
                        raise serializers.ValidationError("Assignee must be an active member of the project's organization.")
                except Project.DoesNotExist:
                    pass
        return value

class TaskCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskComment
        fields = ['id', 'task', 'author', 'content', 'created_at']
        read_only_fields = ['id', 'author', 'created_at']
