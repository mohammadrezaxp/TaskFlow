from django import forms
from django.contrib.auth import get_user_model

from apps.notifications.models import NotificationPreference, TeamMessage
from apps.organizations.models import Membership, Organization
from apps.projects.models import Project
from apps.tasks.models import Task, TaskComment

from . import services


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ["name", "description"]


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "organization",
            "name",
            "description",
            "status",
            "start_date",
            "due_date",
        ]
        widgets = {
            key: forms.DateInput(attrs={"type": "date"})
            for key in ["start_date", "due_date"]
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organization"].queryset = services.organizations(user).filter(
            memberships__user=user, memberships__role__in=services.MANAGERS
        )
        if not self.instance._state.adding:
            self.fields["organization"].disabled = True

    def clean(self):
        data = super().clean()
        if (
            data.get("start_date")
            and data.get("due_date")
            and data["due_date"] < data["start_date"]
        ):
            self.add_error("due_date", "Due date must follow the start date.")
        return data


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            "project",
            "title",
            "description",
            "status",
            "priority",
            "assignee",
            "due_date",
        ]
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = services.projects(user)
        project_id = (
            self.data.get("project")
            or self.initial.get("project")
            or getattr(self.instance, "project_id", None)
        )
        org_ids = services.organizations(user).values_list("pk", flat=True)
        self.fields["assignee"].queryset = (
            get_user_model()
            .objects.filter(memberships__organization__in=org_ids)
            .distinct()
        )
        if project_id:
            try:
                project = services.projects(user).get(pk=project_id)
                self.fields["assignee"].queryset = get_user_model().objects.filter(
                    memberships__organization=project.organization, is_active=True
                )
            except (Project.DoesNotExist, ValueError, forms.ValidationError):
                self.fields["assignee"].queryset = get_user_model().objects.none()

    def clean(self):
        data = super().clean()
        project, assignee = data.get("project"), data.get("assignee")
        if (
            project
            and assignee
            and not project.organization.memberships.filter(user=assignee).exists()
        ):
            self.add_error(
                "assignee", "Assignee must belong to this project’s organization."
            )
        if (
            not self.instance._state.adding
            and project
            and self.instance.project_id != project.pk
        ):
            self.add_error("project", "Move tasks within their existing project.")
        return data


class CommentForm(forms.ModelForm):
    class Meta:
        model = TaskComment
        fields = ["content"]
        widgets = {"content": forms.Textarea(attrs={"rows": 3, "maxlength": 4000})}

    def clean_content(self):
        content = self.cleaned_data["content"].strip()
        if not content or len(content) > 4000:
            raise forms.ValidationError("Write between 1 and 4000 characters.")
        return content


class InvitationForm(forms.Form):
    email = forms.EmailField()
    role = forms.ChoiceField(
        choices=[("MEMBER", "Member"), ("MANAGER", "Manager"), ("ADMIN", "Admin")]
    )


class MessageForm(forms.ModelForm):
    class Meta:
        model = TeamMessage
        fields = ["content"]
        widgets = {"content": forms.Textarea(attrs={"rows": 2})}

    def clean_content(self):
        value = self.cleaned_data["content"].strip()
        if not value or len(value) > 4000:
            raise forms.ValidationError("Write between 1 and 4000 characters.")
        return value


class PreferenceForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        fields = ["assignments", "comments"]
