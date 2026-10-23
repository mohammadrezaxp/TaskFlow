from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    OrganizationCreateView,
    OrganizationDetailView,
    OrganizationInvitationsView,
    OrganizationListView,
    OrganizationMembersView,
    OrganizationViewSet,
)

router = DefaultRouter()
router.register(r"organizations", OrganizationViewSet, basename="organization")

urlpatterns = [
    path("api/v1/", include(router.urls)),
    path("organizations/", OrganizationListView.as_view(), name="organization-list"),
    path(
        "organizations/new/",
        OrganizationCreateView.as_view(),
        name="organization-create",
    ),
    path(
        "organizations/<uuid:pk>/",
        OrganizationDetailView.as_view(),
        name="organization-detail",
    ),
    path(
        "organizations/<uuid:pk>/members/",
        OrganizationMembersView.as_view(),
        name="organization-members",
    ),
    path(
        "organizations/<uuid:pk>/invitations/",
        OrganizationInvitationsView.as_view(),
        name="organization-invitations",
    ),
]
