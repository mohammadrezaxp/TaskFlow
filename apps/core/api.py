from django.core.exceptions import ValidationError as ModelValidationError
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.organizations.models import Organization
from apps.projects.models import Project
from apps.tasks.models import Task, TaskComment

from . import services


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "description", "owner"]
        read_only_fields = ["id", "slug", "owner"]


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            "id",
            "organization",
            "name",
            "slug",
            "description",
            "status",
            "start_date",
            "due_date",
            "created_by",
        ]
        read_only_fields = ["id", "slug", "created_by"]

    def validate(self, data):
        user = self.context["request"].user
        org = data.get("organization", getattr(self.instance, "organization", None))
        if org:
            services.require_role(user, org, services.MANAGERS)
        if self.instance and org.pk != self.instance.organization_id:
            raise serializers.ValidationError("Projects cannot change organization.")
        start = data.get("start_date", getattr(self.instance, "start_date", None))
        end = data.get("due_date", getattr(self.instance, "due_date", None))
        if start and end and end < start:
            raise serializers.ValidationError("Due date precedes start date.")
        return data


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            "id",
            "project",
            "title",
            "description",
            "status",
            "priority",
            "assignee",
            "created_by",
            "due_date",
            "position",
        ]
        read_only_fields = ["id", "created_by", "position"]

    def validate(self, data):
        user = self.context["request"].user
        project = data.get("project", getattr(self.instance, "project", None))
        if project and not services.projects(user).filter(pk=project.pk).exists():
            raise serializers.ValidationError("Project is not accessible.")
        if self.instance and project.pk != self.instance.project_id:
            raise serializers.ValidationError("Tasks cannot change project.")
        assignee = data.get("assignee", getattr(self.instance, "assignee", None))
        if (
            assignee
            and not project.organization.memberships.filter(
                user=assignee, user__is_active=True
            ).exists()
        ):
            raise serializers.ValidationError(
                "Assignee must belong to this organization."
            )
        return data


class TaskCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskComment
        fields = ["id", "task", "author", "content", "created_at"]
        read_only_fields = ["id", "author", "created_at"]

    def validate(self, data):
        task = data.get("task", getattr(self.instance, "task", None))
        if (
            task
            and not services.tasks(self.context["request"].user)
            .filter(pk=task.pk)
            .exists()
        ):
            raise serializers.ValidationError("Task is not accessible.")
        if self.instance and task.pk != self.instance.task_id:
            raise serializers.ValidationError("Comments cannot change task.")
        content = data.get("content", "").strip()
        if "content" in data and (not content or len(content) > 4000):
            raise serializers.ValidationError("Write between 1 and 4000 characters.")
        if "content" in data:
            data["content"] = content
        return data


class MoveSerializer(serializers.Serializer):
    position = serializers.IntegerField(min_value=0)
    status = serializers.ChoiceField(choices=Task.Status.choices, required=False)


class AuthenticatedViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]


class OrganizationViewSet(AuthenticatedViewSet):
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Organization.objects.none()
        return services.organizations(self.request.user)

    def perform_create(self, serializer):
        serializer.instance = services.create_organization(
            self.request.user, **serializer.validated_data
        )

    def perform_update(self, serializer):
        services.require_role(self.request.user, serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        services.require_role(self.request.user, instance, ["OWNER"])
        instance.delete()


class ProjectViewSet(AuthenticatedViewSet):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Project.objects.none()
        return services.projects(self.request.user)

    def perform_create(self, serializer):
        item = serializer.save(created_by=self.request.user)
        services.log(self.request.user, item.organization, "created project", item.name)

    def perform_update(self, serializer):
        services.require_role(
            self.request.user, serializer.instance.organization, services.MANAGERS
        )
        serializer.save()

    def perform_destroy(self, instance):
        services.require_role(
            self.request.user, instance.organization, services.MANAGERS
        )
        instance.delete()


class TaskViewSet(AuthenticatedViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Task.objects.none()
        return services.tasks(self.request.user).order_by("position", "created_at")

    def perform_create(self, serializer):
        item = Task(created_by=self.request.user, **serializer.validated_data)
        serializer.instance = services.save_task(self.request.user, item, created=True)

    def perform_update(self, serializer):
        previous = serializer.instance.assignee_id
        for key, value in serializer.validated_data.items():
            setattr(serializer.instance, key, value)
        services.save_task(self.request.user, serializer.instance, previous)

    def perform_destroy(self, instance):
        services.log(
            self.request.user,
            instance.project.organization,
            "deleted task",
            instance.title,
        )
        instance.delete()

    @extend_schema(request=MoveSerializer, responses=TaskSerializer)
    @action(detail=True, methods=["patch"])
    def reorder(self, request, pk=None):
        item = self.get_object()
        payload = MoveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        if isinstance(request.data.get("position"), bool):
            raise serializers.ValidationError("Position must be an integer.")
        try:
            item = services.move_task(
                request.user,
                item.pk,
                payload.validated_data.get("status", item.status),
                payload.validated_data["position"],
            )
        except ModelValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return Response(self.get_serializer(item).data)


class TaskCommentViewSet(AuthenticatedViewSet):
    serializer_class = TaskCommentSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return TaskComment.objects.none()
        return TaskComment.objects.filter(task__in=services.tasks(self.request.user))

    def perform_create(self, serializer):
        item = serializer.save(author=self.request.user)
        services.log(
            self.request.user,
            item.task.project.organization,
            "commented on task",
            item.task.title,
        )
        if item.task.assignee_id != self.request.user.pk:
            services.notify(
                item.task.assignee,
                item.task.project.organization,
                f"New comment: {item.task.title}",
                kind="comments",
            )

    def check_owner(self, item):
        if item.author_id != self.request.user.pk:
            services.require_role(self.request.user, item.task.project.organization)

    def perform_update(self, serializer):
        self.check_owner(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self.check_owner(instance)
        instance.delete()
