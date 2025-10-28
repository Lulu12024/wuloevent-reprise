# -*- coding: utf-8 -*-
"""
Created on April 26 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging
from datetime import timedelta

import phonenumbers as phonenumbers
from django.contrib.gis.geos import Point
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, NotFound, APIException
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework_simplejwt.serializers import PasswordField
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.organizations.models import (
    Organization
)
from apps.organizations.serializers import OrganizationSerializer
from apps.users.backend import EmailOrPhoneAuthenticationBackend
from apps.users.models import (
    PointOfInterest,
    User,
    Transaction,
    ResetPasswordRequest,
    ZoneOfInterest,
)
from apps.users.utils.account_requests import get_password_reset_code_expiry_time
from apps.utils.models import Country
from apps.utils.validators import PhoneNumberValidator
from apps.xlib.enums import (
    TransactionStatusEnum, )
from apps.xlib.error_util import ErrorUtil, ErrorEnum

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class UserSerializer(serializers.ModelSerializer):
    country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False, allow_null=True
    )
    is_event_organizer = serializers.BooleanField(read_only=True)
    belong_to_an_organization = serializers.BooleanField(read_only=True)
    organizations = serializers.SerializerMethodField()

    @extend_schema_field(OrganizationSerializer(many=True))
    def get_organizations(self, user):
        return OrganizationSerializer(
            Organization.objects.list_by_user(user=user).order_by("-timestamp"),
            many=True,
            user=user,
        ).data

    def is_valid(self, raise_exception=False):
        return super().is_valid(raise_exception)

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
    class Meta:
        model = User
        fields = ("email", "phone")

    def validate(self, data):
        phone = data.get("phone", None)
        email = data.get("email", None)
        update_data = {}
        if email is not None:
            if User.objects.filter(email=email).exists():
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
            if User.objects.filter(phone=phone).exists():
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


class PointOfInterestSerializer(GeoFeatureModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = PointOfInterest
        geo_field = "location"
        fields = (
            "pk",
            "user",
            "location",
            "location_long",
            "location_lat",
            "approximate_distance",
            "allow_notifications",
            "timestamp",
            "active",
        )

    def create(self, validated_data):
        long = validated_data.get("location_long", 0.0)
        lat = validated_data.get("location_lat", 0.0)
        instance = super().create(validated_data)
        location = Point(lat, long, srid=4326)
        instance.location = location
        instance.save()
        return instance


class ZoneOfInterestSerializer(GeoFeatureModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = ZoneOfInterest
        geo_field = "geofence"
        fields = (
            "pk",
            "user",
            "geofence",
            "allow_notifications",
            "timestamp",
            "active",
        )


class TransactionSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Transaction
        fields = (
            "pk",
            "uuid",
            "type",
            "user",
            "local_id",
            "amount",
            "status",
            "gateway",
            "payment_method",
            "entity_id",
            "payment_url"
        )

        read_only_fields = ("local_id", "pk", "uuid")

    def create(self, validated_data):
        try:
            progress_status = [
                TransactionStatusEnum.IN_PROGRESS.value,
                TransactionStatusEnum.PENDING.value,
            ]

            self.Meta.model.objects.get(
                uuid=validated_data.get("uuid"), status__in=progress_status
            )

            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.PAYMENT_ALREADY_IN_PROGRESS),
                code=ErrorEnum.PAYMENT_ALREADY_IN_PROGRESS.value,
            )
        except ObjectDoesNotExist:
            return super().create(validated_data)
        except Exception as exc:
            logger.exception(exc.__str__())
            raise APIException({"message": exc})


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
        return RefreshToken.for_user(user)

    def validate(self, attrs):
        data = super().validate(attrs)

        refresh = self.get_token(self.user)

        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)
        data["user"] = UserSerializer(self.user, context=self.context).data
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
