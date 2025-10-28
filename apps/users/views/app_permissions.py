# -*- coding: utf-8 -*-
"""
Created on 10/11/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework.filters import OrderingFilter
from rest_framework.mixins import UpdateModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated, IsAdminUser, OR
from rest_framework.viewsets import GenericViewSet

from apps.users.models import AppPermission
from apps.users.permissions import HasAppAdminPermissionFor
from apps.users.serializers.app_permissions import AppPermissionSerializer
from apps.utils.utils.baseviews import BaseModelMixin

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-AppPermission-List",
        operation_description="Lister les permissions dans l' application",
        operation_summary="Permissions dans l' application",
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-AppPermission-Update",
        operation_description="Mettre à jour une permission dans l' application",
        operation_summary="Permissions dans l' application",
    ),
)
class AppPermissionViewSet(BaseModelMixin, UpdateModelMixin, ListModelMixin, GenericViewSet):
    object_class = AppPermission
    serializer_default_class = AppPermissionSerializer

    filter_backends = [OrderingFilter]

    ordering_fields = [
        "timestamp"
    ]

    http_method_names = ["put", "get"]

    permission_classes_by_action = {

        "list": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-AppPermission-List"),
            ),
        ],
        "update": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-AppPermission-Update"),
            ),
        ],
    }

    serializer_classes_by_action = {
        "list": AppPermissionSerializer,
        "destroy": AppPermissionSerializer,
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super(AppPermissionViewSet, self).update(request, *args, **kwargs)


__all__ = ["AppPermissionViewSet"]
