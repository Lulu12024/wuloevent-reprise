# -*- coding: utf-8 -*-
"""
Created on April 26 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging
from datetime import timedelta

import phonenumbers as phonenumbers
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, NotFound

from apps.organizations.models import Organization
from apps.organizations.serializers import OrganizationSerializerLight
from apps.users.models import (
    User,
    ResetPasswordRequest,
)
from apps.users.utils.account_requests import get_password_reset_code_expiry_time
from apps.utils.models import Country
from apps.xlib.error_util import ErrorUtil, ErrorEnum

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class AdminUserSerializer(serializers.ModelSerializer):
    country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False, allow_null=True
    )
    role = serializers.SlugRelatedField(read_only=True, slug_field='label')

    class Meta:
        model = User
        fields = (
            "pk",
            "first_name",
            "last_name",
            "birthday",
            "country",
            "email",
            "sex",
            "role",
            "phone",
            "password",
            "profile_image",
            "have_validate_account",
            "username"
        )
        extra_kwargs = {
            "password": {"write_only": True},
            "have_validate_account": {"read_only": True},
        }

    def create(self, validated_data):
        pass


class UserSerializer(serializers.ModelSerializer):
    country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False, allow_null=True
    )
    is_event_organizer = serializers.BooleanField(read_only=True)
    belong_to_an_organization = serializers.BooleanField(read_only=True)
    # Todo: Prefetch organization and roles check
    organizations = serializers.SerializerMethodField()

    @extend_schema_field(OrganizationSerializerLight(many=True))
    def get_organizations(self, user):
        return OrganizationSerializerLight(
            Organization.objects.list_by_user(user=user).order_by("-timestamp"),
            many=True,
            user=user
        ).data

    def is_valid(self, raise_exception=False):
        return super().is_valid(raise_exception=True)

    class Meta:
        model = User
        fields = (
            "pk",
            "first_name",
            "last_name",
            "email",
            "birthday",
            "organizations",
            "country",
            "sex",
            "profile_image",
            "phone",
            "password",
            "is_event_organizer",
            "have_validate_account",
            "belong_to_an_organization",
            "username"
        )
        extra_kwargs = {
            "password": {"write_only": True},
            "conf_num": {"read_only": True},
            "have_validate_account": {"read_only": True},
        }

    def validate(self, data):
        password = data.get("password", "")
        phone = data.get("phone", None)
        email = data.get("email", None)

        if password == "":
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.PASSWORD_REQUIRED),
                code=ErrorEnum.PASSWORD_REQUIRED.value,
            )
        if not email and not phone:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.EMAIL_OR_PHONE_ALREADY_USED),
                code=ErrorEnum.EMAIL_OR_PHONE_SHOULD_BE_SET.value,
            )

        q_node = Q()
        if email:
            q_node |= Q(email=email)

        if phone:
            try:
                phonenumber_instance = phonenumbers.parse(phone, None)
            except:
                raise ValidationError(
                    {
                        "phone": ErrorUtil.get_error_detail(
                            ErrorEnum.INVALID_PHONE_NUMBER
                        )
                    },
                    code=ErrorEnum.INVALID_PHONE_NUMBER.value,
                )
            if not phonenumbers.is_possible_number(phonenumber_instance):
                raise ValidationError(
                    {
                        "phone": ErrorUtil.get_error_detail(
                            ErrorEnum.INVALID_PHONE_NUMBER
                        )
                    },
                    code=ErrorEnum.INVALID_PHONE_NUMBER.value,
                )

            q_node |= Q(phone=phone)

        if User.objects.filter(q_node).exists():
            raise ValidationError(
                {"email": "EMAIL_OR_PHONE_ALREADY_USED"},
                code=ErrorEnum.EMAIL_OR_PHONE_ALREADY_USED.value,
            )
        return super().validate(attrs=data)

    def create(self, validated_data):
        password = validated_data.pop("password")
        instance = self.Meta.model(**validated_data)
        instance.set_password(password)
        instance.save()
        return instance


class UpdateUserSerializer(serializers.ModelSerializer):
    is_event_organizer = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = User
        fields = ("first_name", "last_name", "sex", "birthday", "is_event_organizer", "username")
        extra_kwargs = {
            "is_event_organizer": {"read_only": True}
        }


class UpdateUserPhoneOrEmailSerializer(serializers.ModelSerializer):
    password = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ("email", "phone", "password")
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def validate(self, data):
        phone = data.get("phone", None)
        email = data.get("email", None)
        update_data = {}
        if email is not None:
            if User.global_objects.filter(email=email).exists():
                raise ValidationError(
                    {"email": "EMAIL_ALREADY_USED"},
                    code=ErrorEnum.EMAIL_ALREADY_USED.value,
                )
            update_data["email"] = email

        if phone is not None:
            try:
                phonenumber_instance = phonenumbers.parse(phone, None)
            except:
                raise ValidationError(
                    {"phone": "Votre numéro de téléphone semble invalide."},
                    code=ErrorEnum.INVALID_PHONE_NUMBER.value,
                )
            if not phonenumbers.is_possible_number(phonenumber_instance):
                raise ValidationError(
                    {"phone": "Votre numéro de téléphone semble invalide."},
                    code=ErrorEnum.INVALID_PHONE_NUMBER.value,
                )
            if User.global_objects.filter(phone=phone).exists():
                raise ValidationError(
                    {"phone": "Ce numéro de téléphone est déjà utilisé"},
                    code=ErrorEnum.PHONE_NUMBER_ALREADY_USED.value,
                )
            update_data["phone"] = phone

        return super().validate(attrs=update_data)


class UserSerializerLight(serializers.ModelSerializer):
    class Meta:
        ref_name = "UserSerializerLightForUserModule"
        model = User
        fields = ("pk", "first_name", "last_name", "email", "sex", "phone", "username")


class PhoneSerializer(serializers.Serializer):
    phone = serializers.CharField(required=True)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass

    def validate(self, data):
        phone = data.get("phone", "")
        try:
            phonenumber_instance = phonenumbers.parse(phone, None)
        except Exception as exc:
            logger.exception(exc.__str__())
            raise ValidationError(
                {"phone": "Votre numéro de téléphone semble invalide."},
                code=ErrorEnum.INVALID_PHONE_NUMBER.value,
            )
        if phone == "":
            raise ValidationError({"phone": "Champs requis."})
        else:
            if not phonenumbers.is_possible_number(phonenumber_instance):
                raise ValidationError(
                    {"phone": "Votre numéro de téléphone semble invalide."},
                    code=ErrorEnum.INVALID_PHONE_NUMBER.value,
                )
        return data


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class EmailCodeSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class PasswordCodeSerializer(serializers.Serializer):
    password = serializers.CharField(style={"input_type": "password"}, write_only=True)
    code = serializers.CharField(write_only=True)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass

    def validate(self, data):
        code = data.get("code")

        # get token validation time
        password_reset_token_validation_time = get_password_reset_code_expiry_time()

        # find request
        try:
            reset_password_request = ResetPasswordRequest.objects.get(code=code)
        except Exception as exc:
            logger.exception(exc.__str__())
            logger.exception(exc.__str__())
            raise NotFound(
                {"code": "Le code entré est invalide . Vueillez vérifier et reprendre."}
            )

        # check expiry date
        expiry_date = reset_password_request.timestamp + timedelta(
            hours=password_reset_token_validation_time
        )

        if timezone.now() > expiry_date:
            # delete expired token
            reset_password_request.delete()
            raise NotFound({"code": "Le code à expiré."})
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        style={"input_type": "password"}, write_only=True, required=True
    )
    new_password = serializers.CharField(
        style={"input_type": "password"}, write_only=True, required=True
    )

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass
