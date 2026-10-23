from django.contrib.auth.views import LogoutView
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    CurrentUserAPIView,
    PublicProfileAPIView,
    PublicProfileDetailView,
    RegisterAPIView,
    SecuritySettingsView,
    UserLoginView,
    UserProfileView,
    UserRegisterView,
    avatar,
)

app_name = "accounts"

urlpatterns = [
    path("avatar/<str:username>/", avatar, name="avatar"),
    # API
    path("api/register/", RegisterAPIView.as_view(), name="api-register"),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/me/", CurrentUserAPIView.as_view(), name="api-me"),
    path(
        "api/profile/<str:username>/",
        PublicProfileAPIView.as_view(),
        name="api-public-profile",
    ),
    # Template
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", UserRegisterView.as_view(), name="register"),
    path("profile/", UserProfileView.as_view(), name="profile"),
    path(
        "profile/<str:username>/",
        PublicProfileDetailView.as_view(),
        name="public-profile",
    ),
    path(
        "settings/security/", SecuritySettingsView.as_view(), name="settings-security"
    ),
]
