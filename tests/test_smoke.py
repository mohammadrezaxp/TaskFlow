import pytest
from django.urls import reverse
from apps.accounts.models import User

@pytest.mark.django_db
def test_health_endpoint(client):
    response = client.get('/health/')
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "TaskFlow"}

@pytest.mark.django_db
def test_create_user():
    user = User.objects.create_user(username='testuser', email='test@example.com', password='password123')
    assert user.username == 'testuser'
    assert user.email == 'test@example.com'
    assert user.check_password('password123')
