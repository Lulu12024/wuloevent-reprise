# -*- coding: utf-8 -*-
"""
Created on 13/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.marketing.models import DiscountUsage, Discount
from apps.marketing.serializers.discount_conditions import CreateDiscountConditionSerializer
from apps.marketing.serializers.discount_rules import DiscountUsageRuleSerializer, DiscountValidationRuleSerializer
from apps.marketing.services.discounts import create_discount_validation_rule, create_discount_usage_rule
from apps.organizations.models import Organization
from apps.xlib.enums import DISCOUNT_TYPES_ENUM, ErrorEnum
from apps.xlib.error_util import ErrorUtil


class CreateDiscountSerializer(serializers.ModelSerializer):
    conditions = CreateDiscountConditionSerializer(many=True, required=False)
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.filter(active=True),
                                                      required=False, allow_empty=True)

    discount_type = serializers.ChoiceField(choices=DISCOUNT_TYPES_ENUM.values())
    discount_value = serializers.DecimalField(decimal_places=2, max_digits=9, allow_null=True, required=False)
    max_uses_per_entity = serializers.IntegerField(default=1)

    class Meta:
        model = Discount
        fields = (
            "label", "target_type", "starts_at", "ends_at", "is_dynamic", "minimal_amount", "usage_limit",
            "discount_type", "discount_value", "max_uses_per_entity", "organization", "conditions", "is_automatic"
        )

    # Todo: validation on start not before today
    # Todo minimal_amount must be for example greater than 1000 FCFA
    def validate(self, attrs):
        data = super(CreateDiscountSerializer, self).validate(attrs)
        # Make validation about usage rule
        max_uses_per_entity = data.get("max_uses_per_entity", None)
        usage_limit = data.get("usage_limit", None)

        if max_uses_per_entity and usage_limit and max_uses_per_entity > usage_limit:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.WRONG_MAX_USES_PER_ENTITY),
                code=ErrorEnum.WRONG_MAX_USES_PER_ENTITY.value,
            )

        # Make validation about validation rule
        discount_type = data.get("discount_type")

        starts_at = data.get("starts_at", None)
        ends_at = data.get("ends_at", None)

        discount_value = data.get("discount_value", None)
        minimal_amount = data.get("minimal_amount", None)

        if starts_at and ends_at and starts_at > ends_at:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.START_DATE_AFTER_END_DATE),
                code=ErrorEnum.START_DATE_AFTER_END_DATE.value,
            )

        if discount_type == DISCOUNT_TYPES_ENUM.FREE_SHIPPING.value:
            discount_value = None
        elif discount_type == DISCOUNT_TYPES_ENUM.PERCENTAGE.value:
            if not 0 < discount_value <= 100:
                raise ValidationError(
                    ErrorUtil.get_error_detail(ErrorEnum.WRONG_PERCENTAGE_VALUE),
                    code=ErrorEnum.WRONG_PERCENTAGE_VALUE.value,
                )
        else:
            # Assuming the discount type is fixed
            if minimal_amount and minimal_amount <= discount_value:
                raise ValidationError(
                    ErrorUtil.get_error_detail(ErrorEnum.FIXED_AMOUNT_VALUE_GREATER_THAN_MINIMAL_VALUE),
                    code=ErrorEnum.FIXED_AMOUNT_VALUE_GREATER_THAN_MINIMAL_VALUE.value,
                )

        data["discount_value"] = discount_value
        return data

    def create(self, validated_data):

        discount_type = validated_data.pop("discount_type")
        discount_value = validated_data.pop("discount_value")
        max_uses_per_entity = validated_data.pop("max_uses_per_entity")

        # Create discount
        discount: Discount = super().create(validated_data)

        # Create related rules
        usage_rule = create_discount_usage_rule(discount, max_uses_per_entity)
        validation_rule = create_discount_validation_rule(discount_type, discount_value)

        # Link related rule
        discount.usage_rule = usage_rule
        discount.validation_rule = validation_rule
        discount.save(update_fields=["usage_rule", "validation_rule"])

        return discount


class DiscountSerializer(serializers.ModelSerializer):
    # Todo: create validation for update view in order to make check on
    #  is_dynamique change ( if the is more thant on coupon created to this discount)
    #  and usage limit on update ( must )

    # Todo: validation on start at on update ( when ever there is usage of this discount )
    # Todo validation on ends at: not before start, if start not before today
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.filter(active=True),
                                                      required=False, )
    usage_rule = DiscountUsageRuleSerializer(read_only=True)
    validation_rule = DiscountValidationRuleSerializer(read_only=True)

    class Meta:
        model = Discount
        fields = (
            "pk", "label", "target_type", "starts_at", "ends_at", "is_dynamic", "minimal_amount", "usage_limit",
            "usages_count", "usage_rule", "validation_rule", "organization", "is_automatic",
            "timestamp", "updated", "active"
        )

        extra_kwargs = {
            "updated": {"read_only": True},
            "timestamp": {"read_only": True},
            "usages_count": {"read_only": True},
            "target_type": {"read_only": True}
        }


class DiscountUsageSerializer(serializers.ModelSerializer):
    discount = serializers.PrimaryKeyRelatedField(queryset=Discount.objects.filter(active=True))

    class Meta:
        model = DiscountUsage
        fields = ("pk", "entity_id", "entity_type", "discount", "usages", "timestamp", "updated")

        extra_kwargs = {
            "updated": {"read_only": True},
            "timestamp": {"read_only": True}
        }


__all__ = ["CreateDiscountSerializer", "DiscountSerializer", "DiscountUsageSerializer"]
