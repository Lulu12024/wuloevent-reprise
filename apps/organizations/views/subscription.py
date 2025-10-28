# -*- coding: utf-8 -*-
import logging

from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import (
    NotFound,
)
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated, IsAdminUser, OR
from rest_framework.response import Response

from apps.organizations.filters import SubscriptionFilter
from apps.organizations.mixings import CheckParentPermissionMixin
from apps.organizations.models import (
    Organization,
    Subscription,
)
from apps.organizations.permissions import (
    IsOrganizationOwner,
    IsOrganizationMember,
)
from apps.organizations.serializers import (
    SubscriptionSerializer,
    SubscriptionCreationSerializer,
)
from apps.users.permissions import HasAppAdminPermissionFor
from apps.utils.utils.baseviews import BaseModelsViewSet
from apps.xlib.enums import ErrorEnum
from apps.xlib.error_util import ErrorUtil

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


# Todo: Cache List
class OrganizationSubscriptionViewSet(CheckParentPermissionMixin, BaseModelsViewSet):
    object_class = Subscription
    serializer_default_class = SubscriptionSerializer

    parent_queryset = Organization.objects.all()
    parent_lookup_field = "pk"
    parent_lookup_url_kwarg = "organization_pk"

    filter_backends = [OrderingFilter]

    ordering_fields = [
        "timestamp"
    ]

    permission_classes_by_action = {
        "create": [IsAuthenticated, IsOrganizationOwner],
        "retrieve": [IsAuthenticated, IsOrganizationOwner],
        "list": [IsAuthenticated, IsOrganizationOwner],
        "destroy": [IsAuthenticated, IsOrganizationOwner],
        "get_active_subscription": [IsAuthenticated, IsOrganizationMember],
    }

    serializer_classes_by_action = {
        "create": SubscriptionCreationSerializer,
        "retrieve": SubscriptionSerializer,
        "list": SubscriptionSerializer,
        "destroy": SubscriptionSerializer,
    }

    def get_queryset(self):
        return self.object_class.objects.filter(organization=self.parent_obj)

    def perform_create(self, serializer):
        instance = serializer.save()
        return instance

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data
        data["organization"] = request.organization.pk

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @action(methods=["GET"], detail=False, url_path="active-subscription")
    def get_active_subscription(self, request, *args, **kwargs):
        now = timezone.now()
        organization = request.organization

        """
        active_subscriptions = [
            subscription
            for subscription in organization.subscriptions.all().order_by("-date")
            if subscription.active
        ]
        active_subscription = active_subscriptions[0]
        """

        if active_subscription := Subscription.objects \
                .prefetch_related("subscription_type") \
                .filter(start_date__lte=now, end_date__gte=now, active_status=True, organization_id=organization.pk) \
                .first():
            serialized_active_subscription = self.get_serializer(active_subscription)
            return Response(serialized_active_subscription.data, status=status.HTTP_200_OK)

        raise NotFound(
            ErrorUtil.get_error_detail(
                ErrorEnum.NO_ACTIVE_SUBSCRIPTION
            ),
            code=ErrorEnum.NO_ACTIVE_SUBSCRIPTION.value,
        )


@extend_schema_view(
    list=extend_schema(
        description="Endpoint to get subscriptions list",
        parameters=[
            OpenApiParameter(
                "organization_pk",
                OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=False,
                description="The id of an organization to filter the subscriptions against ",
            ),
            OpenApiParameter(
                "subscription_type_pk",
                OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=False,
                description="The id of a subscription type to filter the subscriptions against ",
            ),
            OpenApiParameter(
                "active_status",
                OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter by the the active status of the subscriptions ",
            ),
        ],
    )
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Subscription-Create",
        operation_description="Créer un abonnement",
        operation_summary="Abonnements",
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Subscription-Retrieve",
        operation_description="Récupérer les détails d' un abonnement",
        operation_summary="Abonnements",
    ),
)
@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Subscription-List",
        operation_description="Lister les abonnements",
        operation_summary="Abonnements",
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Subscription-Update",
        operation_description="Mettre à jour un abonnement",
        operation_summary="Abonnements",
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Subscription-Destroy",
        operation_description="Supprimer un abonnement",
        operation_summary="Abonnements",
    ),
)
@extend_schema_view(
    create=extend_schema(
        description="Endpoint for creating subscription by admin",
        parameters=[
            OpenApiParameter(
                "resolve_transaction",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Design if the transaction related to order should be resolve automatically ",
            )
        ],
        responses=SubscriptionSerializer(),
    )
)
class SubscriptionViewSet(BaseModelsViewSet):
    object_class = Subscription
    serializer_default_class = SubscriptionSerializer

    filter_backends = [OrderingFilter, DjangoFilterBackend]
    filterset_class = SubscriptionFilter

    ordering_fields = [
        "timestamp"
    ]

    http_method_names = ["post", "get", "put", "delete"]

    permission_classes_by_action = {
        "create": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Subscription-Create"),
            ),
        ],
        "retrieve": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Subscription-Retrieve"),
            ),
        ],
        "list": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Subscription-List"),
            ),
        ],
        "update": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Subscription-Update"),
            ),
        ],
        "destroy": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Subscription-Destroy"),
            ),
        ],
    }

    serializer_classes_by_action = {
        "create": SubscriptionCreationSerializer,
        "retrieve": SubscriptionSerializer,
        "list": SubscriptionSerializer,
        "destroy": SubscriptionSerializer,
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        from_admin = True
        resolve_transaction = (
                request.query_params.get("resolve_transaction", "") == "true"
        )
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data=request.data,
            context={
                "request": request,
                "auto_resolve_transaction": from_admin and resolve_transaction,
            },
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super(SubscriptionViewSet, self).update(request, *args, **kwargs)
