import logging
from abc import ABC

from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import NotFound, APIException, ValidationError
from rest_framework.validators import UniqueTogetherValidator

from apps.organizations.models import (
    OrganizationMembership,
    Role,
    Organization,
)
from apps.users.models import User
from apps.xlib.error_util import ErrorUtil, ErrorEnum

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class UserSerializerLight(serializers.ModelSerializer):
    class Meta:
        ref_name = "UserSerializerLightForOrganizationsMemberModule"
        model = User
        fields = ("pk", "first_name", "last_name", "email", "sex", "phone", "username")


class UpperRoleField(serializers.RelatedField, ABC):
    def to_representation(self, value):
        return str(value.name).upper()


class OrganizationMembersSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.filter(active=True)
    )
    user = UserSerializerLight()
    roles = UpperRoleField(
        many=True,
        read_only=True,
    )

    class Meta:
        model = OrganizationMembership
        fields = (
            "pk",
            "organization",
            "user",
            "roles",
            "timestamp",
        )

        validators = [
            UniqueTogetherValidator(
                message="Vous êtes déjà membre de cette organisation.",
                queryset=OrganizationMembership.objects.all(),
                fields=["user", "organization"],
            )
        ]


class AddMemberToOrganizationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_null=True)
    phone = serializers.CharField(required=False, allow_null=True)
    password = serializers.CharField(required=True)
    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all())

    def validate(self, attrs):
        data = super().validate(attrs)
        email = data.get("email", "")
        phone = data.get("phone", "")
        if not phone and not email:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.EMAIL_OR_PHONE_REQUIRED),
                code=ErrorEnum.EMAIL_OR_PHONE_REQUIRED.value,
            )

        try:
            user = User.objects.filter(Q(email=email) or Q(phone=phone)).first()
            if not (user and user.is_active):
                raise APIException(
                    ErrorUtil.get_error_detail(ErrorEnum.USER_DOES_NOT_EXIST),
                    code=ErrorEnum.USER_DOES_NOT_EXIST.value,
                )
            data["user"] = user
        except User.DoesNotExist:
            raise NotFound(
                ErrorUtil.get_error_detail(ErrorEnum.USER_DOES_NOT_EXIST),
                code=ErrorEnum.USER_DOES_NOT_EXIST.value,
            )
        return data


class ManageMembershipRoleSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    roles = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), many=True)
    password = serializers.CharField(required=True)
    action = serializers.ChoiceField(
        allow_null=False, required=True, choices=["ADD", "REMOVE"]
    )
