# -*- coding: utf-8 -*-
"""
Created on 13/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from rest_framework import serializers

from apps.marketing.models import DiscountUsageRule, DiscountValidationRule
from apps.marketing.serializers.discount_conditions import DiscountConditionSerializer


class DiscountUsageRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountUsageRule
        fields = ("pk", "entity_type", "max_uses", "timestamp", "updated", "active")

        extra_kwargs = {
            "updated": {"read_only": True},
            "timestamp": {"read_only": True},
        }


class DiscountValidationRuleSerializer(serializers.ModelSerializer):
    conditions = DiscountConditionSerializer(many=True)

    class Meta:
        model = DiscountValidationRule
        fields = ("pk", "type", "value", "conditions", "timestamp", "updated", "active")

        extra_kwargs = {
            "updated": {"read_only": True},
            "timestamp": {"read_only": True},
            "usages_count": {"read_only": True},
        }


__all__ = ["DiscountUsageRuleSerializer", "DiscountValidationRuleSerializer", ]
