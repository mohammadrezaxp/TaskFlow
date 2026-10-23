import calendar
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404 as django_get_object_or_404
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.activity.models import ActivityEvent
from apps.notifications.models import Notification, NotificationPreference, TeamMessage
from apps.organizations.models import Membership, Organization, OrganizationInvitation
from apps.projects.models import Project
from apps.tasks.models import Task, TaskComment

from . import services
from .forms import (
    CommentForm,
    InvitationForm,
    MessageForm,
    OrganizationForm,
    PreferenceForm,
    ProjectForm,
    TaskForm,
)


def get_object_or_404(queryset, **lookups):
    try:
        return django_get_object_or_404(queryset, **lookups)
    except (ValidationError, ValueError, TypeError):
        raise Http404("Invalid resource identifier.")


def page(request, template, **context):
    status_code = context.pop("status_code", 200)
    return render(request, template, context, status=status_code)


def paginate(request, queryset):
    return Paginator(queryset, 20).get_page(request.GET.get("page"))


def health(request):
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"status": "unhealthy", "app": "TaskFlow"}, status=503)
    return JsonResponse({"status": "ok", "app": "TaskFlow"})


@login_required
def dashboard(request):
    work = services.tasks(request.user)
    today = timezone.localdate()
    stats = {
        "total": work.count(),
        "done": work.filter(status="DONE").count(),
        "overdue": work.exclude(status="DONE").filter(due_date__lt=today).count(),
        "projects": services.projects(request.user).exclude(status="ARCHIVED").count(),
    }
    stats["progress"] = (
        round(stats["done"] * 100 / stats["total"]) if stats["total"] else 0
    )
    return page(
        request,
        "dashboard/index.html",
        stats=stats,
        assigned=work.filter(assignee=request.user)
        .exclude(status="DONE")
        .order_by("due_date", "-priority")[:6],
        projects=services.projects(request.user)
        .annotate(
            task_count=Count("tasks"),
            done_count=Count("tasks", filter=Q(tasks__status="DONE")),
        )
        .order_by("-updated_at")[:4],
        events=ActivityEvent.objects.filter(
            organization__in=services.organizations(request.user)
        ).select_related("actor")[:5],
    )


class OrganizationListView(LoginRequiredMixin, ListView):
    template_name = "organizations/list.html"
    context_object_name = "items"
    paginate_by = 12

    def get_queryset(self):
        return (
            services.organizations(self.request.user)
            .annotate(
                member_count=Count("memberships", distinct=True),
                project_count=Count("projects", distinct=True),
            )
            .order_by("name")
        )


class OrganizationCreateView(LoginRequiredMixin, CreateView):
    template_name = "shared/form.html"
    form_class = OrganizationForm
    extra_context = {"title": "Create organization"}

    def form_valid(self, form):
        item = services.create_organization(self.request.user, **form.cleaned_data)
        messages.success(
            self.request, "Organization created. Invite your team to get started."
        )
        return redirect("organization-detail", pk=item.pk)


class OrganizationDetailView(LoginRequiredMixin, DetailView):
    template_name = "organizations/detail.html"
    context_object_name = "organization"

    def get_queryset(self):
        return services.organizations(self.request.user)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["projects"] = services.projects(self.request.user).filter(
            organization=self.object
        )
        data["can_manage"] = (
            services.role(self.request.user, self.object) in services.ADMINS
        )
        return data


