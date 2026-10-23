from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.core import services
from apps.notifications.models import TeamMessage
from apps.organizations.models import Membership
from apps.projects.models import Project
from apps.tasks.models import Task, TaskComment


class Command(BaseCommand):
    help = "Create an idempotent fictional team and projects in a development database."

    def add_arguments(self, parser):
        parser.add_argument("--password", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo seeding is available only with DEBUG=True.")
        User = get_user_model()
        owner, created = User.objects.get_or_create(
            username="demo",
            defaults={
                "email": "demo@taskflow.local",
                "first_name": "Alex",
                "last_name": "Morgan",
                "job_title": "Product Lead",
            },
        )
        if created:
            owner.set_password(options["password"])
            owner.save()
        teammate, created = User.objects.get_or_create(
            username="sam",
            defaults={
                "email": "sam@taskflow.local",
                "first_name": "Sam",
                "last_name": "Rivera",
                "job_title": "Product Designer",
            },
        )
        if created:
            teammate.set_password(options["password"])
            teammate.save()
        org = services.organizations(owner).filter(
            name="Flow Studio"
        ).first() or services.create_organization(
            owner,
            name="Flow Studio",
            description="A small team building thoughtful digital products.",
        )
        Membership.objects.get_or_create(
            organization=org, user=teammate, defaults={"role": "MEMBER"}
        )
        today = timezone.localdate()
        for index, (name, description) in enumerate(
            [
                (
                    "Website refresh",
                    "A clearer story, a faster site, and a better first impression.",
                ),
                (
                    "Mobile workspace",
                    "Bring the team’s essential workflows to a focused mobile experience.",
                ),
                (
                    "Design system",
                    "Shared foundations for consistent and accessible product experiences.",
                ),
            ]
        ):
            project, _ = Project.objects.get_or_create(
                organization=org,
                name=name,
                defaults={
                    "description": description,
                    "created_by": owner,
                    "status": "ACTIVE",
                    "start_date": today - timedelta(days=12),
                    "due_date": today + timedelta(days=20 + index * 5),
                },
            )
            for n, title in enumerate(
                [
                    "Define success metrics",
                    "Map the user journey",
                    "Review interface concepts",
                    "Build the core experience",
                    "Test keyboard navigation",
                    "Prepare the release checklist",
                ]
            ):
                task, created = Task.objects.get_or_create(
                    project=project,
                    title=title,
                    defaults={
                        "description": "Document the approach, share it with the team, and agree on the next step.",
                        "created_by": owner,
                        "assignee": owner if n % 2 == 0 else teammate,
                        "status": [
                            "DONE",
                            "IN_PROGRESS",
                            "IN_REVIEW",
                            "TODO",
                            "TODO",
                            "DONE",
                        ][n],
                        "priority": [
                            "HIGH",
                            "MEDIUM",
                            "HIGH",
                            "MEDIUM",
                            "LOW",
                            "MEDIUM",
                        ][n],
                        "due_date": today + timedelta(days=n - 1 + index * 2),
                        "position": n,
                    },
                )
                if created:
                    services.log(owner, org, "created task", title)
                    if task.assignee_id != owner.pk:
                        services.notify(
                            teammate,
                            org,
                            "You were assigned: " + title,
                            "/tasks/" + str(task.pk) + "/",
                        )
        if not org.messages.exists():
            TeamMessage.objects.create(
                organization=org,
                author=owner,
                content="Welcome to Flow Studio. Let’s build something we’re proud of.",
            )
            TeamMessage.objects.create(
                organization=org,
                author=teammate,
                content="The first design review is ready. Add feedback directly to the tasks.",
            )
        self.stdout.write(
            self.style.SUCCESS(
                "Demo ready. Sign in as demo or sam using the password supplied on first creation."
            )
        )
