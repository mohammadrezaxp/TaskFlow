from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Organization, Membership
from .serializers import OrganizationSerializer, MembershipSerializer
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

class IsMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return Membership.objects.filter(organization=obj, user=request.user).exists()

class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Organization.objects.filter(memberships__user=self.request.user)

    def perform_create(self, serializer):
        org = serializer.save(owner=self.request.user)
        Membership.objects.create(organization=org, user=self.request.user, role=Membership.Role.OWNER)

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsMember()]
        return super().get_permissions()

# --- Template Views ---
class OrganizationListView(LoginRequiredMixin, ListView):
    model = Organization
    template_name = 'organizations/list.html'
    context_object_name = 'organizations'

    def get_queryset(self):
        return Organization.objects.filter(memberships__user=self.request.user)

class OrganizationCreateView(LoginRequiredMixin, CreateView):
    model = Organization
    fields = ['name', 'description', 'logo']
    template_name = 'organizations/form.html'
    success_url = reverse_lazy('organization-list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        Membership.objects.create(organization=self.object, user=self.request.user, role=Membership.Role.OWNER)
        return response

class OrganizationDetailView(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = 'organizations/detail.html'
    context_object_name = 'organization'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        return Organization.objects.filter(memberships__user=self.request.user)

class OrganizationMembersView(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = 'organizations/members.html'
    context_object_name = 'organization'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        return Organization.objects.filter(memberships__user=self.request.user)

class OrganizationInvitationsView(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = 'organizations/invitations.html'
    context_object_name = 'organization'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        return Organization.objects.filter(memberships__user=self.request.user)
