import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.organizations.models import Membership, Organization
from apps.projects.models import Project
from apps.tasks.models import Task

User = get_user_model()


@pytest.mark.django_db
class TestPhase5:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="p5user", password="password123!")
        self.client.force_authenticate(user=self.user)
        self.org = Organization.objects.create(name="P5 Org", owner=self.user)
        Membership.objects.create(
            organization=self.org, user=self.user, role=Membership.Role.OWNER
        )

    def test_project_crud(self):
        # Create
        response = self.client.post(
            "/api/v1/projects/",
            {
                "organization": str(self.org.id),
                "name": "Test Project",
                "status": "ACTIVE",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        project_id = response.data["id"]

        # List
        response = self.client.get("/api/v1/projects/")
        assert response.status_code == status.HTTP_200_OK
        assert (
            len(
                response.data["results"]
                if "results" in response.data
                else response.data
            )
            == 1
        )

        # Detail
        response = self.client.get(f"/api/v1/projects/{project_id}/")
        assert response.status_code == status.HTTP_200_OK

    def test_task_crud_and_reorder(self):
        project = Project.objects.create(
            organization=self.org, name="Task Proj", created_by=self.user
        )

        # Create Task
        response = self.client.post(
            "/api/v1/tasks/",
            {
                "project": str(project.id),
                "title": "Test Task",
                "status": "TODO",
                "priority": "MEDIUM",
                "position": 0,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        task_id = response.data["id"]

        # Reorder Task
        response = self.client.patch(
            f"/api/v1/tasks/{task_id}/reorder/", {"position": 1}
        )
        assert response.status_code == status.HTTP_200_OK
