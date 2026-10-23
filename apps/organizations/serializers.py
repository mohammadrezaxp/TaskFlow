from rest_framework import serializers

from apps.core.api import OrganizationSerializer

from .models import Membership


class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = ["id", "organization", "user", "role"]
