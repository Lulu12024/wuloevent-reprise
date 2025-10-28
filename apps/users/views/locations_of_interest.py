# -*- coding: utf-8 -*-

import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser, OR
from rest_framework.response import Response

from apps.users.models import (
    PointOfInterest,
    ZoneOfInterest,
)
from apps.users.permissions import IsCreator
from apps.users.serializers.locations_of_interest import (
    PointOfInterestSerializer,
    ZoneOfInterestSerializer,
)
from apps.utils.utils.baseviews import BaseModelsViewSet

User = get_user_model()

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class PointOfInterestViewSet(BaseModelsViewSet):
    object_class = PointOfInterest
    serializer_default_class = PointOfInterestSerializer

    permission_classes_by_action = {
        "create": [IsAuthenticated, IsAuthenticated],
        "retrieve": [IsAuthenticated, IsCreator],
        "list_by_user": [IsAuthenticated, IsAuthenticated],
        "list": [IsAuthenticated, IsAuthenticated, IsAdminUser],
        "destroy": [IsAuthenticated, OR(IsCreator(), IsAdminUser())],
    }

    serializer_classes_by_action = {
        "create": PointOfInterestSerializer,
        "retrieve": PointOfInterestSerializer,
        "list": PointOfInterestSerializer,
        "list_by_user": PointOfInterestSerializer,
        "destroy": PointOfInterestSerializer,
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    def create(self, request, *args, **kwargs):
        data = request.data | {"user": request.user.pk}
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @action(methods=["GET"], detail=False, url_path="by-me")
    def list_by_user(self, request, *args, **kwargs):
        user = request.user
        queryset = self.filter_queryset(self.get_queryset().filter(user=user))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ZoneOfInterestViewSet(BaseModelsViewSet):
    object_class = ZoneOfInterest
    serializer_default_class = ZoneOfInterestSerializer

    permission_classes_by_action = {
        "create": [IsAuthenticated],
        "retrieve": [IsCreator],
        "list_by_user": [IsAuthenticated],
        "list": [IsAuthenticated, IsAdminUser],
        "destroy": [OR(IsCreator(), IsAdminUser())],
    }

    serializer_classes_by_action = {
        "create": ZoneOfInterestSerializer,
        "retrieve": ZoneOfInterestSerializer,
        "list": ZoneOfInterestSerializer,
        "list_by_user": ZoneOfInterestSerializer,
        "destroy": ZoneOfInterestSerializer,
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    def create(self, request, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.data | {"user": str(request.user.pk)})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @action(methods=["GET"], detail=False, url_path="by-me")
    def list_by_user(self, request, *args, **kwargs):
        user = request.user
        queryset = self.filter_queryset(self.get_queryset().filter(user=user))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
