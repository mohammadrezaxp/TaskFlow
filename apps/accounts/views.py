from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    ProfileUpdateSerializer,
    PublicUserSerializer,
    RegisterSerializer,
    UserSerializer,
)

User = get_user_model()

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView

from .forms import CustomUserChangeForm, CustomUserCreationForm

User = get_user_model()


# --- API Views ---
class RegisterAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class CurrentUserAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return ProfileUpdateSerializer
        return UserSerializer


class PublicProfileAPIView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = PublicUserSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "username"


# --- Template Views ---
class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    extra_context = {
        "title": "Sign in",
        "subtitle": "Welcome back. Your team is waiting.",
    }


class UserRegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = "shared/auth_form.html"
    extra_context = {
        "title": "Create account",
        "subtitle": "One place for your team’s best work.",
    }
    success_url = reverse_lazy("accounts:login")


class UserProfileView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = CustomUserChangeForm
    template_name = "shared/form.html"
    extra_context = {"title": "Your profile"}
    success_url = reverse_lazy("accounts:profile")

    def get_object(self):
        return self.request.user


class PublicProfileDetailView(DetailView):
    model = User
    template_name = "accounts/public_profile.html"
    slug_field = "username"
    slug_url_kwarg = "username"
    context_object_name = "profile_user"


class SecuritySettingsView(LoginRequiredMixin, PasswordChangeView):
    template_name = "shared/form.html"
    extra_context = {"title": "Change password"}
    success_url = reverse_lazy("settings-index")


def avatar(request, username):
    from io import BytesIO

    from django.http import Http404, HttpResponse
    from django.shortcuts import get_object_or_404
    from PIL import Image, UnidentifiedImageError

    profile = get_object_or_404(User, username=username, is_active=True)
    if not profile.avatar:
        raise Http404("No avatar.")
    try:
        with profile.avatar.open("rb") as source, Image.open(source) as image:
            image.thumbnail((512, 512))
            output = BytesIO()
            image.convert("RGBA").save(output, format="PNG")
    except (
        FileNotFoundError,
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
    ):
        raise Http404("Avatar is unavailable.")
    response = HttpResponse(output.getvalue(), content_type="image/png")
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "public, max-age=300"
    return response
