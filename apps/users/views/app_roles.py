# -*- coding: utf-8 -*-
import logging

from django.db import transaction
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated, IsAdminUser, OR

from apps.users.models import AppRole
from apps.users.permissions import HasAppAdminPermissionFor
from apps.users.serializers.app_roles import AppRoleSerializer
from apps.utils.utils.baseviews import BaseModelsViewSet

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


@method_decorator(
    name="create",
    decorator=transaction.atomic,
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-AppRole-Create",
        operation_description="Créer un rôle dans l' application",
        operation_summary="Rôles dans l' application",
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-AppRole-Retrieve",
        operation_description="Récupérer les détails d' un rôle dans l' application",
        operation_summary="Rôles dans l' application",
    ),
)
@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-AppRole-List",
        operation_description="Lister les rôles dans l' application",
        operation_summary="Rôles dans l' application",
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-AppRole-Update",
        operation_description="Mettre à jour un rôle dans l' application",
        operation_summary="Rôles dans l' application",
    ),
)
class AppRoleViewSet(BaseModelsViewSet):
    object_class = AppRole
    serializer_default_class = AppRoleSerializer

    filter_backends = [OrderingFilter]

    ordering_fields = [
        "timestamp"
    ]

    http_method_names = ["post", "get", "put"]

    permission_classes_by_action = {
        "create": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-AppRole-Create"),
            ),
        ],
        "retrieve": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-AppRole-Retrieve"),
            ),
        ],
        "list": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-AppRole-List"),
            ),
        ],
        "update": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-AppRole-Update"),
            ),
        ]
    }

    def get_queryset(self):
        return self.object_class.objects.prefetch_related("permissions").all()

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super(AppRoleViewSet, self).update(request, *args, **kwargs)


__all__ = ["AppRoleViewSet"]
