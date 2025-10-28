# -*- coding: utf-8 -*-
"""
Created on 25/07/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.db import transaction
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.filters import OrderingFilter
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny, OR
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.events.filters import EventHighlightingTypeFilter
from apps.events.models import EventHighlighting, EventHighlightingType
from apps.events.permissions import OrganizationIsObjectCreator
from apps.events.serializers import (
    EventHighlightingSerializer,
    EventHighlightingTypeSerializer,
)
from apps.organizations.mixings import CheckParentPermissionMixin
from apps.organizations.models import Organization
from apps.organizations.permissions import (
    IsOrganizationEventManager,
    OrganizationHaveActiveSubscription,
    IsOrganizationMember,
    IsOrganizationOwner,
)
from apps.users.models import Transaction
from apps.users.permissions import HasAppAdminPermissionFor
from apps.utils.utils.baseviews import BaseModelMixin, BaseModelsViewSet
from apps.xlib.error_util import ErrorUtil, ErrorEnum

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


@extend_schema_view(
    list=extend_schema(
        description="Endpoint to get event highlighting type list",
        parameters=[
            OpenApiParameter(
                "price_gt",
                OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
                description="Filter where event highlighting type' s price is greater than this value ",
            ),
            OpenApiParameter(
                "price_lt",
                OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
                description="Filter where event highlighting type' s price is lower than this value ",
            ),
        ],
    )
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Event-Highlighting-Type-Create",
        operation_description="Créer un type de mise en avant d' évènement",
        operation_summary="Types de mise en avant d' évènement",
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Event-Highlighting-Type-Update",
        operation_description="Mettre à jour un type de mise en avant d' évènement",
        operation_summary="Types de mise en avant d' évènement",
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Event-Highlighting-Type-Destroy",
        operation_description="Supprimer un type de mise en avant d' évènement",
        operation_summary="Types de mise en avant d' évènement",
    ),
)
class EventHighlightingTypeViewSet(BaseModelsViewSet):
    object_class = EventHighlightingType
    serializer_default_class = EventHighlightingTypeSerializer

    filter_backends = [OrderingFilter, DjangoFilterBackend]
    filterset_class = EventHighlightingTypeFilter

    ordering_fields = [
        "timestamp"
    ]

    http_method_names = ["post", "get", "put", "delete"]

    permission_classes_by_action = {
        "create": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor(
                    "Admin-Operation-Event-Highlighting-Type-Create"
                ),
            ),
        ],
        "retrieve": [AllowAny],
        "list": [AllowAny],
        "update": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor(
                    "Admin-Operation-Event-Highlighting-Type-Update"
                ),
            ),
        ],
        "destroy": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor(
                    "Admin-Operation-Event-Highlighting-Type-Destroy"
                ),
            ),
        ],
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    def update(self, request, *args, **kwargs):
        kwargs.update({"partial": True})
        return super().update(request, *args, **kwargs)


# Todo: Cache List
@extend_schema_view(
    create=extend_schema(
        description="Endpoint for creating event highlighting",
        parameters=[
            OpenApiParameter(
                "resolve_transaction",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Design if the transaction related to order should be resolve automatically ",
            ),
            OpenApiParameter(
                "from_admin",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
        ],
        responses=EventHighlightingSerializer(),
    )
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Event-Highlighting-Create",
        operation_description="Créer une mise en avant d' un évènement",
        operation_summary="Mises en avant évènement",
    ),
)
@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Event-Highlighting-List",
        operation_description="Récupérer la liste des mises en avant évènements",
        operation_summary="Mises en avant évènement",
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Event-Highlighting-Destroy",
        operation_description="Supprimer un évènement",
        operation_summary="Mises en avant évènement",
    ),
)
class EventHighlightingViewSet(
    CheckParentPermissionMixin,
    CreateModelMixin,
    ListModelMixin,
    DestroyModelMixin,
    BaseModelMixin,
    GenericViewSet,
):
    object_class = EventHighlighting
    serializer_class = EventHighlightingSerializer

    parent_queryset = Organization.objects.all()
    parent_lookup_field = "pk"
    parent_lookup_url_kwarg = "organization_pk"

    filter_backends = [OrderingFilter]

    ordering_fields = [
        "timestamp"
    ]

    permission_classes_by_action = {
        "create": [
            IsAuthenticated,
            OR(
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor(
                        "Admin-Operation-Event-Highlighting-Create"
                    ),
                ),
                (OrganizationHaveActiveSubscription & IsOrganizationEventManager)(),
            ),
        ],
        "list": [
            IsAuthenticated,
            OR(
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-Event-Highlighting-List"),
                ),
                (OrganizationHaveActiveSubscription & IsOrganizationMember)(),
            ),
        ],
        "destroy": [
            IsAuthenticated,
            OR(
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor(
                        "Admin-Operation-Event-Highlighting-Destroy"
                    ),
                ),
                (
                        OrganizationHaveActiveSubscription
                        & OrganizationIsObjectCreator
                        & (IsOrganizationOwner | IsOrganizationEventManager)
                )(),
            ),
        ],
    }

    def get_queryset(self):
        return self.object_class.objects.filter(
            event__organization__pk=self.parent_obj.pk
        )

    def perform_destroy(self, instance):
        instance.hard_delete()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        from_admin = getattr(request, "from_admin", False)

        resolve_transaction = (
                request.query_params.get("resolve_transaction", "") == "true"
        )

        serializer = self.get_serializer_class()(
            data=request.data,
            context={
                "request": request,
                "auto_resolve_transaction": from_admin and resolve_transaction,
            },
        )
        serializer.is_valid(raise_exception=True)

        event = serializer.validated_data.get("event")
        event_highlighting = self.get_queryset().filter(event__pk=event.pk).first()

        if event_highlighting and event_highlighting.active_status:
            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.PROMOTION_ALREADY_EXISTS),
                code=ErrorEnum.PROMOTION_ALREADY_EXISTS.value,
            )
        elif event_highlighting:
            Transaction.objects.get(entity_id=event_highlighting.pk).delete()
            event_highlighting.hard_delete()

        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_destroy(self, instance):
        instance.hard_delete()
