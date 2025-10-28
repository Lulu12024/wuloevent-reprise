# -*- coding: utf-8 -*-
"""
Created on August 28 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
import logging

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.serializers import PasswordField
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from apps.notifications.models import MobileDevice
from apps.users.backend import EmailOrPhoneAuthenticationBackend
from apps.users.models import (
    User,
)
from apps.users.serializers import AdminUserSerializer, UserSerializer
from apps.utils.validators import PhoneNumberValidator
from apps.xlib.error_util import ErrorUtil, ErrorEnum

logger = logging.getLogger(__name__)


class TokenObtainSerializer(serializers.Serializer):

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass

    default_error_messages = {
        "no_active_account": "Aucun compte trouvé avec ces identifiants"
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["phone"] = serializers.CharField(
            required=False, validators=[PhoneNumberValidator()]
        )
        self.fields["email"] = serializers.EmailField(required=False)
        self.fields["password"] = PasswordField()

    def validate(self, attrs):
        phone, email = None, None

        if "phone" in attrs:
            phone = attrs["phone"]
        elif "email" in attrs:
            email = attrs["email"]
        else:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.EMAIL_OR_PHONE_SHOULD_BE_SET),
                code=ErrorEnum.EMAIL_OR_PHONE_SHOULD_BE_SET.value,
            )
        authenticate_kwargs = {
            "phone": phone,
            "email": email,
            "password": attrs.get("password", None),
            "for_app_admin": attrs.get("for_app_admin", None),
        }
        try:
            authenticate_kwargs["request"] = self.context["request"]
        except KeyError:
            pass

        self.user = EmailOrPhoneAuthenticationBackend().authenticate(**authenticate_kwargs)
        return {}

    @classmethod
    def get_token(cls, user):
        raise NotImplementedError(
            "Must implement `get_token` method for `TokenObtainSerializer` subclasses"
        )


class TokenObtainPairSerializer(TokenObtainSerializer):

    @classmethod
    def get_token(cls, user):
        cls.raise_none_user(user=user)
        token = RefreshToken.for_user(user)

        token['username'] = user.username or ""
        token['email'] = user.email or ""
        
        # Add permissions
        permissions = []
        if user.user_permissions.exists():
            permissions = list(user.user_permissions.values_list('codename', flat=True))
        token['permissions'] = permissions
        
        # Add groups
        groups = []
        if user.groups.exists():
            groups = list(user.groups.values_list('name', flat=True))
        token['groups'] = groups
        
        # Add staff and superuser information
        token['isStaff'] = user.is_staff
        token['isSuperuser'] = user.is_superuser
        
        # Add user role
        token['role'] = user.role.label if user.role else None
        return token

    def validate(self, attrs):
        for_app_admin = getattr(self.context.get('request'), 'for_app_admin', False)
        attrs["for_app_admin"] = for_app_admin
        data = super().validate(attrs)

        refresh = self.get_token(self.user)

        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)
        user_serializer_class = AdminUserSerializer if for_app_admin else UserSerializer
        data["user"] = user_serializer_class(self.user, context=self.context).data
        return data

    @staticmethod
    def raise_none_user(user):
        if user is None:
            raise ValidationError(
                {"message": "Aucun compte trouvé avec ces identifiants"},
                code=ErrorEnum.USER_NOT_FOUND.value,
            )


class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField(read_only=True)
    token_class = RefreshToken

    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])
        try:
            user = User.objects.get(pk=refresh.payload["user_id"])
        except:
            raise ValueError("Cet Utilisateur n'existe pas ")
        user_serializer = UserSerializer(
            user, context={"request": self.context["request"]}
        )
        data = {"access": str(refresh.access_token)}

        if api_settings.ROTATE_REFRESH_TOKENS:
            if api_settings.BLACKLIST_AFTER_ROTATION:
                try:
                    # Attempt to blacklist the given refresh token
                    refresh.blacklist()
                except AttributeError:
                    # If blacklist app not installed, `blacklist` method will
                    # not be present
                    pass

            refresh.set_jti()
            refresh.set_exp()
            refresh.set_iat()

            data["refresh"] = str(refresh)
        data["user"] = user_serializer.data

        return data


class UserLogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    device_registration_id = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs['refresh']
        self.registration_id = attrs['device_registration_id']
        return attrs

    def save(self, **kwargs):
        user_id = None
        try:
            token = RefreshToken(self.token)
            user_id = token.payload['user_id']
            token.blacklist()
        except TokenError:
            raise ValidationError(
                ErrorUtil.get_error_detail(
                    ErrorEnum.BAD_REFRESH_TOKEN
                ),
                code=ErrorEnum.BAD_REFRESH_TOKEN.value,
            )

        try:
            mobile_device = MobileDevice.objects.get(registration_id=self.registration_id, user_id=user_id)
            mobile_device.hard_delete()
        except Exception as exc:
            logger.info(exc)
            pass


class CheckUserExistsSerializer(serializers.Serializer):
    """
    Sérialiseur pour vérifier l'existence d'un utilisateur par email/phone.
    """
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    phone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    register_from = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    def validate(self, data):
        if not data.get('email') and not data.get('phone'):
            raise ValidationError(
                ErrorUtil.get_error_detail(
                    ErrorEnum.EMAIL_OR_PHONE_REQUIRED
                ),
                code=ErrorEnum.EMAIL_OR_PHONE_REQUIRED.value,
            )
        return data