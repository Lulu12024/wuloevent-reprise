# -*- coding: utf-8 -*-
"""
Created on 25/07/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.utils.decorators import method_decorator
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import extend_schema, extend_schema_view
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, APIException
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, OR
from rest_framework.response import Response

from apps.events.models import Ticket, TicketCategory, TicketCategoryFeature
from apps.events.permissions import OrganizationIsObjectCreator
from apps.events.serializers import (
    AddFeaturesToTicketCategorySerializer,
    TicketCategoryFeatureSerializer,
    TicketCategorySerializer,
    TicketSerializer,
)
from apps.events.views.utils import WriteOnlyNestedModelViewSet, ReadOnlyModelViewSet
from apps.organizations.models import Organization
from apps.organizations.permissions import (
    IsOrganizationEventManager,
    OrganizationHaveActiveSubscription,
    IsOrganizationOwner,
)
from apps.users.permissions import HasAppAdminPermissionFor

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


# Create your viewsets here


@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Ticket-Category-Create",
        operation_description="Créer une catégorie de ticket",
        operation_summary="Catégories de Ticket",
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Ticket-Category-Update",
        operation_description="Mettre à jour une catégorie de ticket",
        operation_summary="Catégories de Ticket",
    ),
)
@method_decorator(
    name="add_features",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Ticket-Category-Add-Features",
        operation_description="Ajouter une features à une catégorie de ticket",
        operation_summary="Catégories de Ticket",
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Ticket-Category-Destroy",
        operation_description="Supprimer une catégorie de ticket",
        operation_summary="Catégories de Ticket",
    ),
)
class WriteOnlyTicketCategoryViewSet(WriteOnlyNestedModelViewSet):
    object_class = TicketCategory
    serializer_default_class = TicketCategorySerializer

    parent_queryset = Organization.objects.all()
    parent_lookup_field = "pk"
    parent_lookup_url_kwarg = "organization_pk"

    permission_classes_by_action = {
        "create": [
            IsAuthenticated,
            OR(
                (OrganizationHaveActiveSubscription & IsOrganizationEventManager)(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-Ticket-Category-Create"),
                ),
            ),
        ],
        "update": [
            IsAuthenticated,
            OR(
                (
                        OrganizationHaveActiveSubscription
                        & IsOrganizationEventManager
                        & OrganizationIsObjectCreator
                )(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-Ticket-Category-Update"),
                ),
            ),
        ],
        "add_features": [
            IsAuthenticated,
            OR(
                (
                        OrganizationHaveActiveSubscription
                        & IsOrganizationEventManager
                        & OrganizationIsObjectCreator
                )(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor(
                        "Admin-Operation-Ticket-Category-Add-Features"
                    ),
                ),
            ),
        ],
        "destroy": [
            IsAuthenticated,
            OR(
                (
                        OrganizationHaveActiveSubscription
                        & OrganizationIsObjectCreator
                        & (IsOrganizationOwner | IsOrganizationEventManager)
                )(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-Ticket-Category-Destroy"),
                ),
            ),
        ],
    }

    serializer_classes_by_action = {
        "add_features": AddFeaturesToTicketCategorySerializer,
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    @extend_schema(
        responses={200: TicketCategorySerializer()},
    )
    @action(methods=["POST"], detail=True, url_path="add-features")
    def add_features(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        instance = self.get_object()
        serializer = self.serializer_default_class(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Ticket-Category-List",
        operation_description="Récupérer la liste des catégories de ticket",
        operation_summary="Catégories de Ticket",
    ),
)
@extend_schema_view(
    list_by_event=extend_schema(
        description="Endpoint to get ticket list by event",
        parameters=[
            OpenApiParameter(
                "event_pk",
                OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Primary kek of the event",
            ),
        ],
        responses=TicketCategorySerializer(many=True),
    ),
)
class ReadOnlyTicketCategoryViewSet(ReadOnlyModelViewSet):
    object_class = TicketCategory
    serializer_default_class = TicketCategorySerializer

    permission_classes_by_action = {
        "list": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Ticket-Category-List"),
            ),
        ],
        "list_by_event": [AllowAny],
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    @extend_schema(
        responses={200: TicketCategorySerializer(many=True)},
    )
    @action(methods=["GET"], detail=False, url_path="by-event")
    def list_by_event(self, request, *args, **kwargs):
        event_pk = request.GET.get("event_pk", None)
        if event_pk is None:
            raise ValidationError(
                {"message": "Veuillez entrer la clé primaire de l' évènement."}
            )

        queryset = self.object_class.objects.filter(event__pk=event_pk)
        queryset = self.filter_queryset(queryset)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Ticket-Category-Feature-Create",
        operation_description="Créer une description pour une catégorie de ticket",
        operation_summary="Descriptions de catégorie de ticket",
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Ticket-Category-Feature-Update",
        operation_description="Mettre à jour une description d' une catégorie de ticket",
        operation_summary="Descriptions de catégorie de ticket",
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Ticket-Category-Feature-Destroy",
        operation_description="Supprimer une description d' une catégorie de ticket",
        operation_summary="Descriptions de catégorie de ticket",
    ),
)
class WriteOnlyTicketCategoryFeatureViewSet(WriteOnlyNestedModelViewSet):
    object_class = TicketCategoryFeature
    serializer_default_class = TicketCategoryFeatureSerializer

    parent_queryset = Organization.objects.all()
    parent_lookup_field = "pk"
    parent_lookup_url_kwarg = "organization_pk"

    permission_classes_by_action = {
        "create": [
            IsAuthenticated,
            OR(
                (OrganizationHaveActiveSubscription & IsOrganizationEventManager)(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor(
                        "Admin-Operation-Ticket-Category-Feature-Create"
                    ),
                ),
            ),
        ],
        "update": [
            IsAuthenticated,
            OR(
                (
                        OrganizationHaveActiveSubscription
                        & IsOrganizationEventManager
                        & OrganizationIsObjectCreator
                )(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor(
                        "Admin-Operation-Ticket-Category-Feature-Update"
                    ),
                ),
            ),
        ],
        "destroy": [
            IsAuthenticated,
            OR(
                (
                        OrganizationHaveActiveSubscription
                        & OrganizationIsObjectCreator
                        & (IsOrganizationOwner | IsOrganizationEventManager)
                )(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor(
                        "Admin-Operation-Ticket-Category-Feature-Destroy"
                    ),
                ),
            ),
        ],
    }

    def get_queryset(self):
        return self.object_class.objects.all()


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Ticket-Category-Feature-List",
        operation_description="Récupérer la liste des descriptions de catégories de ticket",
        operation_summary="Descriptions de catégorie de ticket",
    ),
)
class ReadOnlyTicketCategoryFeatureViewSet(ReadOnlyModelViewSet):
    object_class = TicketCategoryFeature
    serializer_default_class = TicketCategoryFeatureSerializer

    permission_classes_by_action = {
        "list": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor(
                    "Admin-Operation-Ticket-Category-Feature-List"
                ),
            ),
        ],
        "list_by_ticket_category": [AllowAny],
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    @action(methods=["GET"], detail=False, url_path="by-ticket-category")
    def list_by_ticket_category(self, request, *args, **kwargs):
        ticket_category_pk = request.GET.get("ticket_category_pk", None)
        if ticket_category_pk is None:
            raise ValidationError(
                {
                    "message": "Veuillez entrer la clé primaire du la catégories de ticket."
                }
            )

        try:
            ticket_category = TicketCategory.objects.get(pk=ticket_category_pk)
        except Exception as exc:
            logger.exception(exc.__str__())
            raise APIException("Clé primaire de la catégorie de ticket non valide")
        queryset = ticket_category.features.all()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Ticket-Create",
        operation_description="Créer un ticket.",
        operation_summary="Tickets",
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Ticket-Update",
        operation_description="Mettre à jour un ticket.",
        operation_summary="Tickets",
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Ticket-Destroy",
        operation_description="Supprimer un ticket.",
        operation_summary="Tickets",
    ),
)
class WriteOnlyTicketViewSet(WriteOnlyNestedModelViewSet):
    object_class = Ticket
    serializer_default_class = TicketSerializer

    parent_queryset = Organization.objects.all()
    parent_lookup_field = "pk"
    parent_lookup_url_kwarg = "organization_pk"

    permission_classes_by_action = {
        # "create": [
        #     IsAuthenticated,
        #     OR(
        #         (OrganizationHaveActiveSubscription & IsOrganizationEventManager)(),
        #         OR(
        #             IsAdminUser(),
        #             HasAppAdminPermissionFor("Admin-Operation-Ticket-Create"),
        #         ),
        #     ),
        # ],
        "update": [
            IsAuthenticated,
            OR(
                (
                        OrganizationHaveActiveSubscription
                        & IsOrganizationEventManager
                        & OrganizationIsObjectCreator
                )(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-Ticket-Update"),
                ),
            ),
        ],
        "destroy": [
            IsAuthenticated,
            OR(
                (
                        OrganizationHaveActiveSubscription
                        & OrganizationIsObjectCreator
                        & (IsOrganizationOwner | IsOrganizationEventManager)
                )(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-Ticket-Destroy"),
                ),
            ),
        ],
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Ticket-List",
        operation_description="Récupérer la liste des tickets",
        operation_summary="Tickets",
    ),
)
@extend_schema_view(
    list_by_event=extend_schema(
        description="Endpoint to get ticket list by event",
        parameters=[
            OpenApiParameter(
                "event_pk",
                OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Primary kek of the event",
            ),
        ],
        responses=TicketSerializer(many=True),
    ),
    list_by_ticket_category=extend_schema(
        description="Endpoint to get tickets list by ticket category list",
        parameters=[
            OpenApiParameter(
                "ticket_category_pk",
                OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Primary key of the ticket category",
            ),
        ],
        responses=TicketSerializer(many=True),
    ),
)
class ReadOnlyTicketViewSet(ReadOnlyModelViewSet):
    object_class = Ticket
    serializer_default_class = TicketSerializer

    filter_backends = [OrderingFilter]

    ordering_fields = [
        "name",
        "order_id",
        "timestamp"
    ]

    permission_classes_by_action = {
        "retrieve": [AllowAny],
        "list": [
            IsAuthenticated,
            OR(IsAdminUser(), HasAppAdminPermissionFor("Admin-Operation-Ticket-List")),
        ],
        "list_by_event": [AllowAny],
        "list_by_ticket_category": [AllowAny],
        "list_by_event": [AllowAny],
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    @extend_schema(
        responses={200: TicketSerializer(many=True)},
    )
    @action(methods=["GET"], detail=False, url_path="by-event")
    def list_by_event(self, request, *args, **kwargs):
        event_pk = request.GET.get("event_pk", None)
        if event_pk is None:
            raise ValidationError(
                {"message": "Veuillez entrer la clé primaire de l' évènement."}
            )

        queryset = self.object_class.objects.filter(event__pk=event_pk)
        queryset = self.filter_queryset(queryset)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=False, url_path="by-ticket-category")
    def list_by_ticket_category(self, request, *args, **kwargs):
        ticket_category_pk = request.GET.get("ticket_category_pk", None)
        if ticket_category_pk is None:
            raise ValidationError(
                {
                    "message": "Veuillez entrer la clé primaire du la catégories de ticket."
                }
            )

        try:
            ticket_category = TicketCategory.objects.get(pk=ticket_category_pk)
        except Exception as exc:
            logger.exception(exc.__str__())
            raise APIException("Clé primaire de la catégorie de ticket non valide")
        queryset = ticket_category.features.all()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
