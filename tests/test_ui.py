import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

@pytest.mark.django_db
@pytest.mark.parametrize('url_name,kwargs', [
    ('dashboard', None),
    ('accounts:login', None),
    ('accounts:register', None),
    ('password_reset', None),
    ('accounts:profile', None),
    ('accounts:public-profile', {'username': 'user'}),
    ('organization-list', None),
    ('organization-create', None),
    ('organization-detail', {'pk': 1}),
    ('organization-members', {'pk': 1}),
    ('organization-invitations', {'pk': 1}),
    ('project-list', None),
    ('project-create', None),
    ('project-detail', {'pk': 1}),
    ('task-list', None),
    ('task-kanban', None),
    ('task-create', None),
    ('task-detail', {'pk': 1}),
    ('task-comments', {'pk': 1}),
    ('notification-list', None),
    ('activity-list', None),
    ('analytics', None),
    ('calendar', None),
    ('messages', None),
    ('team-list', None),
    ('settings-index', None),
    ('settings-security', None),
    ('settings-notifications', None),
])
def test_ui_page_renders(client, url_name, kwargs):
    user, _ = User.objects.get_or_create(username='orguser', defaults={'password': 'password123!'})
    client.force_login(user)

    if url_name.startswith('organization') or url_name.startswith('project') or url_name.startswith('task'):
        from apps.organizations.models import Organization, Membership
        from apps.projects.models import Project
        from apps.tasks.models import Task

        if url_name in ['organization-detail', 'organization-members', 'organization-invitations']:
            org, _ = Organization.objects.get_or_create(name='Test Org', defaults={'owner': user})
            Membership.objects.get_or_create(organization=org, user=user, defaults={'role': Membership.Role.OWNER})
            kwargs = {'pk': org.pk}
        elif url_name == 'project-detail':
            org, _ = Organization.objects.get_or_create(name='Test Org', defaults={'owner': user})
            Membership.objects.get_or_create(organization=org, user=user, defaults={'role': Membership.Role.OWNER})
            project, _ = Project.objects.get_or_create(organization=org, name='Test Project', defaults={'created_by': user})
            kwargs = {'pk': project.pk}
        elif url_name in ['task-detail', 'task-comments']:
            org, _ = Organization.objects.get_or_create(name='Test Org', defaults={'owner': user})
            Membership.objects.get_or_create(organization=org, user=user, defaults={'role': Membership.Role.OWNER})
            project, _ = Project.objects.get_or_create(organization=org, name='Test Project', defaults={'created_by': user})
            task, _ = Task.objects.get_or_create(project=project, title='Test Task', defaults={'created_by': user})
            kwargs = {'pk': task.pk}
        else:
            kwargs = None

    url = reverse(url_name, kwargs=kwargs) if kwargs else reverse(url_name)
    if url_name == 'accounts:login':
        client.logout()
        response = client.get(url)
        assert response.status_code == 200
        return

    if url_name in ['accounts:profile', 'settings-security']:
        viewer, _ = User.objects.get_or_create(username='testviewer', defaults={'password': 'password123!', 'email': 'testviewer@example.com'})
        client.force_login(viewer)
    if url_name == 'accounts:public-profile':
        User.objects.get_or_create(username='user', defaults={'email': 'user@example.com'})
    response = client.get(url)
    assert response.status_code == 200
