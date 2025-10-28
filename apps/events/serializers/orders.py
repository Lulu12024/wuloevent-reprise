# -*- coding: utf-8 -*-
"""
Created on June 05, 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.exceptions import APIException, ValidationError

from apps.events.models import (
    Ticket,
    Order,
    OrderItem,
)
from apps.events.serializers import LightEventSerializer
from apps.marketing.models import Coupon, Discount
from apps.marketing.services.discounts import (
    is_discount_available_to_user_or_organization,
    get_discounted_value,
    apply_best_automatic_discount,
    create_automatic_coupon_for_discount
)
from apps.users.models import Transaction
from apps.users.serializers import UserSerializerLight
from apps.users.serializers.transactions import TransactionSerializer
from apps.xlib.enums import TransactionKindEnum, TransactionStatusEnum, TRANSACTIONS_POSSIBLE_GATEWAYS
from apps.xlib.error_util import ErrorUtil, ErrorEnum

User = get_user_model()

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class OrderItemSerializer(serializers.ModelSerializer):
    ticket = serializers.PrimaryKeyRelatedField(
        queryset=Ticket.objects.filter(active=True)
    )

    class Meta:
        model = OrderItem
        fields = ("pk", "ticket", "quantity", "line_total")

        extra_kwargs = {
            "line_total": {"read_only": True},
        }

    def validate(self, attrs):
        ticket = attrs.get("ticket", None)
        quantity = attrs.get("quantity", None)
        if ticket.available_quantity != -1 and int(ticket.available_quantity) < int(
                quantity
        ):
            raise APIException(
                ErrorUtil.get_error_detail(
                    ErrorEnum.INVALID_EVENT_DATA,
                    f"Il ne reste que {ticket.available_quantity} de ce type de ticket que vous voulez",
                ),
                code=ErrorEnum.INSUFFICIENT_TICKET_QUANTITY.value,
            )
        return super().validate(attrs)


class TicketDetailSerializer(serializers.ModelSerializer):
    event = LightEventSerializer()
    category = serializers.SlugRelatedField(read_only=True, slug_field='name')

    class Meta:
        model = Ticket
        fields = (
            "pk",
            "name",
            "organization",
            "event",
            "category",
            "description",
            "price",
            "expiry_date",
            "initial_quantity",
            "available_quantity",
        )

        extra_kwargs = {
            "active": {"read_only": True},
        }


class OrderDetailItemSerializer(serializers.ModelSerializer):
    ticket = TicketDetailSerializer()

    class Meta:
        model = OrderItem
        fields = ("pk", "ticket", "quantity", "line_total")

        extra_kwargs = {
            "line_total": {"read_only": True},
        }


class OrderSerializer(serializers.ModelSerializer):
    # Todo: Upgrade sql queries flow
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True), required=False, default=None,
    )
    coupon = serializers.SlugRelatedField(queryset=Coupon.objects.filter(active=True), slug_field="code",
                                          write_only=True, required=False)
    item = OrderItemSerializer()
    ip_address = serializers.CharField(required=False, default=None, allow_null=False, read_only=True)
    total = serializers.SerializerMethodField(read_only=True)

    @extend_schema_field(serializers.FloatField)
    def get_total(self, instance: Order) -> int:
        return instance.total

    def validate_user(self, value):
        # Todo: Check right usage of the "request. user" attr in case of admin request or not
        is_pseudo_anonymous_request = self.context.get("is_pseudo_anonymous_request", False)
        if is_pseudo_anonymous_request:
            return self.context.get("user")
        if not self.context["request"].user.is_anonymous:
            return self.context["request"].user

    def validate_ip_address(self, value):
        return self.context["request"].META.get("REMOTE_ADDR", "Impossible To Get")

    def create(self, validated_data):
        enable_payment = True
        order_item_data = validated_data.pop("item")
        coupon = validated_data.pop("coupon", None)

        if len(order_item_data) < 1:
            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.INSUFFICIENT_ITEMS_FOR_ORDERING),
                code=ErrorEnum.INSUFFICIENT_ITEMS_FOR_ORDERING.value,
            )

        order_item = OrderItem.objects.create(**order_item_data)
        order_amount = order_item.line_total

        # Check for automatic discounts if no manual coupon is provided
        auto_coupon = None
        if not coupon:
            best_discount, _ = apply_best_automatic_discount(
                target=order_item.ticket,
                target_quantity=order_item.quantity,
                target_price=order_amount,
                user=validated_data.get('user'),
                organization=getattr(validated_data.get('user'), 'organization', None)
            )

            if best_discount:
                # Créer un coupon automatique pour cette réduction
                auto_coupon = create_automatic_coupon_for_discount(best_discount)
                coupon = auto_coupon

        order: Order = super(OrderSerializer, self).create(
            {
                "item_id": order_item.pk,
                "is_pseudo_anonymous": self.context.get("is_pseudo_anonymous_request", False),
                **validated_data
            })

        if enable_payment:
            request = self.context.get("request")
            auto_resolve_transaction = self.context.get("auto_resolve_transaction", False)

            transaction_payload = {
                "type": TransactionKindEnum.ORDER.value,
                "status": TransactionStatusEnum.PENDING.value,
                "description": "-",
                "amount": str(order_amount),
                "entity_id": str(order.pk),
                "user": str(validated_data.get('user').pk)
            }

            # In case there is coupon
            discount_is_available = False
            reduced_amount = order_amount
            if coupon:
                discount = Discount.objects \
                    .select_related("usage_rule", "validation_rule") \
                    .get(pk=coupon.discount_id)
                is_automatic = auto_coupon and auto_coupon.pk == coupon.pk

                # Check if the coupon is for the organization who's ticket is going to be bought
                if discount.organization_id != order_item.ticket.organization_id:
                    # Si c'est un coupon automatique qui ne correspond pas, on l'ignore simplement
                    if is_automatic:
                        coupon = None
                    else:
                        raise ValidationError(
                            ErrorUtil.get_error_detail(ErrorEnum.DISCOUNT_FOR_TICKET_NOT_APPLICABLE_TO_ORGANIZATION),
                            code=ErrorEnum.DISCOUNT_FOR_TICKET_NOT_APPLICABLE_TO_ORGANIZATION.value,
                        )
                else:
                    discount_is_available, message, code = is_discount_available_to_user_or_organization(
                        discount,
                        entity=order_item.ticket,
                        entity_quantity=order_item.quantity,
                        organization=None,
                        user=validated_data.get('user')
                    )
                    if discount_is_available:
                        calculation_infos = discount.validation_rule.get_calculation_infos()

                        reduced_amount = get_discounted_value(initial_value=order_amount,
                                                              discount_calculation_info=calculation_infos)

                        # Ajouter un indicateur pour les coupons automatiques

                        coupon_metadata = {
                            "use_coupon": True,
                            "coupon_id": str(coupon.pk),
                            "coupon_code": coupon.code,
                            "calculation_method": calculation_infos,
                            "initial_amount": str(order_amount),
                            "reduced_amount": str(reduced_amount),
                            "is_automatic": is_automatic
                        }
                        transaction_payload["amount"] = str(reduced_amount)
                        transaction_payload["coupon_metadata"] = coupon_metadata

                        order.item.potential_discount_data = coupon_metadata
                        order.item.save(update_fields=['potential_discount_data'])

                        order.has_been_discounted = True
                        order.save(update_fields={"has_been_discounted"})

                    else:
                        # Si c'est un coupon automatique qui n'est pas disponible, on l'ignore simplement
                        if is_automatic:
                            coupon = None
                        else:
                            raise ValidationError(
                                detail=message,
                                code=code,
                            )

            # In case the request is made by an admin user
            if auto_resolve_transaction:
                transaction_payload['gateway'] = TRANSACTIONS_POSSIBLE_GATEWAYS.INTERNAL_AUTO.value

            # In case coupon used is available, use FREE_SHIPPING Gateway
            if (reduced_amount == 0 and coupon and discount_is_available) or (not coupon and order_amount == 0):
                transaction_payload["gateway"] = (
                    TRANSACTIONS_POSSIBLE_GATEWAYS.FREE_SHIPPING.value
                )
            transaction_serializer = TransactionSerializer(data=transaction_payload)
            transaction_serializer.is_valid(raise_exception=True)
            transaction = transaction_serializer.save()
            transaction.process_payment()

        return order

    def to_representation(self, instance):
        data = super().to_representation(instance)
        transaction = Transaction.objects.get(entity_id=instance.pk, type=TransactionKindEnum.ORDER.value)
        data["transaction"] = TransactionSerializer(instance=transaction).data
        return data

    class Meta:
        model = Order
        fields = (
            "pk",
            "order_id",
            "user",
            "ip_address",
            "name",
            "item",
            "email",
            "sex",
            "coupon",
            "is_income_distributed",
            "phone",
            "total",
            "status",
        )
        read_only_fields = ("pk", "user",)

        extra_kwargs = {
            "status": {"read_only": True},
            "order_id": {"read_only": True},
            "total": {"read_only": True},
            "item": {"read_only": True},
            "is_income_distributed": {"read_only": True},
        }


class OrderDetailSerializer(serializers.ModelSerializer):
    user = UserSerializerLight()
    coupon = serializers.SlugRelatedField(queryset=Coupon.objects.filter(active=True), slug_field="code",
                                          write_only=True, required=False)
    item = OrderDetailItemSerializer()
    ip_address = serializers.CharField(required=False, default=None, allow_null=False)
    total = serializers.SerializerMethodField()

    @extend_schema_field(serializers.FloatField)
    def get_total(self, instance: Order) -> int:
        return instance.total

    def to_representation(self, instance):
        data = super().to_representation(instance)
        transaction = Transaction.objects.get(entity_id=instance.pk, type=TransactionKindEnum.ORDER.value)
        data["transaction"] = TransactionSerializer(instance=transaction).data
        return data

    class Meta:
        model = Order
        fields = (
            "pk",
            "order_id",
            "user",
            "ip_address",
            "name",
            "item",
            "email",
            "sex",
            "coupon",
            "is_income_distributed",
            "phone",
            "total",
            "status",
        )

        extra_kwargs = {
            "status": {"read_only": True},
            "order_id": {"read_only": True},
            "ip_address": {"write_only": True},
            "total": {"read_only": True},
            "item": {"read_only": True},
            "is_income_distributed": {"read_only": True},
        }
