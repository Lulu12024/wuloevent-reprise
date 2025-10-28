# -*- coding: utf-8 -*-
"""
Created on 25/07/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, OR
from rest_framework.response import Response

from apps.events.models import EventImage
from apps.events.parsers import MultiPartFormParser
from apps.events.permissions import OrganizationIsObjectCreator
from apps.events.serializers import EventImageSerializer
from apps.events.views.utils import WriteOnlyNestedModelViewSet, ReadOnlyModelViewSet
from apps.organizations.models import Organization
from apps.organizations.permissions import IsOrganizationEventManager, OrganizationHaveActiveSubscription, \
    IsOrganizationOwner
from apps.users.permissions import HasAppAdminPermissionFor

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


@method_decorator(name='create', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Event-Image-Create",
    operation_description="Créer une image pour un évènement évènement",
    operation_summary="Images d' évènement"
))
@method_decorator(name='update', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Event-Image-Update",
    operation_description="Mettre à jour l' image d' un évènement",
    operation_summary="Images d' évènement"
))
@method_decorator(name='destroy', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Event-Image-Destroy",
    operation_description="Supprimer un image d' un évènement",
    operation_summary="Images d' évènement"
))
class WriteOnlyEventImageViewSet(WriteOnlyNestedModelViewSet):
    object_class = EventImage
    serializer_default_class = EventImageSerializer
    parser_classes = (MultiPartFormParser, FormParser, JSONParser)

    parent_queryset = Organization.objects.all()
    parent_lookup_field = 'pk'
    parent_lookup_url_kwarg = 'organization_pk'

    permission_classes_by_action = {
        'create': [
            IsAuthenticated,
            OR(
                (
                        OrganizationHaveActiveSubscription &
                        IsOrganizationEventManager
                )(),
                OR(IsAdminUser(), HasAppAdminPermissionFor("Admin-Operation-Event-Image-Create"))
            )
        ],
        'update': [
            IsAuthenticated,
            OR(
                (
                        OrganizationHaveActiveSubscription &
                        IsOrganizationEventManager &
                        OrganizationIsObjectCreator
                )(),
                OR(IsAdminUser(), HasAppAdminPermissionFor("Admin-Operation-Event-Image-Update"))
            )
        ],
        'destroy': [
            IsAuthenticated,
            OR(
                (
                        OrganizationHaveActiveSubscription & OrganizationIsObjectCreator &
                        (IsOrganizationOwner | IsOrganizationEventManager)
                )(),
                OR(IsAdminUser(), HasAppAdminPermissionFor("Admin-Operation-Event-Image-Destroy"))
            )
        ],
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    @extend_schema(
        responses={200: EventImageSerializer(many=True)},
    )
    @action(methods=["GET"], detail=False, url_path='by-event')
    def get_event_image_by_event(self, request, *args, **kwargs):
        event_pk = request.GET.get('event_pk', None)
        if event_pk is None:
            raise ValidationError(
                {'message': 'Veuillez entrer la clé primaire de l\'évenement.'})

        queryset = self.object_class.objects.filter(event__pk=event_pk)
        queryset = self.filter_queryset(queryset)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Event-Image-List",
    operation_description="Récupérer la liste de toute les images des évènements",
    operation_summary="Images d' évènement"
))
class ReadOnlyEventImageViewSet(ReadOnlyModelViewSet):
    object_class = EventImage
    serializer_default_class = EventImageSerializer

    permission_classes_by_action = {
        'retrieve': [AllowAny],
        'list': [IsAuthenticated, OR(IsAdminUser(), HasAppAdminPermissionFor("Admin-Operation-Event-Image-List"))],
        'get_event_image_by_event': [AllowAny, ],
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    @extend_schema(
        responses={200: EventImageSerializer(many=True)},
    )
    @action(methods=["GET"], detail=False, url_path='by-event')
    def get_event_image_by_event(self, request, *args, **kwargs):
        event_pk = request.GET.get('event_pk', None)
        if event_pk is None:
            raise ValidationError(
                {'message': 'Veuillez entrer la clé primaire de l\' évènement.'})

        queryset = self.object_class.objects.filter(event__pk=event_pk)
        queryset = self.filter_queryset(queryset)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
