# -*- coding: utf-8 -*-
"""
Created on 13/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.marketing.models import DiscountCondition, DiscountValidationRule
from apps.marketing.serializers.discount_conditions import CreateDiscountConditionListSerializer
from apps.xlib.enums import DISCOUNT_CONDITION_ENTITY_TYPES_ENUM, ErrorEnum

available_entity_types_for_tickets = [DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.USERS.value,
                                      DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.EVENTS.value,
                                      DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.TICKETS.value,
                                      DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.TICKET_CATEGORIES.value]


@extend_schema_serializer(
    exclude_fields=('validation_rule_id',),  # schema ignore these fields
)
class OrganizationCreateDiscountConditionSerializer(serializers.ModelSerializer):
    validation_rule_id = serializers.UUIDField(required=True)
    entity_type = serializers.ChoiceField(choices=available_entity_types_for_tickets)

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

        if entity_type not in available_entity_types_for_tickets:
            raise ValidationError(
                f"Vous ne pouvez pas ajouter une"
                f" condition sur les {entity_type} pour les réduction de type {discount_target_type}",
                code=ErrorEnum.INCOMPATIBLE_CHOICE_BETWEEN_DISCOUNT_TYPE_AND_CONDITION_ENTITY.value,
            )

        return super(OrganizationCreateDiscountConditionSerializer, self).validate(attrs)


class OrganizationDiscountConditionSerializer(serializers.ModelSerializer):
    validation_rule = serializers.PrimaryKeyRelatedField(queryset=DiscountValidationRule.objects.filter(active=True))
    entity_type = serializers.ChoiceField(choices=available_entity_types_for_tickets)

    class Meta:
        model = DiscountCondition
        fields = ("pk", "validation_rule", "entity_type", "operator", "target_ids", "timestamp", "updated", "active")

        extra_kwargs = {
            "updated": {"read_only": True},
            "timestamp": {"read_only": True},
        }

    def validate(self, _data):
        validated_data = super(OrganizationDiscountConditionSerializer, self).validate(_data)

        # Making custom validations
        validation_rule: DiscountValidationRule = validated_data.get("validation_rule")
        discount = validation_rule.discount

        entity_type = _data.get("entity_type")

        if entity_type not in available_entity_types_for_tickets:
            raise ValidationError(
                f"Vous ne pouvez pas ajouter une"
                f" condition sur les {entity_type} pour les réduction de type {discount.target_type}",
                code=ErrorEnum.INCOMPATIBLE_CHOICE_BETWEEN_DISCOUNT_TYPE_AND_CONDITION_ENTITY.value,
            )
        return validated_data


__all__ = ["OrganizationDiscountConditionSerializer", "OrganizationCreateDiscountConditionSerializer"]
