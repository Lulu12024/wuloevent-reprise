# -*- coding: utf-8 -*-
"""
Created on 22/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.db import transaction
from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import CreateModelMixin, ListModelMixin, UpdateModelMixin, DestroyModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.events.permissions import OrganizationIsObjectCreator
from apps.marketing.models import Discount
from apps.marketing.serializers.discount_conditions import CreateDiscountConditionSerializer
from apps.marketing.serializers.discounts import DiscountUsageSerializer
from apps.organizations.mixings import CheckParentPermissionMixin
from apps.organizations.models import Organization
from apps.organizations.permissions import IsOrganizationOwner, OrganizationHaveActiveSubscription
from apps.organizations.serializers.discounts import CreateOrganizationDiscountSerializer, \
    OrganizationDiscountSerializer
from apps.utils.utils.baseviews import BaseGenericViewSet

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


@extend_schema_view(
    create=extend_schema(
        description="Endpoint to create a discount for an organization",
        request=CreateOrganizationDiscountSerializer(),
        responses={201: OrganizationDiscountSerializer()}
    )
)
@extend_schema_view(
    list=extend_schema(
        description="Endpoint to get a list of discount of an organization",
        responses={200: OrganizationDiscountSerializer()}
    )
)
@extend_schema_view(
    update=extend_schema(
        description="Endpoint to update an organization a discount",
        request=OrganizationDiscountSerializer(),
        responses={200: OrganizationDiscountSerializer()}
    )
)
@extend_schema_view(
    usages=extend_schema(
        description="Endpoint to view an organization discount usage",
        responses={200: DiscountUsageSerializer(many=True)}
    )
)
class OrganizationDiscountViewSet(
    CheckParentPermissionMixin, CreateModelMixin, UpdateModelMixin, ListModelMixin, DestroyModelMixin,
    BaseGenericViewSet
):
    permission_classes = [IsAuthenticated, IsOrganizationOwner]
    authentication_classes = [JWTAuthentication]
    object_class = Discount
    serializer_class = OrganizationDiscountSerializer
    serializer_default_class = OrganizationDiscountSerializer

    parent_queryset = Organization.objects.filter(active=True)
    parent_lookup_field = "pk"
    parent_lookup_url_kwarg = "organization_pk"

    filter_backends = [OrderingFilter]

    ordering_fields = [
        "timestamp"
    ]

    permission_classes_by_action = {
        "create": [
            IsAuthenticated,
            OrganizationHaveActiveSubscription,
            IsOrganizationOwner
        ],

        "list": [
            IsAuthenticated,
            OrganizationHaveActiveSubscription,
            IsOrganizationOwner
        ],
        "update": [
            IsAuthenticated,
            OrganizationHaveActiveSubscription,
            OrganizationIsObjectCreator,
            IsOrganizationOwner
        ],
        "usages": [
            IsAuthenticated,
            OrganizationHaveActiveSubscription,
            OrganizationIsObjectCreator,
            IsOrganizationOwner
        ],
        "destroy": [
            IsAuthenticated,
            OrganizationHaveActiveSubscription,
            OrganizationIsObjectCreator,
            IsOrganizationOwner
        ],
    }

    serializer_classes_by_action = {
        "create": CreateOrganizationDiscountSerializer,
        "bloc_update": CreateOrganizationDiscountSerializer,
    }

    def get_queryset(self):
        if self.action in ["list", "bloc_update"]:
            queryset = self.object_class.objects.prefetch_related("coupons", ).select_related("organization",
                                                                                              "usage_rule",
                                                                                              "validation_rule").filter(
                organization_id=self.request.organization.pk)
        else:
            queryset = self.object_class.objects.filter(
                organization_id=self.request.organization.pk)

        return queryset

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # First, make data copy in order to allow modification
        data = request.data.copy()

        # Second,  the conditions dataset
        conditions_data = data.pop("conditions", [])

        # Third create the discount
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        discount = serializer.save()

        # Fourth create the conditions if condition payload is not empty
        if conditions_data:
            condition_serializer = CreateDiscountConditionSerializer(
                data=[{"validation_rule_id": discount.validation_rule_id, **elmt} for elmt in conditions_data],
                many=True,
                context={"request": request, "discount_target_type": discount.target_type}
            )
            condition_serializer.is_valid(raise_exception=True)
            self.perform_create(condition_serializer)

        return Response(OrganizationDiscountSerializer(discount).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        kwargs.update({"partial": True})
        return super().update(request, *args, **kwargs)

    @action(methods=["GET"], detail=True, url_path="usages")
    def usages(self, request, pk, *args, **kwargs):
        discount = self.get_queryset().prefetch_related("usages").get(pk=pk)
        serializer = DiscountUsageSerializer(discount.usages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["PUT"], detail=True, url_path="bloc-update")
    def bloc_update(self, request, *args, **kwargs):
        discount = get_object_or_404(self.get_queryset(), **{self.lookup_field: self.kwargs["pk"]})
        serializer = self.get_serializer(discount, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(OrganizationDiscountSerializer(discount).data, status=status.HTTP_200_OK)
