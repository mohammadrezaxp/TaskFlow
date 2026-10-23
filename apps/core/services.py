"""Tenant policy and transactional domain operations shared by HTML and API views."""

import hashlib
import secrets
from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F
from django.urls import reverse
from django.utils import timezone

from apps.activity.models import ActivityEvent
from apps.notifications.models import Notification, NotificationPreference
from apps.organizations.models import Membership, Organization, OrganizationInvitation
from apps.projects.models import Project
from apps.tasks.models import Task

MANAGERS = ["OWNER", "ADMIN", "MANAGER"]
ADMINS = ["OWNER", "ADMIN"]


def organizations(user):
    # Keep the outer query lockable on PostgreSQL: DISTINCT cannot be combined
    # with FOR UPDATE. The membership subquery preserves tenant scope without
    # multiplying organization rows or locking joined membership rows.
    member_orgs = Membership.objects.filter(user=user).values("organization_id")
    return Organization.objects.filter(pk__in=member_orgs)


def projects(user):
    return (
        Project.objects.filter(organization__in=organizations(user))
        .select_related("organization")
        .distinct()
    )


def tasks(user):
    return (
        Task.objects.filter(project__organization__in=organizations(user))
        .select_related("project", "project__organization", "assignee")
        .distinct()
    )


def role(user, organization):
    return (
        Membership.objects.filter(user=user, organization=organization)
        .values_list("role", flat=True)
        .first()
    )


def require_role(user, organization, allowed=ADMINS):
    if role(user, organization) not in allowed:
        raise PermissionDenied("Your organization role does not allow this action.")


def log(user, org, verb, label):
    ActivityEvent.objects.create(
        actor=user, organization=org, verb=verb, label=str(label)[:255]
    )


def notify(user, org, title, url="", kind="assignments"):
    if not user or not Membership.objects.filter(user=user, organization=org).exists():
        return
    preference = NotificationPreference.objects.filter(user=user).first()
    if preference and not getattr(preference, kind):
        return
    Notification.objects.create(user=user, organization=org, title=title[:255], url=url)


@transaction.atomic
def create_organization(user, **data):
    org = Organization.objects.create(owner=user, **data)
    Membership.objects.create(user=user, organization=org, role="OWNER")
    log(user, org, "created organization", org.name)
    return org


@transaction.atomic
def invite(user, org, email, invited_role):
    require_role(user, org)
    if invited_role not in ["ADMIN", "MANAGER", "MEMBER"]:
        raise ValidationError("Owner access cannot be granted by invitation.")
    if role(user, org) != "OWNER" and invited_role == "ADMIN":
        raise PermissionDenied("Only the owner can invite administrators.")
    if org.memberships.filter(user__email__iexact=email).exists():
        raise ValidationError("This user is already a member.")
    raw = secrets.token_urlsafe(32)
    record = OrganizationInvitation.objects.create(
        organization=org,
        inviter=user,
        invited_email=email.lower(),
        invited_role=invited_role,
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        expires_at=timezone.now() + timedelta(days=7),
    )
    log(user, org, "invited member", email)
    return record, raw


@transaction.atomic
def accept_invitation(user, raw):
    try:
        invitation = OrganizationInvitation.objects.select_for_update().get(
            token_hash=hashlib.sha256(raw.encode()).hexdigest()
        )
    except OrganizationInvitation.DoesNotExist:
        raise ValidationError("Invitation not found.")
    if (
        invitation.accepted_at
        or invitation.revoked_at
        or invitation.expires_at <= timezone.now()
    ):
        raise ValidationError("Invitation has expired or has already been used.")
    if user.email.lower() != invitation.invited_email.lower():
        raise PermissionDenied(
            "Log in with the email address this invitation was sent to."
        )
    Membership.objects.get_or_create(
        organization=invitation.organization,
        user=user,
        defaults={"role": invitation.invited_role},
    )
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["accepted_at"])
    log(user, invitation.organization, "joined organization", user.username)
    return invitation.organization


@transaction.atomic
def save_task(user, instance, previous_assignee=None, created=False):
    instance.save()
    org = instance.project.organization
    log(user, org, "created task" if created else "updated task", instance.title)
    if (
        instance.assignee_id
        and instance.assignee_id != previous_assignee
        and instance.assignee_id != user.pk
    ):
        notify(
            instance.assignee,
            org,
            f"You were assigned: {instance.title}",
            reverse("task-detail", args=[instance.pk]),
        )
    return instance


@transaction.atomic
def move_task(user, task_id, status, position):
    # Lock the project before its tasks so concurrent moves use one stable sequence.
    task = tasks(user).get(pk=task_id)
    Project.objects.select_for_update().get(pk=task.project_id)
    task = Task.objects.select_for_update().get(pk=task.pk)
    if (
        status not in Task.Status.values
        or not isinstance(position, int)
        or position < 0
    ):
        raise ValidationError("Use a valid status and a non-negative position.")
    peers = list(
        Task.objects.filter(project=task.project, status=status)
        .exclude(pk=task.pk)
        .order_by("position", "created_at", "pk")
    )
    peers.insert(min(position, len(peers)), task)
    task.status = status
    task.save(update_fields=["status", "updated_at"])
    for index, item in enumerate(peers):
        Task.objects.filter(pk=item.pk).update(position=index)
    log(user, task.project.organization, "moved task", task.title)
    task.refresh_from_db()
    return task
