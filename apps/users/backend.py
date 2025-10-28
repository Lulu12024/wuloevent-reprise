# -*- coding: utf-8 -*-
"""
Created on April 26 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.xlib.error_util import ErrorUtil, ErrorEnum

User = get_user_model()


class EmailOrPhoneAuthenticationBackend(ModelBackend):

    def authenticate(self, request, **kwargs):
        email = kwargs.get("email", None)
        phone = kwargs.get("phone", None)
        password = kwargs.get("password", None)
        for_app_admin = kwargs.get("for_app_admin", None)

        error_code = ErrorEnum.INCORRECT_EMAIL_OR_PASSWORD

        q_node = Q()
        if email:
            q_node |= Q(email=email)

        if phone:
            error_code = ErrorEnum.INCORRECT_PHONE_OR_PASSWORD
            q_node |= Q(phone=phone)
        # Todo: Supposing the account is deleted, propose a flow to restore it
        try:
            user = User.global_objects.select_related("country").filter(q_node).first()
            if not user:
                raise User.DoesNotExist
        except User.DoesNotExist:
            return None
        else:
            if self.user_account_is_deactivate(user):
                raise ValidationError(
                    {
                        "message": "Votre compte a été désactivé",
                        "deactivated_at": user.deactivated_at,
                    },
                    code=ErrorEnum.DISABLE_ACCOUNT.value,
                )
            if user.check_password(password):
                if for_app_admin and not user.is_app_admin:
                    raise ValidationError(
                        {"message": ErrorUtil.get_error_detail(ErrorEnum.RESOURCE_RESERVED_TO_ADMIN)},
                        code=ErrorEnum.RESOURCE_RESERVED_TO_ADMIN.value,
                    )
                if for_app_admin and not user.role:
                    raise ValidationError(
                        {"message": ErrorUtil.get_error_detail(ErrorEnum.NO_ROLE_SPECIFIED_FOR_THE_ADMIN)},
                        code=ErrorEnum.NO_ROLE_SPECIFIED_FOR_THE_ADMIN.value,
                    )
                return user
            else:
                raise ValidationError(
                    {"message": ErrorUtil.get_error_detail(error_code)},
                    code=error_code.value,
                )

    def user_can_authenticate(self, user):
        """
        Reject users with is_active=False. Custom user models that don't have
        that attribute are allowed.
        """
        is_active = getattr(user, "is_active", None)
        return is_active or is_active is None

    def user_account_is_deactivate(self, user):
        """
        Reject users with deactivated_at is not null Custom user models that don't have
        that attribute is not are allowed.
        """
        deactivated_at = getattr(user, "deactivated_at", timezone.now())
        return deactivated_at is not None

    def get_user(self, user_pk):
        try:
            user = User.objects.get(pk=user_pk)
        except User.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None
