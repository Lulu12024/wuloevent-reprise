# -*- coding: utf-8 -*-
"""
Created on 22/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from rest_framework import filters
from rest_framework.filters import OrderingFilter
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin, DestroyModelMixin, ListModelMixin
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.marketing.models import Coupon
from apps.organizations.mixings import CheckParentPermissionMixin
from apps.organizations.models import Organization
from apps.organizations.permissions import IsOrganizationOwner, OrganizationHaveActiveSubscription
from apps.organizations.serializers.coupons import OrganizationCouponSerializer
from apps.utils.utils.baseviews import BaseGenericViewSet

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


class OrganizationCouponViewSet(CheckParentPermissionMixin, CreateModelMixin, ListModelMixin, UpdateModelMixin,
                                DestroyModelMixin,
                                BaseGenericViewSet):
    object_class = Coupon
    serializer_default_class = OrganizationCouponSerializer

    filter_backends = [OrderingFilter, filters.SearchFilter]
    search_fields = ["code", "discount__label"]

    ordering_fields = [
        "timestamp"
    ]

    parent_queryset = Organization.objects.filter(active=True)
    parent_lookup_field = "pk"
    parent_lookup_url_kwarg = "organization_pk"

    http_method_names = ["post", "get", "put", "delete"]

    permission_classes_by_action = {
        "create": [IsAuthenticated, OrganizationHaveActiveSubscription, IsOrganizationOwner],
        "retrieve": [AllowAny],
        "list": [IsAuthenticated, OrganizationHaveActiveSubscription, IsOrganizationOwner],
        "update": [IsAuthenticated, OrganizationHaveActiveSubscription, IsOrganizationOwner],
        "destroy": [IsAuthenticated, OrganizationHaveActiveSubscription, IsOrganizationOwner],
    }

    def get_queryset(self):
        return self.object_class.objects.filter(discount__organization_id=self.request.organization.pk)

    def update(self, request, *args, **kwargs):
        kwargs.update({"partial": True})
        return super().update(request, *args, **kwargs)


__all__ = ["OrganizationCouponViewSet", ]
