import pytest
from django.urls import reverse

@pytest.mark.django_db
@pytest.mark.parametrize('url_name,kwargs', [
    ('dashboard', None),
    ('login', None),
    ('register', None),
    ('password-reset', None),
    ('profile', None),
    ('public-profile', None),
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
    response = client.get(url)
    assert response.status_code == 200
