import hashlib
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.activity.models import ActivityEvent
from apps.core import services
from apps.notifications.models import Notification, NotificationPreference, TeamMessage
from apps.organizations.models import Membership, Organization, OrganizationInvitation
from apps.projects.models import Project
from apps.tasks.models import Task, TaskComment

pytestmark = pytest.mark.django_db


def test_avatar_upload_and_safe_image_response(client, tmp_path, settings):
    from io import BytesIO

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    settings.MEDIA_ROOT = tmp_path
    user = get_user_model().objects.create_user(
        "avatar-user", email="avatar@example.org", password="StrongPass!957"
    )
    image = BytesIO()
    Image.new("RGB", (20, 20), "purple").save(image, format="JPEG")
    c = api(user)
    response = c.patch(
        "/accounts/api/me/",
        {
            "avatar": SimpleUploadedFile(
                "photo.jpg", image.getvalue(), content_type="image/jpeg"
            )
        },
        format="multipart",
    )
    assert response.status_code == 200
    avatar = client.get(reverse("accounts:avatar", args=[user.username]))
    assert avatar.status_code == 200
    assert avatar["Content-Type"] == "image/png"
    assert avatar.content.startswith(b"\x89PNG")
    assert "/accounts/avatar/avatar-user/" in c.get("/accounts/api/me/").data["avatar"]


def test_registration_checks_password_against_personal_fields(client):
    response = client.post(
        "/accounts/api/register/",
        {
            "username": "myuniquename",
            "email": "myuniquename@example.org",
            "password": "myuniquename",
            "password_confirm": "myuniquename",
        },
    )
    assert response.status_code == 400
    assert not get_user_model().objects.filter(username="myuniquename").exists()


@pytest.fixture
def workspace():
    User = get_user_model()
    owner = User.objects.create_user(
        "owner", email="owner@example.org", password="StrongPass!957"
    )
    member = User.objects.create_user(
        "member", email="member@example.org", password="StrongPass!957"
    )
    outsider = User.objects.create_user(
        "outsider", email="other@example.org", password="StrongPass!957"
    )
    org = services.create_organization(owner, name="Studio")
    foreign = services.create_organization(outsider, name="Private")
    Membership.objects.create(user=member, organization=org, role="MEMBER")
    project = Project.objects.create(organization=org, name="Launch", created_by=owner)
    other_project = Project.objects.create(
        organization=foreign, name="Secret", created_by=outsider
    )
    task = Task.objects.create(
        project=project, title="First task", created_by=owner, assignee=member
    )
    return dict(
        owner=owner,
        member=member,
        outsider=outsider,
        org=org,
        foreign=foreign,
        project=project,
        other_project=other_project,
        task=task,
    )


