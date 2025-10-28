# -*- coding: utf-8 -*-
"""
Created on June 08, 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import datetime
import logging
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.validators import UniqueValidator

from apps.events.models import (
    Event,
    EventHighlightingType,
    EventHighlighting, )
from apps.marketing.models import Discount, Coupon
from apps.marketing.services.discounts import is_discount_available_to_user_or_organization, get_discounted_value
from apps.users.models import Transaction
from apps.users.serializers.transactions import TransactionSerializer
from apps.xlib.enums import TransactionKindEnum, TransactionStatusEnum, TRANSACTIONS_POSSIBLE_GATEWAYS
from apps.xlib.error_util import ErrorUtil, ErrorEnum

User = get_user_model()

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class EventHighlightingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventHighlightingType
        fields = (
            "pk",
            "name",
            "description",
            "price",
            "order",
            "active",
            "number_of_days_covered",
        )


class EventHighlightingSerializer(serializers.ModelSerializer):
    event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all(), validators=[UniqueValidator(
        message="Une mise en avant existe déjà pour cet évènement.",
        queryset=EventHighlighting.global_objects.all().only("pk"),
    )])
    type = serializers.PrimaryKeyRelatedField(
        queryset=EventHighlightingType.objects.filter(active=True)
    )
    coupon = serializers.SlugRelatedField(queryset=Coupon.objects.filter(active=True), slug_field="code",
                                          write_only=True, required=False)

    class Meta:
        model = EventHighlighting
        fields = (
            "pk",
            "event",
            "type",
            "coupon",
            "start_date",
            "end_date",
        )

        extra_kwargs = {
            "start_date": {"read_only": True},
            "end_date": {"read_only": True},
        }

    def validate_event(self, event):
        if not event.have_passed_validation:
            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.EVENT_UNDERGOING_VALIDATION),
                code=ErrorEnum.EVENT_UNDERGOING_VALIDATION.value,
            )
        if not event.valid:
            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.INVALID_EVENT_DATA),
                code=ErrorEnum.INVALID_EVENT_DATA.value,
            )
        return event

    def create(self, validated_data):

        enable_payment = True
        coupon = validated_data.pop("coupon", None)

        event: Event = validated_data.get("event")
        highlighting_type: EventHighlightingType = validated_data.get("type")
        validated_data["start_date"] = datetime.datetime.now().date()
        validated_data["end_date"] = validated_data["start_date"] + datetime.timedelta(
            days=int(highlighting_type.number_of_days_covered)
        )

        instance = super(EventHighlightingSerializer, self).create(validated_data)

        if enable_payment:
            amount = highlighting_type.price
            request = self.context.get("request")
            auto_resolve_transaction = self.context.get("auto_resolve_transaction", False)

            transaction_payload = {
                "type": TransactionKindEnum.EVENT_HIGHLIGHTING.value,
                "status": TransactionStatusEnum.PENDING.value,
                "description": "-",
                "amount": str(Decimal(amount)),
                "entity_id": str(instance.pk),
                "user": str(request.user.pk)
            }

            # In case there is coupon
            discount_is_available = False
            reduced_amount = amount
            if coupon:
                discount = Discount.objects \
                    .select_related("usage_rule", "validation_rule") \
                    .get(pk=coupon.discount_id)
                discount_is_available, message, code = is_discount_available_to_user_or_organization(
                    discount,
                    entity=highlighting_type,
                    entity_quantity=1,
                    organization=event.organization,
                    user=request.user)
                if discount_is_available:
                    calculation_infos = discount.validation_rule.get_calculation_infos()

                    reduced_amount = get_discounted_value(initial_value=amount,
                                                          discount_calculation_info=calculation_infos)
                    coupon_metadata = {
                        "use_coupon": True,
                        "coupon_id": str(coupon.pk),
                        "coupon_code": coupon.code,
                        "calculation_method": calculation_infos,
                        "initial_amount": str(amount),
                        "reduced_amount": str(reduced_amount)
                    }
                    transaction_payload["amount"] = str(reduced_amount)
                    transaction_payload["coupon_metadata"] = coupon_metadata
                else:
                    raise ValidationError(
                        detail=message,
                        code=code,
                    )

            # In case the request is made by an admin user
            if auto_resolve_transaction:
                transaction_payload['gateway'] = TRANSACTIONS_POSSIBLE_GATEWAYS.INTERNAL_AUTO.value

            # In case coupon used is available, use FREE_SHIPPING Gateway
            if reduced_amount == 0 and discount_is_available:
                transaction_payload["gateway"] = (
                    TRANSACTIONS_POSSIBLE_GATEWAYS.FREE_SHIPPING.value
                )

            transaction_serializer = TransactionSerializer(data=transaction_payload)
            transaction_serializer.is_valid(raise_exception=True)
            transaction = transaction_serializer.save()
            transaction.process_payment()

        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        transaction = Transaction.objects.get(entity_id=instance.pk, type=TransactionKindEnum.EVENT_HIGHLIGHTING.value)
        data["transaction"] = TransactionSerializer(instance=transaction).data
        return data
