# -*- coding: utf-8 -*-

import logging
from typing import Literal

import phonenumbers
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.events.models.super_seller_profile import OrganizationType
from apps.organizations.models import (
    OrganizationFollow,
    Organization,
)
from apps.users.models import User
from apps.utils.models import Country
from apps.xlib.error_util import ErrorUtil, ErrorEnum

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class UserSerializerLight(serializers.ModelSerializer):
    class Meta:
        ref_name = "UserSerializerLightForOrganizationsOrganizationModule"
        model = User
        fields = ("pk", "first_name", "last_name", "email", "sex", "phone", "username")


class OrganizationSerializerLight(serializers.ModelSerializer):
    owner_infos = UserSerializerLight(
        source="owner", required=False, allow_null=True, read_only=True
    )
    current_user_role = serializers.SerializerMethodField()

    def __init__(self, instance=None, *args, **kwargs):
        self.current_user = kwargs.pop("user", None)
        super().__init__(instance, *args, **kwargs)

    def get_current_user_role(
            self, instance
    ) -> Literal["OWNER", "MEMBER", "COORDINATOR", None]:
        if self.current_user is not None:
            return self.current_user.get_user_role_for_organization(instance)
        request = self.context.get("request", None)
        if request and request.user and request.user.is_authenticated:
            return request.user.get_user_role_for_organization(instance)
        return None

    class Meta:
        model = Organization
        fields = (
            "pk",
            "name",
            "email",
            "phone",
            "description",
            "owner_infos",
            "current_user_role",
            "logo",
            "current_user_role",
        )
        extra_kwargs = {
            "logo": {"required": False, "allow_null": False},
            "phone": {"required": False, "allow_null": False},
        }


class OrganizationSerializer(serializers.ModelSerializer):
    country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False, allow_null=True
    )
    owner_infos = UserSerializerLight(
        source="owner", required=False, allow_null=True, read_only=True
    )
    owner = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True), required=False
    )

    is_owner = serializers.SerializerMethodField()
    current_user_role = serializers.SerializerMethodField()

    organization_type = serializers.ChoiceField(
        choices=OrganizationType.choices,
        default=OrganizationType.STANDARD
    )
    is_super_seller = serializers.BooleanField(read_only=True, source='is_super_seller')
    is_verified = serializers.BooleanField(read_only=True, source='is_super_seller_verified')
    seller_count = serializers.IntegerField(read_only=True, source='get_seller_count')
    


    def __init__(self, instance=None, *args, **kwargs):
        self.current_user = kwargs.pop("user", None)
        super().__init__(instance, *args, **kwargs)

    @extend_schema_field(serializers.BooleanField)
    def get_is_owner(self, instance):
        if self.current_user is not None:
            return self.current_user == instance.owner
        request = self.context.get("request", None)
        return (
                request
                and request.user
                and request.user.is_authenticated
                and request.user == instance.owner
        )

    def get_current_user_role(
            self, instance
    ) -> Literal["OWNER", "MEMBER", "COORDINATOR", None]:
        if self.current_user is not None:
            return self.current_user.get_user_role_for_organization(instance)
        request = self.context.get("request", None)
        if request and request.user and request.user.is_authenticated:
            return request.user.get_user_role_for_organization(instance)
        return None

    def validate(self, attrs):
        phone = attrs.get("phone", None)
        user = self.context["request"].user
        if phone != "" and phone is not None:
            try:
                phonenumber_instance = phonenumbers.parse(phone, None)
            except Exception as exc:
                raise ValidationError(
                    {
                        "phone": ErrorUtil.get_error_detail(
                            ErrorEnum.INVALID_PHONE_NUMBER
                        )
                    },
                    code=ErrorEnum.MISSING_PAGE_NUMBER.value,
                )
            if not phonenumbers.is_possible_number(phonenumber_instance):
                raise ValidationError(
                    {
                        "phone": ErrorUtil.get_error_detail(
                            ErrorEnum.INVALID_PHONE_NUMBER
                        )
                    },
                    code=ErrorEnum.MISSING_PAGE_NUMBER.value,
                )
        else:
            if self.context["request"].user.phone is not None:
                attrs["phone"] = user.phone

        attrs["owner"] = user
        _validation = super().validate(attrs)

        name = attrs.get("name", None)
        if not self.instance and Organization.objects.filter(name=name).exists():
            raise ValidationError(
                {"name": "ORGANIZATION_WITH_THIS_NAME_ALREADY_EXISTS"},
                code=ErrorEnum.ORGANIZATION_WITH_THIS_NAME_ALREADY_EXISTS.value,
            )

        return _validation

    class Meta:
        model = Organization
        fields = (
            "pk",
            "name",
            "email",
            "description",
            "phone",
            "country",
            "address",
            "owner",
            "owner_infos",
            "logo",
            "active",
            "is_owner",
            "current_user_role",
            "phone_number_validated",
            "percentage",
            "percentage_if_discounted",
            'organization_type',
            'is_super_seller',
            'is_verified',
            'seller_count',
        )
        extra_kwargs = {
            "logo": {"required": False, "allow_null": False},
            "phone": {"required": False, "allow_null": False},
        }
        read_only_fields = ['is_super_seller', 'is_verified', 'seller_count']

class OrganizationFollowSerializer(serializers.ModelSerializer):
    follower = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True)
    )
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.filter(active=True)
    )

    class Meta:
        model = OrganizationFollow
        fields = (
            "pk",
            "follower",
            "organization",
        )
