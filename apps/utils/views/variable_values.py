# -*- coding: utf-8 -*-
"""
Created on July 27 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
from django.utils.decorators import method_decorator
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import DestroyModelMixin, UpdateModelMixin, CreateModelMixin
from rest_framework.permissions import IsAdminUser, OR
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from apps.users.permissions import HasAppAdminPermissionFor
from apps.utils.models import VariableValue
from apps.utils.serializers import VariableValueSerializer
from apps.utils.utils.baseviews import BaseGenericViewSet


# Todo: Cache List by variable
@method_decorator(name='create', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Variable-Value-Create",
    operation_description="Créer une valeur pour une variable",
    operation_summary="Valeurs des variables"
))
@method_decorator(name='list_by_variable', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Variable-Value-List-By-Variable",
    operation_description="Lister les valeurs d' une variable",
    operation_summary="Valeurs des variables"
))
@method_decorator(name='update', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Variable-Value-Update",
    operation_description="Mettre à jour une valeur d' une variable",
    operation_summary="Valeurs des variables"
))
@method_decorator(name='destroy', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Variable-Value-Destroy",
    operation_description="Supprimer une valeur d' une variable",
    operation_summary="Valeurs des variables"
))
class VariableValueViewSet(CreateModelMixin, UpdateModelMixin, DestroyModelMixin, BaseGenericViewSet):
    object_class = VariableValue
    serializer_default_class = VariableValueSerializer

    http_method_names = ["post", "get", "put", "delete"]

    permission_classes_by_action = {
        "create": [
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Variable-Value-Create")
            )
        ],
        "list_by_variable": [
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Variable-Value-List-By-Variable")
            )
        ],
        "update": [
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Variable-Value-Update")
            )
        ],
        "destroy": [
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Variable-Value-Destroy")
            )
        ],
    }

    def get_queryset(self):
        return self.object_class.objects.filter(active=True)

    @extend_schema(
        description="Endpoint to get values list related to a variable",
        parameters=[
            OpenApiParameter('variable', OpenApiTypes.NUMBER, location=OpenApiParameter.QUERY,
                             description="The primary key of the variable's values you want to get."),
        ],
    )
    @action(methods=["GET"], detail=False, url_path='by-variable')
    def list_by_variable(self, request, *args, **kwargs):
        variable_pk = request.query_params.get('variable', None)
        if variable_pk is None:
            raise ValidationError(
                {'message': 'Veuillez entrer la clé primaire de la variable.'})

        queryset = self.object_class.objects.filter(variable_id=variable_pk)
        queryset = self.filter_queryset(queryset)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super(VariableValueViewSet, self).update(request, *args, **kwargs)
