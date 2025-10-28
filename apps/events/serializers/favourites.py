# -*- coding: utf-8 -*-
"""
Created on June 05, 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import APIException

from apps.events.models import (
    EventType,
    Event,
    FavouriteEvent,
    FavouriteEventType,
)
from apps.xlib.error_util import ErrorUtil, ErrorEnum

User = get_user_model()

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class FavouriteEventTypeSerializer(serializers.ModelSerializer):
    event_type = serializers.PrimaryKeyRelatedField(
        queryset=EventType.objects.filter(active=True)
    )
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True)
    )

    class Meta:
        model = FavouriteEventType
        fields = ("event_type", "user")


class FavouriteEventSerializer(serializers.ModelSerializer):
    event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all())
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True)
    )

    class Meta:
        model = FavouriteEvent
        fields = ("event", "user", "receive_news_by_email")

    def validate_event(self, event):
        if not event.have_passed_validation:
            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.EVENT_UNDERGOING_VALIDATION),
                code=ErrorEnum.EVENT_UNDERGOING_VALIDATION.value,
            )
        if not event.valid:
            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.INVALID_EVENT_DATA),
                code=ErrorEnum.INVALID_EVENT_DATA.value,
            )
        return event
