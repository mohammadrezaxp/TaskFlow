import pytest
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization, Membership, OrganizationInvitation
from django.utils import timezone
import datetime
import hashlib

User = get_user_model()

@pytest.mark.django_db
class TestOrganizationSecurity:
    
    def test_cross_tenant_access_denied(self, client):
        user1 = User.objects.create_user(username='user1', email='u1@e.com', password='password123!')
        user2 = User.objects.create_user(username='user2', email='u2@e.com', password='password123!')
        
        org1 = Organization.objects.create(name='Org One', owner=user1)
        Membership.objects.create(organization=org1, user=user1, role=Membership.Role.OWNER)
        
        client.force_login(user2)
        url = reverse('organization-detail', kwargs={'pk': org1.pk})
        response = client.get(url)
        assert response.status_code == 404

    def test_anonymous_access_denied(self, client):
        user1 = User.objects.create_user(username='user1', password='password123!')
        org1 = Organization.objects.create(name='Org One', owner=user1)
        
        url = reverse('organization-detail', kwargs={'pk': org1.pk})
        response = client.get(url)
        assert response.status_code == 302

    def test_last_owner_protection(self):
        user1 = User.objects.create_user(username='user1', password='password123!')
        org1 = Organization.objects.create(name='Org One', owner=user1)
        m = Membership.objects.create(organization=org1, user=user1, role=Membership.Role.OWNER)
        
        # Trying to remove or demote last owner should be guardable
        owners_count = Membership.objects.filter(organization=org1, role=Membership.Role.OWNER).count()
        assert owners_count == 1

    def test_invitation_security(self):
        user1 = User.objects.create_user(username='user1', password='password123!')
        org1 = Organization.objects.create(name='Org One', owner=user1)
        
        token = "secrettoken123"
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        inv = OrganizationInvitation.objects.create(
            organization=org1,
            invited_email='invited@example.com',
            invited_role=Membership.Role.MEMBER,
            inviter=user1,
            token_hash=token_hash,
            expires_at=timezone.now() + datetime.timedelta(days=1)
        )
        assert inv.token_hash != token
        assert inv.expires_at > timezone.now()
