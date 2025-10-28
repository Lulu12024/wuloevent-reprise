# -*- coding: utf-8 -*-
"""
Created on 12/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.db import transaction
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema_view, extend_schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, OR
from rest_framework.response import Response

from apps.marketing.models import Discount
from apps.marketing.serializers.discount_conditions import CreateDiscountConditionSerializer
from apps.marketing.serializers.discounts import DiscountUsageSerializer, DiscountSerializer, CreateDiscountSerializer
from apps.marketing.services.discounts import get_applicable_automatic_discounts
from apps.users.permissions import HasAppAdminPermissionFor
from apps.utils.paginator import Pagination
from apps.utils.utils.baseviews import BaseModelsViewSet

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


# Todo review permission per action list
# Todo implement filter for discounts lists
# Todo: Cache List
@method_decorator(name='create', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Discount-Create",
    operation_description="Créer une réduction",
    operation_summary="Réductions"
))
@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Discount-List",
    operation_description="Lister les réductions",
    operation_summary="Réductions"
))
@method_decorator(name='update', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Discount-Update",
    operation_description="Mettre à jour une réduction",
    operation_summary="Réductions"
))
@method_decorator(name='usages', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Discount-Usages",
    operation_description="Voir l' utilisation d' une réduction",
    operation_summary="Réductions"
))
@method_decorator(name='destroy', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Discount-Destroy",
    operation_description="Supprimer une réduction",
    operation_summary="Réductions"
))
@extend_schema_view(
    usages=extend_schema(
        description="Endpoint to view discount usage", responses={200: DiscountUsageSerializer(many=True)}
    )
)
@extend_schema_view(
    create=extend_schema(
        description="Endpoint to create a discount",
        request=CreateDiscountSerializer(),
        responses={201: DiscountSerializer()}
    )
)
class DiscountViewSet(BaseModelsViewSet):
    object_class = Discount
    serializer_default_class = DiscountSerializer
    pagination_class = Pagination

    filter_backends = [OrderingFilter, filters.SearchFilter]

    ordering_fields = [
        "timestamp"
    ]
    search_fields = ["label"]

    http_method_names = ["post", "get", "put", "delete"]

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
        "retrieve": [AllowAny],
        "list": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor(
                    "Admin-Operation-Discount-List"
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
        "usages": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Discount-Usages")
            )
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
        "create": CreateDiscountSerializer,
    }

    def get_queryset(self):
        return self.object_class.objects.all()

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

        return Response(DiscountSerializer(discount).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        kwargs.update({"partial": True})
        return super().update(request, *args, **kwargs)

    @action(methods=["GET"], detail=True, url_path="usages")
    def usages(self, request, pk, *args, **kwargs):
        discount = self.get_queryset().prefetch_related("usages").get(pk=pk)
        serializer = DiscountUsageSerializer(discount.usages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=False, url_path="check-automatic")
    def check_automatic_discounts(self, request, *args, **kwargs):
        """
        Vérifie les réductions automatiques applicables pour une entité donnée
        """
        target_type = request.data.get("target_type")
        target_id = request.data.get("target_id")
        target_quantity = request.data.get("quantity", 1)

        if not all([target_type, target_id]):
            return Response(
                {"detail": "Les paramètres target_type et target_id sont requis"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the target model class
        from apps.marketing.services.discounts import DISCOUNT_TARGET_TYPES
        target_model = DISCOUNT_TARGET_TYPES.get(target_type)
        if not target_model:
            return Response(
                {"detail": f"Type de cible invalide: {target_type}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            target = target_model.objects.get(pk=target_id)
        except target_model.DoesNotExist:
            return Response(
                {"detail": f"Entité cible non trouvée avec l'ID: {target_id}"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get applicable automatic discounts
        applicable_discounts = get_applicable_automatic_discounts(
            target=target,
            target_quantity=target_quantity,
            user=request.user if not request.user.is_anonymous else None,
            organization=getattr(request.user, 'organization', None)
        )

        return Response(
            DiscountSerializer(applicable_discounts, many=True).data,
            status=status.HTTP_200_OK
        )


__all__ = ["DiscountViewSet", ]
