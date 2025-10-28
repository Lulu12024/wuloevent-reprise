# -*- coding: utf-8 -*-
"""
Created on 10/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.db import models

from apps.events.models import Ticket, EventHighlightingType
from apps.organizations.models import Organization, SubscriptionType
from apps.users.models import User
from apps.utils.utils.codes.utils import get_blank_dict
from apps.xlib.enums import DISCOUNT_CONDITION_ENTITY_TYPES_ENUM, DISCOUNT_CONDITION_OPERATORS_ENUM
from commons.models import AbstractCommonBaseModel


class DiscountCondition(AbstractCommonBaseModel):
    validation_rule = models.ForeignKey(to="marketing.DiscountValidationRule", verbose_name="Règle relative",
                                        on_delete=models.CASCADE, related_name="conditions")
    entity_type = models.CharField(verbose_name="Entité relative", max_length=128,
                                   choices=DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.items(),
                                   default=DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.ORGANIZATIONS.value)
    operator = models.CharField(verbose_name="Opérateur", max_length=128,
                                choices=DISCOUNT_CONDITION_OPERATORS_ENUM.items(),
                                default=DISCOUNT_CONDITION_OPERATORS_ENUM.IN.value)
    target_ids = models.JSONField(verbose_name="Ids de l' entité cible", default=get_blank_dict)

    class Meta:
        verbose_name = "Condition de réduction"
        verbose_name_plural = "Condition de réductions"

    def __str__(self):
        return f"Condition des {self.entity_type} pour la règle {self.validation_rule.__str__()}"

    def is_condition_matched(self, entity_id):
        ids = self.target_ids

        base_queryset = None
        match self.entity_type:
            case DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.EVENT_HIGHLIGHTING_TYPES.value:
                base_queryset = EventHighlightingType.objects.filter(pk__in=ids)
            case DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.SUBSCRIPTION_TYPES.value:
                base_queryset = SubscriptionType.objects.filter(pk__in=ids)
            case DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.ORGANIZATIONS.value:
                base_queryset = Organization.objects.filter(pk__in=ids)
            case DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.USERS.value:
                base_queryset = User.objects.filter(pk__in=ids)
            case DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.EVENTS.value:
                base_queryset = Ticket.objects.filter(event_id__in=ids)
            case DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.TICKETS.value:
                base_queryset = Ticket.objects.filter(pk__in=ids)
            case DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.TICKET_CATEGORIES.value:
                base_queryset = Ticket.objects.filter(category_id__in=ids)

        evaluator = base_queryset.filter(pk=entity_id).exists()

        return evaluator if self.operator == DISCOUNT_CONDITION_OPERATORS_ENUM.IN.value else not evaluator


__all__ = [
    "DiscountCondition",
]
