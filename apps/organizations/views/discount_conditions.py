# -*- coding: utf-8 -*-
"""
Created on 23/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from rest_framework.mixins import CreateModelMixin, UpdateModelMixin, DestroyModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.events.permissions import IsPasswordConfirmed
from apps.marketing.models import DiscountCondition
from apps.marketing.serializers.discount_conditions import UpdateDiscountConditionSerializer
from apps.organizations.mixings import CheckParentPermissionMixin
from apps.organizations.models import Organization
from apps.organizations.permissions import IsOrganizationOwner, OrganizationHaveActiveSubscription
from apps.organizations.serializers.discount_conditions import OrganizationDiscountConditionSerializer, \
    OrganizationCreateDiscountConditionSerializer
from apps.utils.utils.baseviews import BaseGenericViewSet

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class OrganizationDiscountConditionViewSet(
    CheckParentPermissionMixin, CreateModelMixin, UpdateModelMixin, DestroyModelMixin,
    BaseGenericViewSet
):
    permission_classes = [IsAuthenticated, IsOrganizationOwner]
    authentication_classes = [JWTAuthentication]
    object_class = DiscountCondition
    serializer_class = OrganizationDiscountConditionSerializer
    serializer_default_class = OrganizationDiscountConditionSerializer

    parent_queryset = Organization.objects.filter(active=True)
    parent_lookup_field = "pk"
    parent_lookup_url_kwarg = "organization_pk"

    permission_classes_by_action = {
        "create": [
            IsAuthenticated,
            OrganizationHaveActiveSubscription,
            IsOrganizationOwner
        ],
        "update": [
            IsAuthenticated,
            OrganizationHaveActiveSubscription,
            IsOrganizationOwner
        ],
        "destroy": [
            IsAuthenticated,
            OrganizationHaveActiveSubscription,
            IsPasswordConfirmed,
            IsOrganizationOwner
        ],
    }

    serializer_classes_by_action = {
        "create": OrganizationCreateDiscountConditionSerializer,
        "update": UpdateDiscountConditionSerializer
    }

    def get_queryset(self):
        return self.object_class.objects.filter(validation_rule__discount__organization_id=self.request.organization.pk)

    def update(self, request, *args, **kwargs):
        kwargs.update({"partial": True})
        return super().update(request, *args, **kwargs)
