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
    url = reverse(url_name, kwargs=kwargs) if kwargs else reverse(url_name)
    if url_name in ['accounts:profile', 'settings-security']:
        user = User.objects.create_user(username='testviewer', password='password123!')
        client.force_login(user)
    if url_name == 'accounts:public-profile':
        User.objects.get_or_create(username='user')
    response = client.get(url)
    assert response.status_code == 200
