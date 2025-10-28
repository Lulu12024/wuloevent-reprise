# -*- coding: utf-8 -*-
"""
Created on July 13, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import django_filters
from django.db.models import Q
from django.utils import timezone
from rest_framework import filters

from apps.events.models import Event, EventHighlightingType


class EventOrdering(filters.OrderingFilter):
    pass


class EventSearch(filters.SearchFilter):
    pass


class EventTypeSearch(filters.SearchFilter):
    pass


class EventFilter(django_filters.FilterSet):
    price = django_filters.NumberFilter()
    price_gt = django_filters.NumberFilter(field_name="default_price", lookup_expr="gt")
    price_lt = django_filters.NumberFilter(field_name="default_price", lookup_expr="lt")
    publisher = django_filters.CharFilter(
        field_name="publisher__pk", lookup_expr="exact"
    )
    expiry_date_gt = django_filters.DateTimeFilter(
        field_name="expiry_date", lookup_expr="gt"
    )
    expiry_date_lt = django_filters.DateTimeFilter(
        field_name="expiry_date", lookup_expr="lt"
    )
    is_passed = django_filters.BooleanFilter(method="filter_by_passed_events")

    class Meta:
        model = Event
        fields = ["have_passed_validation", "valid", "expiry_date"]

    def filter_by_passed_events(self, queryset, name, value):
        now = timezone.now()

        if value:
            query = Q(start_datetime__lt=now)
        else:
            query = Q(start_datetime__gte=now)

        return queryset.filter(query)


class EventHighlightingTypeFilter(django_filters.FilterSet):
    price_gt = django_filters.NumberFilter(field_name="price", lookup_expr="gt")
    price_lt = django_filters.NumberFilter(field_name="price", lookup_expr="lt")

    class Meta:
        model = EventHighlightingType
        fields = ["timestamp"]
