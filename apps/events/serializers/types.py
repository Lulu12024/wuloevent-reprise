# -*- coding: utf-8 -*-
"""
Created on 08/06/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.events.models import (
    EventType,
)

User = get_user_model()

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class EventTypeSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=EventType.objects.filter(active=True), required=False, allow_null=True, allow_empty=True,
    )

    class Meta:
        model = EventType
        fields = (
            "pk",
            "name",
            "description",
            "parent",
            "active",
        )
        read_only_fields = ("active",)

    def validate_organization(self, value):
        return self.context["request"].organization