class OrganizationMembersView(LoginRequiredMixin, View):
    def get(self, request, pk):
        org = get_object_or_404(services.organizations(request.user), pk=pk)
        return page(
            request,
            "organizations/members.html",
            organization=org,
            items=org.memberships.select_related("user").order_by("joined_at"),
            can_manage=services.role(request.user, org) in services.ADMINS,
            roles=[("MEMBER", "Member"), ("MANAGER", "Manager"), ("ADMIN", "Admin")],
        )

    @transaction.atomic
    def post(self, request, pk):
        org = get_object_or_404(
            services.organizations(request.user).select_for_update(), pk=pk
        )
        services.require_role(request.user, org)
        member = get_object_or_404(
            org.memberships.select_for_update(), pk=request.POST.get("membership")
        )
        if member.role == "OWNER" or member.user_id == request.user.pk:
            raise PermissionDenied(
                "The owner and your own role cannot be changed here."
            )
        if (
            member.role == "ADMIN" or request.POST.get("role") == "ADMIN"
        ) and services.role(request.user, org) != "OWNER":
            raise PermissionDenied("Only the owner can manage administrators.")
        if request.POST.get("action") == "remove":
            Task.objects.filter(project__organization=org, assignee=member.user).update(
                assignee=None
            )
            member.delete()
            services.log(request.user, org, "removed member", member.user.username)
        else:
            value = request.POST.get("role")
            if value not in ["MEMBER", "MANAGER", "ADMIN"]:
                raise PermissionDenied("Invalid role.")
            member.role = value
            member.save(update_fields=["role"])
            services.log(request.user, org, "changed member role", member.user.username)
        messages.success(request, "Membership updated.")
        return redirect("organization-members", pk=pk)


