# -*- coding: utf-8 -*-

import datetime
from datetime import timedelta

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.marketing.models import Coupon, Discount
from apps.marketing.services.discounts import is_discount_available_to_user_or_organization, get_discounted_value
from apps.organizations.models import (
    Subscription,
    SubscriptionType,
    Organization,
)
from apps.users.models import Transaction
from apps.users.serializers.transactions import TransactionSerializer
from apps.xlib.enums import (
    TransactionKindEnum,
    TransactionStatusEnum,
    TRANSACTIONS_POSSIBLE_GATEWAYS,
)


class SubscriptionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionType
        fields = ("pk", "name", "price", "order", "validity_days_range", "active")


class SubscriptionCreationSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.filter(active=True)
    )
    subscription_type = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionType.objects.filter(active=True)
    )
    coupon = serializers.SlugRelatedField(queryset=Coupon.objects.filter(active=True),
                                          slug_field="code", write_only=True, required=False)

    class Meta:
        model = Subscription
        fields = (
            "pk",
            "organization",
            "subscription_type",
            "start_date",
            "end_date",
            "unity_time_number",
            "coupon",
        )

    def create(self, validated_data):
        enable_payment = True

        coupon = validated_data.pop("coupon", None)

        organization = validated_data.get("organization")
        subscription_type = validated_data.get("subscription_type")
        unity_time_number = validated_data.get("unity_time_number")
        total_validity_day_range = subscription_type.validity_days_range * int(
            unity_time_number
        )

        start_date = datetime.datetime.now().date()

        last_subscription_end_date = organization.subscribe_until
        if last_subscription_end_date and last_subscription_end_date >= start_date:
            # Start one day after the last subscription end date
            start_date = last_subscription_end_date + timedelta(days=1)

        end_date = start_date + timedelta(days=total_validity_day_range)
        validated_data["start_date"] = start_date
        validated_data["end_date"] = end_date

        subscription_instance = super().create(validated_data)

        if enable_payment:
            amount = (
                    subscription_type.price
                    * subscription_instance.unity_time_number
            )
            request = self.context.get("request")
            auto_resolve_transaction = self.context.get(
                "auto_resolve_transaction", False
            )
            transaction_payload = {
                "type": TransactionKindEnum.SUBSCRIPTION.value,
                "status": TransactionStatusEnum.PENDING.value,
                "description": "-",
                "amount": str(amount),
                "entity_id": str(subscription_instance.pk),
                "user": str(request.user.pk),
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
                    entity=subscription_type,
                    entity_quantity=unity_time_number,
                    organization=organization,
                    user=request.user
                )
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
                transaction_payload["gateway"] = (
                    TRANSACTIONS_POSSIBLE_GATEWAYS.INTERNAL_AUTO.value
                )

            # In case coupon used is available, use FREE_SHIPPING Gateway
            if reduced_amount == 0 and discount_is_available:
                transaction_payload["gateway"] = (
                    TRANSACTIONS_POSSIBLE_GATEWAYS.FREE_SHIPPING.value
                )

            transaction_serializer = TransactionSerializer(data=transaction_payload)
            transaction_serializer.is_valid(raise_exception=True)
            transaction = transaction_serializer.save()
            transaction.process_payment()
        return subscription_instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        transaction = Transaction.objects.get(entity_id=instance.pk)
        data["transaction"] = TransactionSerializer(instance=transaction).data
        return data


class SubscriptionSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.filter(active=True)
    )
    subscription_type = SubscriptionTypeSerializer()

    class Meta:
        model = Subscription
        fields = (
            "pk",
            "organization",
            "subscription_type",
            "start_date",
            "end_date",
            "unity_time_number",
            "active_status",
        )
