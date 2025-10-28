# -*- coding: utf-8 -*-
"""
Created on 22/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema_view, extend_schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework.mixins import DestroyModelMixin, UpdateModelMixin, CreateModelMixin
from rest_framework.permissions import IsAuthenticated, IsAdminUser, OR

from apps.marketing.models import DiscountCondition
from apps.marketing.serializers.discount_conditions import DiscountConditionSerializer, \
    UpdateDiscountConditionSerializer
from apps.users.permissions import HasAppAdminPermissionFor
from apps.utils.utils.baseviews import BaseGenericViewSet

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


@method_decorator(name='create', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Discount-Condition-Create",
    operation_description="Créer une réduction",
    operation_summary="Conditions de réduction"
))
@method_decorator(name='update', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Discount-Condition-Update",
    operation_description="Mettre à jour une condition de réduction",
    operation_summary="Conditions de réduction"
))
@method_decorator(name='destroy', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Discount-Condition-Destroy",
    operation_description="Supprimer une condition de réduction",
    operation_summary="Conditions de réduction"
))
@extend_schema_view(
    update=extend_schema(
        description="Endpoint to update a discount condition",
        request=UpdateDiscountConditionSerializer(),
        responses={201: DiscountConditionSerializer()}
    )
)
class DiscountConditionViewSet(BaseGenericViewSet, CreateModelMixin, UpdateModelMixin, DestroyModelMixin):
    object_class = DiscountCondition
    serializer_default_class = DiscountConditionSerializer

    http_method_names = ["post", "put", "delete"]

    permission_classes_by_action = {
        "create": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor(
                    "Admin-Operation-Discount-Create"
                ),
            ),
        ],
        "update": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor(
                    "Admin-Operation-Discount-Update"
                ),
            ),
        ],
        "destroy": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor(
                    "Admin-Operation-Discount-Destroy"
                ),
            ),
        ],
    }

    serializer_classes_by_action = {
        "update": UpdateDiscountConditionSerializer
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    def update(self, request, *args, **kwargs):
        kwargs.update({"partial": True})
        return super().update(request, *args, **kwargs)


__all__ = ["DiscountConditionViewSet", ]