class OrganizationInvitationsView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.org = get_object_or_404(
            services.organizations(request.user), pk=kwargs["pk"]
        )
        services.require_role(request.user, self.org)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        return self.show(request, InvitationForm())

    def show(self, request, form, invite_url=None):
        return page(
            request,
            "organizations/invitations.html",
            organization=self.org,
            form=form,
            items=self.org.invitations.order_by("-created_at")[:50],
            invite_url=invite_url,
        )

    def post(self, request, pk):
        if request.POST.get("revoke"):
            invitation = get_object_or_404(
                self.org.invitations, pk=request.POST["revoke"], accepted_at=None
            )
            invitation.revoked_at = timezone.now()
            invitation.save(update_fields=["revoked_at"])
            messages.success(request, "Invitation revoked.")
            return redirect("organization-invitations", pk=pk)
        form = InvitationForm(request.POST)
        if form.is_valid():
            try:
                record, token = services.invite(
                    request.user,
                    self.org,
                    form.cleaned_data["email"],
                    form.cleaned_data["role"],
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                return self.show(
                    request,
                    InvitationForm(),
                    request.build_absolute_uri(
                        reverse("invitation-accept", args=[token])
                    ),
                )
        return self.show(request, form)


@login_required
def invitation_accept(request, token):
    if request.method == "POST":
        try:
            org = services.accept_invitation(request.user, token)
        except ValidationError as exc:
            return page(
                request,
                "shared/notice.html",
                title="Invitation unavailable",
                detail=" ".join(exc.messages),
                status_code=400,
            )
        messages.success(request, "You joined the organization.")
        return redirect("organization-detail", pk=org.pk)
    return page(request, "organizations/accept.html")


@login_required
def project_list(request):
    query = services.projects(request.user).annotate(
        task_count=Count("tasks"),
        done_count=Count("tasks", filter=Q(tasks__status="DONE")),
    )
    if request.GET.get("q"):
        query = query.filter(name__icontains=request.GET["q"])
    if request.GET.get("status"):
        query = query.filter(status=request.GET["status"])
    return page(
        request,
        "projects/list.html",
        items=paginate(request, query.order_by("-updated_at")),
        statuses=Project.Status.choices,
    )


@login_required
def project_form(request, pk=None):
    item = get_object_or_404(services.projects(request.user), pk=pk) if pk else None
    if item:
        services.require_role(request.user, item.organization, services.MANAGERS)
    form = ProjectForm(request.POST or None, user=request.user, instance=item)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        if not item.created_by_id:
            item.created_by = request.user
        item.save()
        services.log(request.user, item.organization, "saved project", item.name)
        messages.success(request, "Project saved.")
        return redirect("project-detail", pk=item.pk)
    return page(
        request,
        "shared/form.html",
        form=form,
        title="Edit project" if pk else "Create project",
    )


@login_required
def project_detail(request, pk):
    item = get_object_or_404(services.projects(request.user), pk=pk)
    return page(
        request,
        "projects/detail.html",
        project=item,
        items=services.tasks(request.user)
        .filter(project=item)
        .order_by("position", "created_at"),
        can_manage=services.role(request.user, item.organization) in services.MANAGERS,
    )


@login_required
def task_list(request):
    query = services.tasks(request.user)
    if request.GET.get("q"):
        query = query.filter(
            Q(title__icontains=request.GET["q"])
            | Q(description__icontains=request.GET["q"])
        )
    if request.GET.get("status") in Task.Status.values:
        query = query.filter(status=request.GET["status"])
    if request.GET.get("mine"):
        query = query.filter(assignee=request.user)
    return page(
        request,
        "tasks/list.html",
        items=paginate(request, query.order_by("position", "-created_at")),
        statuses=Task.Status.choices,
    )


@login_required
def task_form(request, pk=None):
    item = get_object_or_404(services.tasks(request.user), pk=pk) if pk else None
    previous = item.assignee_id if item else None
    form = TaskForm(
        request.POST or None,
        user=request.user,
        instance=item,
        initial={"project": request.GET.get("project")} if not item else None,
    )
    if request.method == "POST" and form.is_valid():
        task = form.save(commit=False)
        if not pk:
            task.created_by = request.user
        services.save_task(request.user, task, previous, created=not pk)
        messages.success(request, "Task saved.")
        return redirect("task-detail", pk=task.pk)
    return page(
        request,
        "shared/form.html",
        form=form,
        title="Edit task" if pk else "Create task",
    )


@login_required
@transaction.atomic
def task_detail(request, pk):
    item = get_object_or_404(services.tasks(request.user), pk=pk)
    form = CommentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        comment = form.save(commit=False)
        comment.task = item
        comment.author = request.user
        comment.save()
        services.log(
            request.user, item.project.organization, "commented on task", item.title
        )
        if item.assignee_id != request.user.pk:
            services.notify(
                item.assignee,
                item.project.organization,
                f"New comment: {item.title}",
                reverse("task-detail", args=[pk]),
                kind="comments",
            )
        return redirect("task-detail", pk=pk)
    return page(
        request,
        "tasks/detail.html",
        task=item,
        form=form,
        comments=item.comments.select_related("author").order_by("created_at"),
    )


class KanbanView(LoginRequiredMixin, View):
    def get(self, request):
        query = services.tasks(request.user)
        project = None
        if request.GET.get("project"):
            project = get_object_or_404(
                services.projects(request.user), pk=request.GET["project"]
            )
            query = query.filter(project=project)
        return page(
            request,
            "tasks/kanban.html",
            columns=[
                {
                    "name": label,
                    "status": status,
                    "tasks": query.filter(status=status).order_by(
                        "position", "created_at"
                    ),
                }
                for status, label in Task.Status.choices
            ],
            projects=services.projects(request.user),
            selected=project,
        )


@login_required
def delete_resource(request, kind, pk):
    query = {
        "task": services.tasks(request.user),
        "project": services.projects(request.user),
        "organization": services.organizations(request.user),
    }[kind]
    item = get_object_or_404(query, pk=pk)
    org = (
        item
        if kind == "organization"
        else item.organization if kind == "project" else item.project.organization
    )
    if kind != "task":
        services.require_role(
            request.user,
            org,
            ["OWNER"] if kind == "organization" else services.MANAGERS,
        )
    if request.method == "POST":
        if kind != "organization":
            services.log(request.user, org, "deleted " + kind, str(item))
        item.delete()
        messages.success(request, kind.title() + " deleted.")
        return redirect(
            {
                "task": "task-list",
                "project": "project-list",
                "organization": "organization-list",
            }[kind]
        )
    return page(request, "shared/confirm.html", item=item)


@login_required
def notifications(request):
    query = Notification.objects.filter(
        user=request.user, organization__in=services.organizations(request.user)
    )
    if request.method == "POST":
        if request.POST.get("id"):
            query = query.filter(pk=request.POST["id"])
        query.filter(read_at=None).update(read_at=timezone.now())
        return redirect("notification-list")
    return page(request, "notifications/list.html", items=paginate(request, query))


@login_required
def activity(request):
    query = ActivityEvent.objects.filter(
        organization__in=services.organizations(request.user)
    ).select_related("actor", "organization")
    return page(request, "activity/list.html", items=paginate(request, query))


@login_required
def team(request):
    query = (
        Membership.objects.filter(organization__in=services.organizations(request.user))
        .select_related("user", "organization")
        .order_by("organization__name", "user__username")
    )
    return page(request, "team/list.html", items=paginate(request, query))


@login_required
def messaging(request):
    orgs = services.organizations(request.user).order_by("name")
    org = (
        get_object_or_404(orgs, pk=request.GET["org"])
        if request.GET.get("org")
        else orgs.first()
    )
    form = MessageForm(request.POST or None)
    if request.method == "POST":
        if org is None:
            raise PermissionDenied("Join an organization first.")
        if form.is_valid():
            item = form.save(commit=False)
            item.organization = org
            item.author = request.user
            item.save()
            return redirect(reverse("messages") + "?org=" + str(org.pk))
    items = (
        list(org.messages.select_related("author").order_by("-created_at")[:100])[::-1]
        if org
        else []
    )
    return page(
        request,
        "messages/index.html",
        organizations=orgs,
        organization=org,
        items=items,
        form=form,
    )


@login_required
def analytics(request):
    query = services.tasks(request.user)
    total = query.count()
    done = query.filter(status="DONE").count()
    status_counts = {
        row["status"]: row["count"]
        for row in query.values("status").annotate(count=Count("id"))
    }
    rows = [
        {
            "label": label,
            "count": status_counts.get(value, 0),
            "percent": round(status_counts.get(value, 0) * 100 / total) if total else 0,
        }
        for value, label in Task.Status.choices
    ]
    return page(
        request,
        "analytics/index.html",
        total=total,
        done=done,
        rows=rows,
        completion=round(done * 100 / total) if total else 0,
        projects=services.projects(request.user)
        .annotate(
            total=Count("tasks"), done=Count("tasks", filter=Q(tasks__status="DONE"))
        )
        .order_by("name"),
    )


@login_required
def calendar_view(request):
    today = timezone.localdate()
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
        if not 1900 <= year <= 2100 or not 1 <= month <= 12:
            raise ValueError
    except ValueError:
        year, month = today.year, today.month
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    by_day = {}
    for task in (
        services.tasks(request.user)
        .filter(due_date__range=[first, last])
        .order_by("due_date", "title")
    ):
        by_day.setdefault(task.due_date, []).append(task)
    weeks = [
        [
            {
                "date": day,
                "tasks": by_day.get(day, []),
                "today": day == today,
                "in_month": day.month == month,
            }
            for day in week
        ]
        for week in calendar.Calendar().monthdatescalendar(year, month)
    ]
    return page(
        request,
        "calendar/index.html",
        weeks=weeks,
        month_label=first.strftime("%B %Y"),
        previous=first - timedelta(days=1),
        next=last + timedelta(days=1),
    )


@login_required
def preferences(request):
    item, _ = NotificationPreference.objects.get_or_create(user=request.user)
    form = PreferenceForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Notification preferences saved.")
        return redirect("settings-notifications")
    return page(
        request, "shared/form.html", title="Notification preferences", form=form
    )


@login_required
def settings_index(request):
    return page(request, "settings/index.html")
