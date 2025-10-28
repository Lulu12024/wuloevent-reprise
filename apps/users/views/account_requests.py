# -*- coding: utf-8 -*-

import logging
from datetime import timedelta
from string import digits

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.crypto import get_random_string
from drf_spectacular.utils import inline_serializer, extend_schema
from rest_framework import status
from rest_framework.exceptions import (
    ValidationError,
    NotFound,
    NotAcceptable,
)
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.notifications.signals.initializers import send_email_signal
from apps.users.models import (
    ResetPasswordRequest,
    AccountValidationRequest,
)
from apps.users.serializers import (
    EmailCodeSerializer,
    EmailSerializer,
    PasswordCodeSerializer,
)
from apps.users.utils.account_requests import (
    get_password_reset_code_expiry_time,
    clear_account_validation_expired,
    get_account_validation_code_expiry_time,
    clear_password_reset_expired,
)
from apps.xlib.error_util import ErrorEnum

User = get_user_model()

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


# Create your viewsets here.


class SendAccountValidationRequestView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = EmailSerializer

    @extend_schema(
        responses={
            204: inline_serializer(
                name="AccountValidationRequestResponseSerializer",
                fields={
                },
            )
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        # before we continue, delete all existing expired tokens
        account_validation_code_validation_time = (
            get_account_validation_code_expiry_time()
        )

        # datetime.now minus expiry hours
        now_minus_expiry_time = timezone.now() - timedelta(
            hours=account_validation_code_validation_time
        )

        # delete all tokens where created_at < now - 24 hours
        clear_account_validation_expired(now_minus_expiry_time)

        # find a user by email address or phone (case insensitive search)
        try:
            user = User.objects.get(email=email)
        except Exception as exc:
            logger.exception(exc.__str__())
            raise NotFound(
                {"email": "Nous n'avons pas trouver un utilisateur avec cette adresse."}
            )

        # last but not least: iterate over all users that are active and can change their password
        # and create a Reset Password Token and send a signal with the created token
        if not user.eligible_for_reset():
            token = None
            # check if the user already has a token
            if user.account_validation_requests.all().count() > 0:
                # yes, already has a token, re-use this token
                token = user.account_validation_requests.all()[0]
                token.re_send_verification_code()
            else:
                # no token exists, generate a new token
                token = AccountValidationRequest.objects.create(
                    user=user,
                    user_agent=request.META.get("HTTP_USER_AGENT_HEADER", ""),
                    ip_address=request.META.get("HTTP_IP_ADDRESS_HEADER", ""),
                )
            return Response(status=status.HTTP_202_ACCEPTED)
        else:
            raise NotAcceptable({"message": "Votre compte est déjà validé!"})


class AccountValidationValidateCodeView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = EmailCodeSerializer

    @extend_schema(
        responses={
            202: inline_serializer(
                name="AccountValidationResponseSerializer",
                fields={
                },
            )
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]
        email = serializer.validated_data["email"]
        user = None
        try:
            account_validation_request = AccountValidationRequest.objects.get(
                code=code, user__email=email
            )
            account_validation_request.user.validate()
            user = account_validation_request.user
            account_validation_request.delete()
        except AccountValidationRequest.DoesNotExist:
            try:
                user = User.objects.get(
                    email=email, conf_num=code, have_validate_account=False
                )
                user.validate()
            except User.DoesNotExist:
                raise ValidationError({"message": "Informations incorrectes."})
        except Exception as exc:
            logger.exception(exc.__str__())
            raise ValidationError(
                {
                    "message": "Nous avons rencontré une erreur, Veuillez reéssayer ou contactez notre équipe."
                },
                code=ErrorEnum.SERVER_ERROR.value,
            )

        send_email_signal.send(
            sender='AccountValidationValidateCodeView', instance=user,
            email_data={
                "params": {
                    "user_id": str(user.pk),
                    "email": user.email,
                    'full_name': user.get_full_name(),
                },
                "email_type": 'account_validation_successful'
            })

        return Response(status=status.HTTP_202_ACCEPTED)


class SendPasswordResetRequestView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = EmailSerializer

    @extend_schema(
        responses={
            204: inline_serializer(
                name="PasswordResetRequestResponseSerializer",
                fields={
                },
            )
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        # before we continue, delete all existing expired tokens
        password_reset_token_validation_time = get_password_reset_code_expiry_time()

        # datetime.now minus expiry hours
        now_minus_expiry_time = timezone.now() - timedelta(
            hours=password_reset_token_validation_time
        )

        # delete all tokens where created_at < now - 24 hours
        clear_password_reset_expired(now_minus_expiry_time)

        # find a user by email address or email (case insensitive search)
        try:
            user = User.objects.get(email=email, is_staff=False)
        except Exception as exc:
            logger.exception(exc.__str__())
            raise NotFound(
                {
                    "email": "Nous n' avons pas trouver un utilisateur avec cette adresse mail."
                }
            )

        # last but not least: iterate over all users that are active and can change their password
        # and create a Reset Password Token and send a signal with the created token
        # define the token as none for now
        token = None

        # check if the user already has a token
        if user.password_reset_requests.all().count() > 0:
            # yes, already has a token, re-use this token
            token = user.password_reset_requests.all()[0]
            token.re_send_verification_code()
        else:
            # no token exists, generate a new token
            token = ResetPasswordRequest.objects.create(
                user=user,
                user_agent=request.META.get("HTTP_USER_AGENT_HEADER", ""),
                ip_address=request.META.get("HTTP_IP_ADDRESS_HEADER", ""),
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class ResetPasswordValidateCodeView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordCodeSerializer

    @extend_schema(
        responses={
            202: inline_serializer(
                name="ResetPasswordValidationResponseSerializer",
                fields={
                },
            )
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]
        password = serializer.validated_data["password"]
        try:
            password_reset_request = ResetPasswordRequest.objects.select_related("user").get(code=code)
            password_reset_request.user.set_password(password)
            password_reset_request.user.save()
            password_reset_request.delete()
        except Exception as exc:
            logger.exception(exc.__str__())
            raise ValidationError(
                {
                    "message": "Nous avons rencontré une erreur, Veuillez réessayer ou contactez notre équipe."
                },
                code=ErrorEnum.SERVER_ERROR.value,
            )

        code = get_random_string(length=6, allowed_chars=digits)
        send_email_signal.send(sender='ResetPasswordValidateCodeView', instance=self,
                               email_data={
                                   "params": {
                                       "user_id": str(password_reset_request.user.pk),
                                       "email": password_reset_request.user.email,
                                       'full_name': password_reset_request.user.get_full_name(),
                                       'code': code
                                   },
                                   "email_type": 'password_reset_successful'}
                               )

        return Response(status=status.HTTP_202_ACCEPTED)
