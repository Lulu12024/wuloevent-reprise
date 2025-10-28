# -*- coding: utf-8 -*-
"""
Created on 25/07/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.db import transaction
from django.utils.decorators import method_decorator
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, OR
from rest_framework.response import Response

from apps.events.models import Order
from apps.events.permissions import IsOrderCreator
from apps.events.serializers import OrderSerializer, OrderDetailSerializer
from apps.users.models import User
from apps.users.permissions import HasAppAdminPermissionFor
from apps.utils.paginator import Pagination
from apps.utils.utils.baseviews import BaseModelsViewSet
from apps.xlib.custom_decorators import custom_paginated_response
from apps.xlib.enums import OrderStatusEnum
from apps.xlib.error_util import ErrorUtil, ErrorEnum

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


@method_decorator(name='create', decorator=transaction.atomic)
@method_decorator(name='admin_create', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Order-Create",
    operation_description="Créer une commande.",
    operation_summary="Commandes"
))
@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Order-List",
    operation_description="Récupérer la liste des commandes.",
    operation_summary="Commandes"
))
@method_decorator(name='list_by_user', decorator=custom_paginated_response(
    name="CustomOrderListByUserPaginatedResponseSerializer",
    description="Retrieve Order List",
    code=200,
    serializer_class=OrderSerializer,
))
@method_decorator(name='start', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Order-Start",
    operation_description="Démarrer le traitement d' une commande",
    operation_summary="Commandes"
))
@method_decorator(name='destroy', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Order-Destroy",
    operation_description="Supprimer une commande",
    operation_summary="Commandes"
))
@extend_schema_view(
    retrieve=extend_schema(
        description="Endpoint to retrieve order details",
        responses=OrderDetailSerializer(),
    )
)
@extend_schema_view(
    admin_create=extend_schema(
        description="Endpoint for admin to create order",
        parameters=[
            OpenApiParameter(
                "resolve_transaction",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Design if the transaction related to order should be resolve automatically ",
            )
        ],
        responses=OrderSerializer(),
    )
)
@extend_schema_view(
    pseudo_anonymous=extend_schema(
        description="Endpoint to create pseudo-anonymous order using email as identifier",
        parameters=[],
        responses=OrderSerializer(),
    )
)
class OrderViewSet(BaseModelsViewSet):
    object_class = Order
    serializer_default_class = OrderSerializer
    filter_backends = [filters.OrderingFilter]

    pagination_class = Pagination

    ordering_fields = [
        "name",
        "order_id",
        "timestamp"
    ]

    permission_classes_by_action = {
        "create": [AllowAny],
        "update": [AllowAny],
        "retrieve": [AllowAny],
        "list": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Order-List")
            )
        ],
        "admin_create": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Order-Create")
            )
        ],
        "list_by_user": [IsAuthenticated],
        "pseudo_anonymous": [AllowAny],
        "start": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Order-Start")
            )
        ],
        "destroy": [
            IsAuthenticated,
            OR(
                IsOrderCreator(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-Order-Destroy")
                )
            )
        ],
    }

    serializer_classes_by_action = {
        "retrieve": OrderDetailSerializer
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    @transaction.atomic
    @action(methods=["POST"], detail=False, url_path="admin-create")
    def admin_create(self, request, *args, **kwargs):
        from_admin = True
        resolve_transaction = request.query_params.get("resolve_transaction", "") == "true"

        serializer = self.get_serializer_class()(
            data=request.data,
            context={"request": request, "auto_resolve_transaction": from_admin and resolve_transaction}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @extend_schema(
        description="Get an order the current user orders list",
        responses={
            200: OrderSerializer(many=True)
        }
    )
    @action(methods=["GET"], detail=False, url_path="by-me")
    def list_by_user(self, request, *args, **kwargs):
        user = request.user
        queryset = self.get_queryset().filter(user=user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=True, url_path="start")
    def start(self, request, *args, **kwargs):
        instance = self.get_object()
        event = instance.item.ticket.event
        item = instance.item
        if not event:
            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.EVENT_NOT_FOUND),
                code=ErrorEnum.EVENT_NOT_FOUND.value,
            )
        if (
            event.private
            and (event.participant_limit <= (event.participant_count + item.quantity))
        ):
            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.EVENT_PARTICIPANT_LIMIT_REACHED),
                code=ErrorEnum.EVENT_PARTICIPANT_LIMIT_REACHED.value,
            )
        if not instance.valid:
            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.ORDER_NOT_YET_PAID),
                code=ErrorEnum.ORDER_NOT_YET_PAID.value,
            )
        instance.status = OrderStatusEnum.STARTED
        instance.save()
        queryset = self.object_class.objects.get(pk=instance.pk)
        serializer = self.serializer_default_class(queryset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @transaction.atomic
    @action(methods=["POST"], detail=False, url_path="pseudo-anonymous")
    def pseudo_anonymous(self, request, *args, **kwargs):
        email = request.data.get("email", None)

        if not email:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.EMAIL_REQUIRED),
                code=ErrorEnum.EMAIL_REQUIRED.value,
            )

        user = User.objects.get_or_create_anonymous_user(email)

        serializer = self.get_serializer_class()(
            data=request.data,
            context={"user": user, "request": request, "is_pseudo_anonymous_request": True}
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )
