from rest_framework import serializers
from .models import Organization, Membership, OrganizationInvitation

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'slug', 'description', 'logo', 'owner', 'created_at']
        read_only_fields = ['id', 'slug', 'owner', 'created_at']

class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = ['id', 'organization', 'user', 'role', 'joined_at']
        read_only_fields = ['id', 'organization', 'user', 'joined_at']

class OrganizationInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationInvitation
        fields = ['id', 'organization', 'invited_email', 'invited_role', 'inviter', 'created_at']
        read_only_fields = ['id', 'organization', 'inviter', 'created_at']
