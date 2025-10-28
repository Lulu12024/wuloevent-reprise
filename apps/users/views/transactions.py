# -*- coding: utf-8 -*-

import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import (
    ValidationError,
    NotFound, )
from rest_framework.filters import OrderingFilter
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin, DestroyModelMixin
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny, OR
from rest_framework.response import Response

from apps.organizations.models import Withdraw
from apps.organizations.serializers.extras import PossibleWithdrawWaysResponseSerializer
from apps.users.filters import TransactionFilter
from apps.users.models import (
    Transaction,
)
from apps.users.permissions import IsCreator, HasAppAdminPermissionFor
from apps.users.serializers.transactions import (
    TransactionSerializer,
)
from apps.utils.utils.baseviews import BaseGenericViewSet
from apps.xlib.enums import (
    TransactionStatusEnum, TransactionKindEnum, WithdrawStatusEnum,
)
from apps.xlib.error_util import ErrorUtil, ErrorEnum
from backend.commons import custom_get_object_or_404 as get_object_or_404
from commons.constants.transactions import FEDAPAY_TRANSACTION_RETURNED_DATA_FORMAT

User = get_user_model()

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


@extend_schema_view(
    list=extend_schema(
        description="Endpoint to retrieve user transactions",
        parameters=[
            OpenApiParameter('user', OpenApiTypes.UUID, location=OpenApiParameter.QUERY, required=False,
                             description="The id of a user to filter transactions against"
                             ),
            OpenApiParameter('status', OpenApiTypes.BOOL, location=OpenApiParameter.QUERY, required=False,
                             description="A status of transaction to filter transactions against"
                             ),
            OpenApiParameter('type', OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False,
                             description="A type of transaction to filter transactions against"
                             ),
            OpenApiParameter('gateway_id', OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False,
                             description="A gateway id to filter transactions against"
                             ),
            OpenApiParameter('payment_method', OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False,
                             description="A payment method to filter transactions against"
                             ),
        ],
    )
)
@method_decorator(name='retrieve', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Transaction-Retrieve",
    operation_description="Récupérer les détails d' une transaction",
    operation_summary="Transactions"
))
@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Transaction-List",
    operation_description="Lister les transactions",
    operation_summary="Transactions"
))
@method_decorator(name='list_by_user', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Transaction-List-By-User",
    operation_description="Lister les transactions par utilisateur",
    operation_summary="Transactions"
))
@method_decorator(name='destroy', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Transaction-Destroy",
    operation_description="Supprimer une transaction",
    operation_summary="Transactions"
))
class TransactionViewSet(BaseGenericViewSet, RetrieveModelMixin, ListModelMixin, DestroyModelMixin):
    object_class = Transaction
    serializer_default_class = TransactionSerializer
    http_method_names = ["get", "post", "delete"]

    filter_backends = [OrderingFilter, DjangoFilterBackend]
    filterset_class = TransactionFilter

    ordering_fields = [
        "timestamp"
    ]

    permission_classes_by_action = {
        "payments_callbacks": [AllowAny],
        "withdraws_callbacks": [AllowAny],
        "possible_withdraw_ways": [AllowAny],
        "retrieve": [
            OR(IsCreator(), OR(IsAdminUser(), HasAppAdminPermissionFor("Admin-Operation-Transaction-Retrieve")))
        ],
        "list_by_user": [IsAuthenticated],
        "list": [IsAuthenticated, OR(IsAdminUser(), HasAppAdminPermissionFor("Admin-Operation-Transaction-List"))],
        "destroy": [
            OR(
                IsCreator(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-Transaction-Destroy"))
            )
        ],
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    def get_object(self):
        if self.action == "callback":
            return get_object_or_404(
                self.get_queryset(), local_id=self.kwargs["local_id"]
            )
        return super().get_object()

    @action(methods=["GET", "POST"], detail=False, url_path="payments-callbacks")
    @transaction.atomic
    def payments_callbacks(self, request, *args, **kwargs):
        data = request.data

        failed_status = ["transaction.canceled", "transaction.failed", "transaction.declined"]
        success_status = ["transaction.approved"]
        status_to_handle = success_status + failed_status

        if request.method == "POST" and data.get("name") in status_to_handle:
            payment_transaction = data.get("entity", {})

            gateway_id = payment_transaction.get("id", None)
            if not gateway_id:
                raise ValidationError("An error occurred when trying to retrieve gateway_id", code=400)

            try:
                _transaction = Transaction.objects.get(gateway_id=gateway_id)
            except Transaction.DoesNotExist:
                raise NotFound(ErrorUtil.get_error_detail(ErrorEnum.PAYMENT_TRANSACTION_NOT_FOUND),
                               code=ErrorEnum.PAYMENT_TRANSACTION_NOT_FOUND.value)

            time_threshold = timezone.now() - timezone.timedelta(minutes=10)

            if _transaction.completed \
                    and _transaction.status_updated_at is not None and _transaction.status_updated_at < time_threshold:
                raise ValidationError(
                    ErrorUtil.get_error_detail(ErrorEnum.TRANSACTION_ALREADY_COMPLETED),
                    code=ErrorEnum.TRANSACTION_ALREADY_COMPLETED.value,
                )

            if _transaction.paid:
                raise ValidationError(
                    ErrorUtil.get_error_detail(ErrorEnum.TRANSACTION_ALREADY_PAID),
                    code=ErrorEnum.TRANSACTION_ALREADY_PAID.value,
                )

            transaction_status = f"transaction.{payment_transaction.get('status', None)}"

            if transaction_status in failed_status:
                issue = {"transaction.canceled": TransactionStatusEnum.CANCELED.value,
                         "transaction.declined": TransactionStatusEnum.CANCELED.value,
                         "transaction.failed": TransactionStatusEnum.FAILED.value}.get(transaction_status)
                _transaction.status = issue
            elif transaction_status in success_status:
                _transaction.status = TransactionStatusEnum.PAID.value

            # Todo: Adapt to other gateways after
            _transaction.last_webhook_data = {key: data['entity'][key] for key in
                                              FEDAPAY_TRANSACTION_RETURNED_DATA_FORMAT.keys()}
            _transaction.status_updated_at = timezone.now()
            _transaction.save()

            return Response(status=status.HTTP_202_ACCEPTED)
        return Response(status=status.HTTP_200_OK)

    @action(methods=["GET", "POST"], detail=False, url_path="withdraws-callbacks")
    @transaction.atomic
    def withdraws_callbacks(self, request, *args, **kwargs):
        data = request.data

        failed_status = ["payout.failed"]
        success_status = ["payout.sent"]

        status_to_handle = success_status + failed_status

        if request.method == "POST" and data.get("name") in status_to_handle:
            withdraw_transaction = data.get("entity", {})
            gateway_id = withdraw_transaction.get("id", None)

            if not gateway_id:
                raise ValidationError("An error occurred when trying to retrieve gateway_id", code=400)

            try:
                _transaction = Transaction.objects.get(gateway_id=gateway_id, type=TransactionKindEnum.WITHDRAW.value)
            except Transaction.DoesNotExist:
                raise NotFound(ErrorUtil.get_error_detail(ErrorEnum.WITHDRAW_TRANSACTION_NOT_FOUND),
                               code=ErrorEnum.WITHDRAW_TRANSACTION_NOT_FOUND.value)

            related_withdraw = Withdraw.objects.get(pk=_transaction.entity_id)

            if _transaction.completed:
                raise ValidationError(
                    ErrorUtil.get_error_detail(ErrorEnum.TRANSACTION_ALREADY_COMPLETED),
                    code=ErrorEnum.TRANSACTION_ALREADY_COMPLETED.value,
                )

            transaction_status = f"payout.{withdraw_transaction.get('status', None)}"

            if transaction_status in failed_status:
                _transaction.status = TransactionStatusEnum.FAILED.value
                related_withdraw.status = WithdrawStatusEnum.FAILED.value
            elif transaction_status in success_status:
                _transaction.status = TransactionStatusEnum.RESOLVED.value
                related_withdraw.status = WithdrawStatusEnum.FINISHED.value
                related_withdraw.save()
                related_withdraw.update_user_financial_account()

            # Todo: Adapt to other gateways after
            _transaction.last_webhook_data = {key: data['entity'].get(key, None) for key in
                                              FEDAPAY_TRANSACTION_RETURNED_DATA_FORMAT.keys()}

            _transaction.status_updated_at = timezone.now()
            _transaction.save()
            related_withdraw.save()

            return Response(status=status.HTTP_202_ACCEPTED)
        return Response(status=status.HTTP_200_OK)

    @extend_schema(
        responses={200: TransactionSerializer(many=True)},
    )
    @action(methods=["GET"], detail=False, url_path="by-me")
    def list_by_user(self, request, *args, **kwargs):
        user = request.user

        queryset = self.filter_queryset(self.get_queryset().filter(user_id=user.pk))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses={200: PossibleWithdrawWaysResponseSerializer(many=True)},
    )
    @action(methods=["GET"], detail=False, url_path="possible-withdraw-ways")
    def possible_withdraw_ways(self, request, *args, **kwargs):
        data = [
            {
                "label": "MTN_BENIN",
                "name": "MTN Benin",
                "processor_id": "mtn",
                "available": True,
            },
            {
                'label': 'MOOV_BENIN',
                'name': 'MOOV Bénin',
                'processor_id': 'moov',
                'available': True
            }
        ]
        return Response(data)
