# -*- coding: utf-8 -*-
"""
Created on 13/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
from abc import ABC
from typing import List

from drf_spectacular.utils import extend_schema_serializer, extend_schema_field
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.marketing.business_logics.discount_conditions import get_discount_condition_target_entity_type_queryset
from apps.marketing.models import DiscountCondition, DiscountValidationRule
from apps.xlib.enums import DISCOUNT_CONDITION_ENTITY_TYPES_ENUM, ErrorEnum

available_entity_types_per_target_type = {
    "EVENT_HIGHLIGHTING": [
        DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.EVENT_HIGHLIGHTING_TYPES.value,
        DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.ORGANIZATIONS.value
    ],
    "SUBSCRIPTION": [DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.SUBSCRIPTION_TYPES.value,
                     DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.ORGANIZATIONS.value],
    "TICKET": [DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.USERS.value,
               DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.EVENTS.value,
               DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.TICKETS.value,
               DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.TICKET_CATEGORIES.value]

}


class CreateDiscountConditionListSerializer(serializers.ListSerializer, ABC):

    def create(self, validated_data):
        discounts = [DiscountCondition(**item) for item in validated_data]
        return DiscountCondition.objects.bulk_create(discounts)


@extend_schema_serializer(
    exclude_fields=('validation_rule_id',),  # schema ignore these fields
)
class CreateDiscountConditionSerializer(serializers.ModelSerializer):
    validation_rule_id = serializers.UUIDField(required=True)

    # Todo:  Make validation on target ids to assume the presence
    #  of related entity elmts with id provided
    target_ids = serializers.ListField(required=True, allow_null=True, allow_empty=True, child=serializers.CharField())

    # entity_type = serializers.ChoiceField(choices=["USERS", "EVENTS", "TICKETS", "TICKET_CATEGORIES"])

    class Meta:
        model = DiscountCondition
        fields = ("pk", "validation_rule_id", "entity_type", "operator", "target_ids",)
        list_serializer_class = CreateDiscountConditionListSerializer

    def validate(self, attrs):
        discount_target_type = self.context.get("discount_target_type")
        entity_type = attrs.get("entity_type")

        if entity_type not in available_entity_types_per_target_type.get(discount_target_type, []):
            raise ValidationError(
                f"Vous ne pouvez pas ajouter une"
                f" condition sur les {entity_type} pour les réduction de type {discount_target_type}",
                code=ErrorEnum.INCOMPATIBLE_CHOICE_BETWEEN_DISCOUNT_TYPE_AND_CONDITION_ENTITY.value,
            )

        return super(CreateDiscountConditionSerializer, self).validate(attrs)


class UpdateDiscountConditionSerializer(serializers.ModelSerializer):
    validation_rule = serializers.PrimaryKeyRelatedField(required=False, read_only=True)
    target_ids = serializers.ListField(required=True, allow_null=True, allow_empty=True, child=serializers.CharField())

    # Todo:  Make validation on target ids to assume the presence
    #  of related entity elmts with id provided
    class Meta:
        model = DiscountCondition
        fields = ("pk", "validation_rule", "entity_type", "operator", "target_ids", "timestamp", "updated", "active")
        extra_kwargs = {
            "validation_rule": {"read_only": True},
            "entity_type": {"read_only": True},
            "updated": {"read_only": True},
            "timestamp": {"read_only": True},
        }


class DiscountConditionSerializer(serializers.ModelSerializer):
    validation_rule = serializers.PrimaryKeyRelatedField(queryset=DiscountValidationRule.objects.filter(active=True))
    targets = serializers.SerializerMethodField()

    @extend_schema_field(serializers.ListField)
    def get_targets(self, obj: DiscountCondition) -> List:
        base_queryset = get_discount_condition_target_entity_type_queryset(obj)
        return [{"pk": item.pk, **item.get_entity_info} for item in base_queryset]

    class Meta:
        model = DiscountCondition
        fields = (
            "pk", "validation_rule", "entity_type", "operator", "target_ids", "targets", "timestamp", "updated",
            "active")
        extra_kwargs = {
            "updated": {"read_only": True},
            "timestamp": {"read_only": True},
        }

    def validate(self, _data):
        validated_data = super(DiscountConditionSerializer, self).validate(_data)

        # Making custom validations
        validation_rule: DiscountValidationRule = validated_data.get("validation_rule")
        discount = validation_rule.discount

        entity_type = _data.get("entity_type")

        if entity_type not in available_entity_types_per_target_type.get(discount.target_type, []):
            raise ValidationError(
                f"Vous ne pouvez pas ajouter une"
                f" condition sur les {entity_type} pour les réduction de type {discount.target_type}",
                code=ErrorEnum.INCOMPATIBLE_CHOICE_BETWEEN_DISCOUNT_TYPE_AND_CONDITION_ENTITY.value,
            )

        return validated_data


__all__ = ["CreateDiscountConditionListSerializer", "CreateDiscountConditionSerializer",
           "UpdateDiscountConditionSerializer", "DiscountConditionSerializer", ]