def api(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_html_organization_and_project_creation(client, workspace):
    client.force_login(workspace["owner"])
    response = client.post(
        "/organizations/new/", {"name": "Another team", "description": "Hello"}
    )
    assert response.status_code == 302
    org = Organization.objects.get(name="Another team")
    assert org.memberships.get(user=workspace["owner"]).role == "OWNER"
    response = client.post(
        "/projects/new/",
        {"name": "A project", "organization": str(org.pk), "status": "ACTIVE"},
    )
    assert response.status_code == 302
    assert Project.objects.filter(name="A project", organization=org).exists()


def test_html_task_create_comment_and_persistence(client, workspace):
    client.force_login(workspace["owner"])
    response = client.post(
        "/tasks/new/",
        {
            "title": "Ship it",
            "project": str(workspace["project"].pk),
            "status": "TODO",
            "priority": "HIGH",
            "assignee": workspace["member"].pk,
        },
    )
    assert response.status_code == 302
    task = Task.objects.get(title="Ship it")
    assert Notification.objects.filter(
        user=workspace["member"], title__contains="Ship it"
    ).exists()
    response = client.post(
        reverse("task-detail", args=[task.pk]), {"content": "Ready for review"}
    )
    assert response.status_code == 302
    assert task.comments.get().content == "Ready for review"
    assert b"Ready for review" in client.get(response.url).content


@pytest.mark.parametrize("resource", ["projects", "tasks", "task-comments"])
def test_foreign_create_relationship_is_rejected(workspace, resource):
    c = api(workspace["outsider"])
    data = {
        "projects": {"name": "attack", "organization": str(workspace["org"].pk)},
        "tasks": {"title": "attack", "project": str(workspace["project"].pk)},
        "task-comments": {"task": str(workspace["task"].pk), "content": "attack"},
    }[resource]
    response = c.post("/api/v1/" + resource + "/", data)
    assert response.status_code in (400, 403)
    assert not Task.objects.filter(title="attack").exists()


def test_foreign_relationship_update_rejected(workspace):
    response = api(workspace["owner"]).patch(
        f"/api/v1/tasks/{workspace['task'].pk}/",
        {"project": str(workspace["other_project"].pk)},
    )
    assert response.status_code == 400
    workspace["task"].refresh_from_db()
    assert workspace["task"].project_id == workspace["project"].pk


def test_member_cannot_manage_project_or_org(workspace):
    c = api(workspace["member"])
    assert (
        c.patch(
            f"/api/v1/organizations/{workspace['org'].pk}/", {"name": "changed"}
        ).status_code
        == 403
    )
    assert c.delete(f"/api/v1/projects/{workspace['project'].pk}/").status_code == 403
    assert (
        c.post(
            "/api/v1/projects/",
            {"organization": str(workspace["org"].pk), "name": "restricted"},
        ).status_code
        == 403
    )


def test_comment_edit_restricted_to_author_or_admin(workspace):
    comment = TaskComment.objects.create(
        task=workspace["task"], author=workspace["owner"], content="Original"
    )
    response = api(workspace["member"]).patch(
        f"/api/v1/task-comments/{comment.pk}/", {"content": "tampered"}
    )
    assert response.status_code == 403
    comment.refresh_from_db()
    assert comment.content == "Original"


def test_kanban_move_updates_status_and_unique_order(workspace):
    task = workspace["task"]
    second = Task.objects.create(
        project=workspace["project"], title="Second", status="DONE", position=0
    )
    response = api(workspace["member"]).patch(
        f"/api/v1/tasks/{task.pk}/reorder/", {"position": 0, "status": "DONE"}
    )
    assert response.status_code == 200
    task.refresh_from_db()
    second.refresh_from_db()
    assert (task.status, task.position, second.position) == ("DONE", 0, 1)
    assert (
        api(workspace["member"])
        .patch(f"/api/v1/tasks/{task.pk}/reorder/", {"position": -1})
        .status_code
        == 400
    )


def test_invitation_hashed_email_bound_expiring_single_use(workspace):
    invited = get_user_model().objects.create_user(
        "invited", email="invite@example.org", password="StrongPass!957"
    )
    record, token = services.invite(
        workspace["owner"], workspace["org"], invited.email, "MEMBER"
    )
    assert record.token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert token not in record.token_hash
    from django.core.exceptions import PermissionDenied

    with pytest.raises(PermissionDenied):
        services.accept_invitation(workspace["outsider"], token)
    org = services.accept_invitation(invited, token)
    assert org == workspace["org"]
    assert org.memberships.filter(user=invited).exists()
    with pytest.raises(ValidationError):
        services.accept_invitation(invited, token)


def test_expired_or_revoked_invite_rejected(workspace):
    for field, value in [
        ("expires_at", timezone.now() - timedelta(seconds=1)),
        ("revoked_at", timezone.now()),
    ]:
        record, token = services.invite(
            workspace["owner"], workspace["org"], "other@example.org", "MEMBER"
        )
        setattr(record, field, value)
        record.save()
        with pytest.raises(ValidationError):
            services.accept_invitation(workspace["outsider"], token)


def test_owner_cannot_be_removed(client, workspace):
    client.force_login(workspace["owner"])
    member = workspace["org"].memberships.get(user=workspace["owner"])
    response = client.post(
        reverse("organization-members", args=[workspace["org"].pk]),
        {"membership": str(member.pk), "action": "remove"},
    )
    assert response.status_code == 403
    assert Membership.objects.filter(pk=member.pk, role="OWNER").exists()


def test_member_removal_clears_assignments_and_access(client, workspace):
    client.force_login(workspace["owner"])
    member = workspace["org"].memberships.get(user=workspace["member"])
    response = client.post(
        reverse("organization-members", args=[workspace["org"].pk]),
        {"membership": str(member.pk), "action": "remove"},
    )
    assert response.status_code == 302
    workspace["task"].refresh_from_db()
    assert workspace["task"].assignee is None
    assert (
        api(workspace["member"])
        .get(f"/api/v1/tasks/{workspace['task'].pk}/")
        .status_code
        == 404
    )


def test_messages_and_activity_do_not_leak(client, workspace):
    TeamMessage.objects.create(
        organization=workspace["foreign"],
        author=workspace["outsider"],
        content="Confidential message",
    )
    services.log(
        workspace["outsider"],
        workspace["foreign"],
        "secret operation",
        "Confidential event",
    )
    client.force_login(workspace["member"])
    assert b"Confidential message" not in client.get("/messages/").content
    assert b"Confidential event" not in client.get("/activity/").content
    assert (
        client.get("/messages/?org=" + str(workspace["foreign"].pk)).status_code == 404
    )


def test_messages_persist_and_escape_html(client, workspace):
    client.force_login(workspace["member"])
    url = "/messages/?org=" + str(workspace["org"].pk)
    assert client.post(url, {"content": "<script>alert(1)</script>"}).status_code == 302
    response = client.get(url)
    assert b"&lt;script&gt;" in response.content
    assert b"<script>alert(1)</script>" not in response.content


def test_notification_mutations_are_user_scoped(client, workspace):
    item = Notification.objects.create(
        user=workspace["owner"],
        organization=workspace["org"],
        title="Private notification",
    )
    client.force_login(workspace["member"])
    client.post("/notifications/", {"id": item.pk})
    item.refresh_from_db()
    assert item.read_at is None
    NotificationPreference.objects.create(user=workspace["member"], assignments=False)
    services.notify(workspace["member"], workspace["org"], "Hidden assignment")
    assert not Notification.objects.filter(title="Hidden assignment").exists()


def test_password_reset_flow_generates_internal_link(client, workspace, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    response = client.post("/password-reset/", {"email": workspace["owner"].email})
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    assert "/reset/" in mail.outbox[0].body


def test_csrf_required_for_browser_writes(workspace):
    c = Client(enforce_csrf_checks=True)
    c.force_login(workspace["owner"])
    assert c.post("/tasks/new/", {"title": "Forged"}).status_code == 403


def test_anonymous_html_redirect_and_api_reject(client, workspace):
    assert client.get("/tasks/").status_code == 302
    assert client.get("/api/v1/tasks/").status_code == 401


def test_schema_and_health(client):
    assert client.get("/api/schema/").status_code == 200
    assert client.get("/health/").json()["status"] == "ok"


def test_due_date_validation_and_priority_default(workspace):
    assert (
        Task.objects.create(project=workspace["project"], title="Default").priority
        == "MEDIUM"
    )
    response = api(workspace["owner"]).post(
        "/api/v1/projects/",
        {
            "organization": str(workspace["org"].pk),
            "name": "Bad dates",
            "start_date": "2026-10-20",
            "due_date": "2026-10-01",
        },
    )
    assert response.status_code == 400


def test_failed_domain_operation_does_not_create_partial_org(workspace):
    before = Organization.objects.count()
    with patch("apps.core.services.log", side_effect=RuntimeError("failed")):
        with pytest.raises(RuntimeError):
            services.create_organization(workspace["owner"], name="Rollback")
    assert Organization.objects.count() == before
