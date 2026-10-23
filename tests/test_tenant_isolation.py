import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.organizations.models import Membership, Organization
from apps.projects.models import Project
from apps.tasks.models import Task, TaskComment

User = get_user_model()


@pytest.mark.django_db
class TestTenantIsolationAndSecurity:
    def setup_method(self):
        self.user1 = User.objects.create_user(
            username="user1", email="user1@test.com", password="password123!"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@test.com", password="password123!"
        )

        self.org1 = Organization.objects.create(name="Org One", owner=self.user1)
        Membership.objects.create(
            organization=self.org1, user=self.user1, role=Membership.Role.OWNER
        )

        self.org2 = Organization.objects.create(name="Org Two", owner=self.user2)
        Membership.objects.create(
            organization=self.org2, user=self.user2, role=Membership.Role.OWNER
        )

        self.project1 = Project.objects.create(
            organization=self.org1, name="Project One", created_by=self.user1
        )
        self.project2 = Project.objects.create(
            organization=self.org2, name="Project Two", created_by=self.user2
        )

        self.task1 = Task.objects.create(
            project=self.project1, title="Task One", created_by=self.user1
        )
        self.task2 = Task.objects.create(
            project=self.project2, title="Task Two", created_by=self.user2
        )

        self.comment1 = TaskComment.objects.create(
            task=self.task1, author=self.user1, content="Comment One"
        )

        self.client1 = APIClient()
        self.client1.force_authenticate(user=self.user1)

        self.client2 = APIClient()
        self.client2.force_authenticate(user=self.user2)

    def test_cross_tenant_project_access(self):
        # User 2 tries to view Project 1
        url = f"/api/v1/projects/{self.project1.id}/"
        response = self.client2.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cross_tenant_task_access(self):
        # User 2 tries to view Task 1
        url = f"/api/v1/tasks/{self.task1.id}/"
        response = self.client2.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cross_tenant_comment_access(self):
        # User 2 tries to view Comment 1 directly or via task
        url = f"/api/v1/task-comments/"
        response = self.client2.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 0

    def test_unauthorized_kanban_move(self):
        # User 2 tries to reorder Task 1
        url = f"/api/v1/tasks/{self.task1.id}/reorder/"
        response = self.client2.patch(url, {"position": 1})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_task_assignee_validation(self):
        # User 1 tries to assign Task 1 to User 2 (who is not in Org 1)
        url = f"/api/v1/tasks/{self.task1.id}/"
        response = self.client1.patch(url, {"assignee": self.user2.id})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
