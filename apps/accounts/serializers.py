from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import reverse
from rest_framework import serializers

User = get_user_model()


class AvatarURLMixin:
    def get_avatar(self, obj) -> str | None:
        if not obj.avatar:
            return None
        url = reverse("accounts:avatar", args=[obj.username])
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url


class UserSerializer(AvatarURLMixin, serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "avatar",
            "bio",
            "job_title",
            "location",
            "birth_date",
            "date_joined",
        ]
        read_only_fields = ["id", "date_joined", "username", "email"]


class PublicUserSerializer(AvatarURLMixin, serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "avatar",
            "bio",
            "job_title",
            "location",
            "date_joined",
        ]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, trim_whitespace=False
    )
    password_confirm = serializers.CharField(
        write_only=True, required=True, trim_whitespace=False
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        candidate = User(
            **{
                key: value
                for key, value in attrs.items()
                if key not in ["password", "password_confirm"]
            }
        )
        try:
            validate_password(attrs["password"], candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )
        return user


class ProfileUpdateSerializer(serializers.ModelSerializer):
    def validate_avatar(self, value):
        if value and value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Avatar must be no larger than 5 MB.")
        return value

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "avatar",
            "bio",
            "job_title",
            "location",
            "birth_date",
        ]
