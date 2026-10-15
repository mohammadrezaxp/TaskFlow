import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

@pytest.mark.django_db
def test_user_registration_api():
    client = APIClient()
    url = reverse('accounts:api-register')
    data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'SecurePassword123!',
        'password_confirm': 'SecurePassword123!',
        'first_name': 'Test',
        'last_name': 'User'
    }
    response = client.post(url, data, format='json')
    assert response.status_code == 201
    assert User.objects.filter(username='testuser').exists()

@pytest.mark.django_db
def test_jwt_token_obtain_and_refresh():
    user = User.objects.create_user(username='jwtuser', email='jwt@example.com', password='Password123!')
    client = APIClient()
    url = reverse('accounts:token_obtain_pair')
    response = client.post(url, {'username': 'jwtuser', 'password': 'Password123!'}, format='json')
    assert response.status_code == 200
    data = response.json()
    assert 'access' in data
    assert 'refresh' in data

    refresh_url = reverse('accounts:token_refresh')
    refresh_response = client.post(refresh_url, {'refresh': data['refresh']}, format='json')
    assert refresh_response.status_code == 200
    assert 'access' in refresh_response.json()

@pytest.mark.django_db
def test_current_user_profile_update():
    user = User.objects.create_user(username='profileuser', email='profile@example.com', password='Password123!')
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse('accounts:api-me')
    
    # Get
    response = client.get(url)
    assert response.status_code == 200
    assert response.json()['username'] == 'profileuser'

    # Update
    response = client.patch(url, {'bio': 'Senior Developer', 'job_title': 'Architect'}, format='json')
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.bio == 'Senior Developer'
    assert user.job_title == 'Architect'

@pytest.mark.django_db
def test_public_profile():
    user = User.objects.create_user(username='publicuser', email='public@example.com', password='Password123!', bio='Public Bio')
    client = APIClient()
    url = reverse('accounts:api-public-profile', kwargs={'username': 'publicuser'})
    response = client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert data['username'] == 'publicuser'
    assert data['bio'] == 'Public Bio'
    # Ensure sensitive fields like email are NOT exposed publicly
    assert 'email' not in data
