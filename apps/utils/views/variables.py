# -*- coding: utf-8 -*-
"""
Created on July 27 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
from django.db.models import Prefetch
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAdminUser, OR
from rest_framework.response import Response

from apps.users.permissions import HasAppAdminPermissionFor
from apps.utils.models import Variable, VariableValue
from apps.utils.serializers import VariableSerializer
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiTypes,
)

# Todo: Cache : Invalidate where new var or update var


@extend_schema_view(
    get=extend_schema(
        description="Endpoint to get variables list",
        parameters=[
            OpenApiParameter(
                "active",
                OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Filter by if the variable is active",
            ),
        ],
        responses=VariableSerializer(many=True),
    )
)
class VariableListView(GenericAPIView):
    object_class = Variable
    permission_classes = [
        OR(IsAdminUser(), HasAppAdminPermissionFor("Admin-Operation-Variable-List"))
    ]
    serializer_class = VariableSerializer

    def get_permissions(self):
        def get_permission_function(instance):
            try:
                return instance()
            except TypeError:
                return instance

        return [
            get_permission_function(permission)
            for permission in self.permission_classes
        ]

    def get_queryset(self):
        return self.object_class.objects.all()

    @swagger_auto_schema(
        operation_id="Admin-Operation-Variable-List",
        operation_description="Lister les variables",
        operation_summary="Variables",
    )
    def get(self, request, *args, **kwargs):
        variables = Variable.objects.prefetch_related(
            Prefetch("possible_values", VariableValue.objects.all())
        )

        return Response(
            self.serializer_class(variables, many=True).data, status=status.HTTP_200_OK
        )
