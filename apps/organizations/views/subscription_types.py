# -*- coding: utf-8 -*-
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework.mixins import (
    ListModelMixin,
    DestroyModelMixin,
    UpdateModelMixin,
    CreateModelMixin,
)
from rest_framework.permissions import IsAuthenticated, IsAdminUser, OR

from apps.organizations.models import (
    SubscriptionType,
)
from apps.organizations.serializers import SubscriptionTypeSerializer
from apps.users.permissions import HasAppAdminPermissionFor
from apps.utils.utils.baseviews import BaseGenericViewSet


# Todo: Cache List
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Subscription-Type-Create",
        operation_description="Créer un type d' abonnement",
        operation_summary="Types d' abonnement",
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Subscription-Type-Update",
        operation_description="Mettre à jour un type d' abonnement",
        operation_summary="Types d' abonnement",
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Subscription-Type-Destroy",
        operation_description="Supprimer un type d' abonnement",
        operation_summary="Types d' abonnements",
    ),
)
class SubscriptionTypeViewSet(
    CreateModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    BaseGenericViewSet,
):
    object_class = SubscriptionType
    serializer_default_class = SubscriptionTypeSerializer

    http_method_names = ["post", "get", "patch", "delete", "put"]

    permission_classes_by_action = {
        "create": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Subscription-Type-Create"),
            ),
        ],
        "list": [IsAuthenticated],
        "update": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Subscription-Type-Update"),
            ),
        ],
        "destroy": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Subscription-Type-Destroy"),
            ),
        ],
    }

    def get_queryset(self):
        return self.object_class.objects.all()
