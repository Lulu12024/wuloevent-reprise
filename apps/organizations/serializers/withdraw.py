# -*- coding: utf-8 -*-
"""
Created on April 26 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging
from decimal import Decimal

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.organizations.models import (
    Withdraw, Organization
)
from apps.users.serializers.transactions import TransactionSerializer
from apps.utils.models import Variable
from apps.xlib.enums import (
    TransactionStatusEnum, TransactionKindEnum, VARIABLE_NAMES_ENUM,
)
from apps.xlib.error_util import ErrorEnum, ErrorUtil

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class WithdrawSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(), required=False
    )

    class Meta:
        model = Withdraw

        fields = ("method", "amount", "status", "payment_phone", "organization")

        read_only_fiels = ("status",)

        extra_kwargs = {
            "amount": {"required": True},
        }

    def validate(self, attrs):
        request = self.context.get("request")
        organization = request.organization
        financial_account = organization.get_financial_account
        attrs["organization"] = organization
        data = super().validate(attrs)
        amount = data.get("amount")
        # Minimal amount of withdraw

        minimal_amount_variable = Variable.objects.get(
            name=VARIABLE_NAMES_ENUM.MINIMAL_AMOUNT_REQUIRED_FOR_WITHDRAW.value
        )
        minimal_amount_value = minimal_amount_variable.format_value(
            minimal_amount_variable.possible_values.first().value
        )

        if int(amount) < minimal_amount_value:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.MINIMAL_AMOUNT_FOR_WITHDRAW_NOT_REACHED),
                code=ErrorEnum.MINIMAL_AMOUNT_FOR_WITHDRAW_NOT_REACHED.value,
            )

        if not financial_account.can_withdraw_amount(int(amount)):
            raise ValidationError(
                {"amount": "Vous n' avez pas assez de liquidité"},
                code=ErrorEnum.INSUFFICIENT_BALANCE.value,
            )
        return data

    def create(self, validated_data):

        withdraw = super().create(
            validated_data
        )

        initialization_data = withdraw.process()
        withdraw.disburse(gateway_id=initialization_data.id)

        amount = withdraw.amount
        request = self.context.get("request")

        transaction_payload = {
            "type": TransactionKindEnum.WITHDRAW.value,
            "status": TransactionStatusEnum.PENDING.value,
            "description": "-",
            "amount": str(Decimal(amount)),
            "entity_id": str(withdraw.pk),
            "user": str(request.user.pk)
        }
        transaction_serializer = TransactionSerializer(data=transaction_payload)
        transaction_serializer.is_valid(raise_exception=True)
        t = transaction_serializer.save()
        t.gateway_id = initialization_data.id
        t.description = initialization_data.reference
        t.save()
        return withdraw
