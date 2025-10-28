# -*- coding: utf-8 -*-
"""
Created on October 22 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.marketing.models import Discount
from apps.marketing.serializers.discount_rules import DiscountUsageRuleSerializer, DiscountValidationRuleSerializer
from apps.marketing.services.discounts import create_discount_validation_rule, create_discount_usage_rule
from apps.organizations.models import Organization
from apps.organizations.serializers.coupons import OrganizationCouponSerializer
from apps.organizations.serializers.discount_conditions import OrganizationCreateDiscountConditionSerializer
from apps.xlib.enums import ErrorEnum, DISCOUNT_TARGET_TYPES_ENUM, DISCOUNT_TYPES_ENUM
from apps.xlib.error_util import ErrorUtil


class CreateOrganizationDiscountSerializer(serializers.ModelSerializer):
    conditions = OrganizationCreateDiscountConditionSerializer(many=True, required=False)

    discount_type = serializers.ChoiceField(choices=['PERCENTAGE', 'FIXED'])
    discount_value = serializers.DecimalField(decimal_places=2, max_digits=9, allow_null=True, required=False)
    max_uses_per_entity = serializers.IntegerField(default=1)

    class Meta:
        model = Discount
        fields = (
            "label", "starts_at", "ends_at", "minimal_amount", "usage_limit",
            "discount_value", "discount_type", "max_uses_per_entity", "conditions"
        )

    # Todo: validation on start not before today
    # Todo minimal_amount must be for example greater than 1000 FCFA
    def validate(self, attrs):
        data = super(CreateOrganizationDiscountSerializer, self).validate(attrs)
        organization = self.context.get("request").organization
        # Make validation about usage rule

        max_uses_per_entity = data.get("max_uses_per_entity", None)
        usage_limit = data.get("usage_limit", None)

        if max_uses_per_entity and usage_limit and max_uses_per_entity > usage_limit:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.WRONG_MAX_USES_PER_ENTITY),
                code=ErrorEnum.WRONG_MAX_USES_PER_ENTITY.value,
            )

        starts_at = data.get("starts_at", None)
        ends_at = data.get("ends_at", None)

        discount_type = data.get("discount_type")
        discount_value = data.get("discount_value", None)

        if starts_at and ends_at and starts_at > ends_at:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.START_DATE_AFTER_END_DATE),
                code=ErrorEnum.START_DATE_AFTER_END_DATE.value,
            )

        if discount_type == DISCOUNT_TYPES_ENUM.PERCENTAGE.value and not 0 < discount_value <= 100:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.WRONG_PERCENTAGE_VALUE),
                code=ErrorEnum.WRONG_PERCENTAGE_VALUE.value,
            )

        data["target_type"] = DISCOUNT_TARGET_TYPES_ENUM.TICKET.value

        data["discount_value"] = discount_value

        data["organization"] = organization
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

    def update(self, instance: Discount, validated_data):

        validated_data.pop("conditions", None)

        discount_type = validated_data.pop("discount_type")
        discount_value = validated_data.pop("discount_value")
        max_uses_per_entity = validated_data.pop("max_uses_per_entity")

        instance.usage_rule.max_uses = max_uses_per_entity
        instance.usage_rule.save(update_fields=["max_uses"])

        instance.validation_rule.type = discount_type
        instance.validation_rule.value = discount_value
        instance.validation_rule.save(update_fields=["type", "value"])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class OrganizationDiscountSerializer(serializers.ModelSerializer):
    # Todo: create validation for update view in order to make check on
    #  is_dynamique change ( if the is more thant on coupon created to this discount)
    #  and usage limit on update ( must )

    # Todo: validation on start at on update ( when ever there is usage of this discount )
    # Todo validation on ends at: not before start, if start not before today
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.filter(active=True),
                                                      required=False, )
    usage_rule = DiscountUsageRuleSerializer(read_only=True)
    validation_rule = DiscountValidationRuleSerializer(read_only=True)

    coupons = OrganizationCouponSerializer(many=True, read_only=True)

    class Meta:
        model = Discount
        fields = (
            "pk", "label", "target_type", "starts_at", "ends_at", "minimal_amount", "usage_limit",
            "usages_count", "usage_rule", "validation_rule", "organization", "coupons",
            "timestamp", "updated", "active"
        )

        extra_kwargs = {
            "updated": {"read_only": True},
            "timestamp": {"read_only": True},
            "usages_count": {"read_only": True},
            "organization": {"read_only": True},
            "target_type": {"read_only": True}
        }


__all__ = ["CreateOrganizationDiscountSerializer", "OrganizationDiscountSerializer", ]
