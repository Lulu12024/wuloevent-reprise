# -*- coding: utf-8 -*-
"""
Created on August 3, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import django_filters

from apps.events.models import ETicket, Order
from apps.organizations.models import Subscription


class SubscriptionFilter(django_filters.FilterSet):
    organization_pk = django_filters.CharFilter(field_name='organization__pk', lookup_expr='exact')
    subscription_type_pk = django_filters.CharFilter(field_name='subscription_type__pk', lookup_expr='exact')

    class Meta:
        model = Subscription
        fields = ['organization_pk', 'subscription_type_pk', 'active_status']


class ETicketFilter(django_filters.FilterSet):
    event = django_filters.CharFilter(field_name='event__pk', lookup_expr='exact')
    ticket = django_filters.CharFilter(field_name='ticket__pk', lookup_expr='exact')
    order = django_filters.CharFilter(field_name='related_order_id', lookup_expr='exact')
    user = django_filters.CharFilter(method="filter_by_user")

    class Meta:
        model = ETicket
        fields = ['event', 'ticket', 'order', 'is_downloaded']

    def filter_by_user(self, queryset, name, value):
        orders_ids = [str(elmt.pk) for elmt in Order.objects.filter(user_id=value).only('pk')]
        return queryset.filter(related_order_id__in=orders_ids)
