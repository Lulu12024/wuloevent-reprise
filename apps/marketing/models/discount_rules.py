# -*- coding: utf-8 -*-
"""
Created on 10/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
import logging
from typing import Union, TypeVar

from django.db import models

from apps.events.models import Ticket, EventHighlightingType
from apps.marketing.models.discount_usages import DiscountUsage
from apps.organizations.models import Organization, SubscriptionType
from apps.users.models import User
from apps.xlib.enums import DISCOUNT_USE_ENTITY_TYPES_ENUM, DISCOUNT_TYPES_ENUM, DISCOUNT_CONDITION_ENTITY_TYPES_ENUM
from commons.models import AbstractCommonBaseModel

logger = logging.getLogger(__name__)

UserTypeVar = TypeVar("UserTypeVar", bound=User)
TicketTypeVar = TypeVar("TicketTypeVar", bound=Ticket)
OrganizationTypeVar = TypeVar("OrganizationTypeVar", bound=Organization)
SubscriptionTypeTypeVar = TypeVar("SubscriptionTypeTypeVar", bound=SubscriptionType)
EventHighlightingTypeTypeVar = TypeVar("EventHighlightingTypeTypeVar", bound=EventHighlightingType)


class DiscountUsageRule(AbstractCommonBaseModel):
    entity_type = models.CharField(verbose_name="Type de l' entité", max_length=220,
                                   choices=DISCOUNT_USE_ENTITY_TYPES_ENUM.items(),
                                   default=DISCOUNT_USE_ENTITY_TYPES_ENUM.USER.value)
    # None if infinite usage else some value
    max_uses = models.BigIntegerField(verbose_name="Maximum d' usage", default=None, blank=True, null=True)

    def __str__(self):
        return "Limite d' usage Max {0}, par {1}".format(self.max_uses, self.related_entity_name)

    @property
    def related_entity_name(self) -> str:
        entity_name = "None"
        match self.entity_type:
            case DISCOUNT_USE_ENTITY_TYPES_ENUM.ORGANIZATION.value:
                return "Organisations"
            case DISCOUNT_USE_ENTITY_TYPES_ENUM.USER.value:
                return "Utilisateurs"
            case _:
                pass

        return entity_name

    def check_rule(self, obj: Union[OrganizationTypeVar, UserTypeVar]) -> bool:
        if self.max_uses is None:
            return True
        try:
            usage = DiscountUsage.objects.get(entity_id=obj.pk, entity_type=self.entity_type,
                                              discount_id=self.discount.pk)
        except Exception as exc:
            logger.warning(exc.__str__())
            return True

        return usage.usages < self.max_uses

    class Meta:
        verbose_name = "Limite d' usage de réduction"
        verbose_name_plural = "Limites d' usage des réductions"


class DiscountValidationRule(AbstractCommonBaseModel):
    type = models.CharField(verbose_name="Type", choices=DISCOUNT_TYPES_ENUM.items(),
                            default=DISCOUNT_TYPES_ENUM.PERCENTAGE.value, max_length=128)
    value = models.IntegerField(null=True, blank=True, default=None, verbose_name="Valeur")

    class Meta:
        verbose_name = "Règle de réduction"
        verbose_name_plural = "Règles de réductions"

    def __str__(self):
        return "{2} | Validation de type {0}, et de valeur {1}".format(self.type, self.value,
                                                                       self.discount.label)

    def evaluate_conditions_for_target(self, target, entity, consumer):
        # Check Organization Conditions
        conditions = self.conditions.all()
        condition_matched = True

        # Todo: where updating condition, assume that the right entity type is populated base discount model
        for condition in conditions:
            if condition.entity_type in [DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.ORGANIZATIONS.value,
                                         DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.USERS.value]:
                condition_matched &= condition.is_condition_matched(consumer.pk)
            else:
                condition_matched &= condition.is_condition_matched(entity.pk)

        return condition_matched

    def get_calculation_infos(self):
        value = self.value

        if self.type == DISCOUNT_TYPES_ENUM.PERCENTAGE.value:
            value = (100 - self.value) / 100

        return {
            "method": self.type,
            "value": value
        }


__all__ = ["DiscountUsageRule", "DiscountValidationRule"]
