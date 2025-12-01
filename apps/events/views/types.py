# -*- coding: utf-8 -*-
"""
Created on 25/07/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, OR

from apps.events.filters import EventTypeSearch
from apps.events.models import EventType
from apps.events.serializers import EventTypeSerializer
from apps.users.permissions import HasAppAdminPermissionFor
from apps.utils.utils.baseviews import BaseModelsViewSet

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


# Todo: Cache List
@method_decorator(name='create', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Event-Type-Create",
    operation_description="Créer un type d' évènement",
    operation_summary="Types d' évènement"
))
@method_decorator(name='update', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Event-Type-Update",
    operation_description="Mettre à jour un type évènement",
    operation_summary="Types d' évènement"
))
@method_decorator(name='destroy', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Event-Type-Destroy",
    operation_description="Supprimer un type d' évènement",
    operation_summary="Types d' évènement"
))
class EventTypeViewSet(BaseModelsViewSet):
    object_class = EventType
    serializer_default_class = EventTypeSerializer

    filter_backends = [EventTypeSearch]
    search_fields = ["name", "description"]

    http_method_names = ["post", "get", "put", "delete"]

    permission_classes_by_action = {
        # "create": [
        #     IsAuthenticated,
        #     OR(
        #         IsAdminUser(),
        #         HasAppAdminPermissionFor(
        #             "Admin-Operation-Event-Type-Create"
        #         ),
        #     ),
        # ],
        "retrieve": [AllowAny],
        "list": [AllowAny],
        "update": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor(
                    "Admin-Operation-Event-Type-Update"
                ),
            ),
        ],
        "destroy": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor(
                    "Admin-Operation-Event-Type-Destroy"
                ),
            ),
        ],
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    def update(self, request, *args, **kwargs):
        kwargs.update({"partial": True})
        return super().update(request, *args, **kwargs)
