# -*- coding: utf-8 -*-
"""
Created on 25/07/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.filters import OrderingFilter
from rest_framework.mixins import DestroyModelMixin, RetrieveModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated, IsAdminUser, OR
from rest_framework.response import Response

from apps.events.models import ETicket
from apps.events.permissions import IsETicketCreator
from apps.events.serializers import ETicketSerializer
from apps.organizations.filters import ETicketFilter
from apps.users.permissions import HasAppAdminPermissionFor
from apps.utils.utils.baseviews import BaseGenericViewSet
from apps.xlib.error_util import ErrorUtil, ErrorEnum

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


@extend_schema_view(
    list=extend_schema(
        description="Endpoint to get e-tickets list",
        parameters=[
            OpenApiParameter(
                "event",
                OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=False,
                description="The id of an event to filter the e-tickets against ",
            ),
            OpenApiParameter(
                "ticket",
                OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=False,
                description="The id of a ticket to filter the e-tickets against ",
            ),
            OpenApiParameter(
                "user",
                OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=False,
                description="The id of an user to filter the e-tickets against ",
            ),
            OpenApiParameter(
                "order",
                OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=False,
                description="The id of a order to filter the e-ticket against ",
            ),
            OpenApiParameter(
                "is_downloaded",
                OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter by if the e-tickets was download or not ",
            ),
        ],
    )
)
@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-E-Tickets-List",
        operation_description="Récupérer la liste des E Tickets",
        operation_summary="E-Tickets",
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-E-Tickets-Destroy",
        operation_description="Supprimer un e-tickets",
        operation_summary="E-Tickets",
    ),
)
class ETicketViewSet(
    BaseGenericViewSet, RetrieveModelMixin, ListModelMixin, DestroyModelMixin
):
    object_class = ETicket
    serializer_default_class = ETicketSerializer

    filter_backends = [OrderingFilter, DjangoFilterBackend]
    filterset_class = ETicketFilter

    ordering_fields = [
        "timestamp"
    ]

    permission_classes_by_action = {
        "retrieve": [IsAuthenticated],
        "list": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-E-Tickets-List"),
            ),
        ],
        "list_by_user": [IsAuthenticated],
        "download": [IsAuthenticated],
        "destroy": [
            IsAuthenticated,
            OR(
                IsETicketCreator(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-E-Tickets-Destroy"),
                ),
            ),
        ],
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    @extend_schema(
        responses={
            200: ETicketSerializer(many=True),
        },
    )
    @action(methods=["GET"], detail=False, url_path="by-me")
    def list_by_user(self, request, *args, **kwargs):
        user = request.user
        queryset = self.get_queryset().filter(related_order__user__id=user.pk)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=True, url_path="download")
    def download(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_downloaded:
            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.TICKET_ALREADY_DOWNLOADED),
                code=ErrorEnum.TICKET_ALREADY_DOWNLOADED.value,
            )
        file_handle = instance.file.open()
        # send file
        response = Response(file_handle, content_type="application/png")
        response["Content-Length"] = instance.file.size
        response["Content-Disposition"] = (
                'attachment; filename="%s"' % instance.file.name
        )

        return response
