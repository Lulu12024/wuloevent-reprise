# -*- coding: utf-8 -*-
"""
Created on November 26 2024
@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from apps.events.models import EventHighlightingType, Event, Ticket, TicketCategory
from apps.marketing.models import DiscountCondition
from apps.organizations.models import SubscriptionType, Organization
from apps.users.models import User
from apps.xlib.enums import DISCOUNT_CONDITION_ENTITY_TYPES_ENUM


def get_discount_condition_target_entity_type_queryset(discount_condition: DiscountCondition):
    ids = discount_condition.target_ids

    base_queryset = None
    match discount_condition.entity_type:
        case DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.EVENT_HIGHLIGHTING_TYPES.value:
            base_queryset = EventHighlightingType.objects.filter(pk__in=ids)
        case DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.SUBSCRIPTION_TYPES.value:
            base_queryset = SubscriptionType.objects.filter(pk__in=ids)
        case DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.ORGANIZATIONS.value:
            base_queryset = Organization.objects.filter(pk__in=ids)
        case DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.USERS.value:
            base_queryset = User.objects.filter(pk__in=ids)
        case DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.EVENTS.value:
            base_queryset = Event.objects.filter(pk__in=ids)
        case DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.TICKETS.value:
            base_queryset = Ticket.objects.filter(pk__in=ids)
        case DISCOUNT_CONDITION_ENTITY_TYPES_ENUM.TICKET_CATEGORIES.value:
            base_queryset = TicketCategory.objects.filter(pk__in=ids)

    return base_queryset
