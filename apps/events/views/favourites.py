# -*- coding: utf-8 -*-
"""
Created on 25/07/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.events.models import Event, EventType, FavouriteEvent, FavouriteEventType
from apps.events.paginator import EventPagination, EventTypePagination
from apps.events.serializers import (
    EventSerializer,
    EventTypeSerializer,
    FavouriteEventSerializer,
    FavouriteEventTypeSerializer,
)
from apps.xlib.custom_decorators import custom_paginated_response
from apps.xlib.error_util import ErrorUtil, ErrorEnum

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class FavouriteEventView(GenericAPIView, CreateModelMixin, DestroyModelMixin):
    object_class = FavouriteEvent
    permission_classes = [
        IsAuthenticated,
    ]
    serializer_class = FavouriteEventSerializer
    pagination_class = EventPagination

    @custom_paginated_response(
        name="CustomFavouriteEventListPaginatedResponseSerializer",
        code=200,
        serializer_class=EventSerializer
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        user_favourite_events = list(
            self.request.user.favourite_events.order_by("-timestamp").values_list(
                "event", flat=True
            )
        )
        return Event.objects.filter(pk__in=user_favourite_events)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            kwargs.setdefault("context", self.get_serializer_context())
            serializer = EventSerializer(page, many=True, **kwargs)
            return self.get_paginated_response(serializer.data)
        else:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.MISSING_PAGE_NUMBER),
                code=ErrorEnum.MISSING_PAGE_NUMBER.value,
            )

    def post(self, request, *args, **kwargs):
        data = request.data | {"user": request.user.pk}
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        data = request.data | {"user": request.user.pk}
        serializer = self.get_serializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as exc:
            logger.exception(exc.__str__())
            if exc.get_codes().get("non_field_errors", [None])[0] == "unique":
                user_pk = serializer.data.get("user")
                event_pk = serializer.data.get("event")
                instance = self.object_class.objects.get(
                    user__pk=user_pk, event__pk=event_pk
                )
                self.perform_destroy(instance)
            else:
                raise NotFound({"message": "Aucun objet favoris associé."})
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.hard_delete()


class FavouriteEventTypeView(GenericAPIView, CreateModelMixin, DestroyModelMixin):
    object_class = FavouriteEventType
    permission_classes = [
        IsAuthenticated,
    ]
    serializer_class = FavouriteEventTypeSerializer
    pagination_class = EventTypePagination

    def get_queryset(self):
        user_favourite_event_types = list(
            self.request.user.favourite_event_types.order_by("-timestamp").values_list(
                "event_type", flat=True
            )
        )
        return EventType.objects.filter(pk__in=user_favourite_event_types)

    @custom_paginated_response(
        name="CustomEventTypeListPaginatedResponseSerializer",
        description="Get current user ' s paginated favorite event types list",
        code=200,
        serializer_class=EventTypeSerializer
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = EventTypeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        else:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.MISSING_PAGE_NUMBER),
                code=ErrorEnum.MISSING_PAGE_NUMBER.value,
            )

    def create(self, request, *args, **kwargs):
        data = request.data | {"user": request.user.pk}
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def destroy(self, request, *args, **kwargs):
        data = request.data | {"user": request.user.pk}
        serializer = self.get_serializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as exc:
            logger.exception(exc.__str__())
            if exc.get_codes().get("non_field_errors", [None])[0] == "unique":
                user_pk = serializer.data.get("user")
                event_type_pk = serializer.data.get("event_type")
                instance = self.object_class.objects.get(
                    user__pk=user_pk, event_type__pk=event_type_pk
                )
                self.perform_destroy(instance)
            else:
                raise NotFound({"message": "Aucun objet favoris associé."})
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.hard_delete()
