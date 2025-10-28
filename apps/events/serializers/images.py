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
    Event,
    EventImage,
)
from apps.organizations.models import Organization

User = get_user_model()

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class EventImageSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.filter(active=True), required=False, default=None
    )
    event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all())

    class Meta:
        model = EventImage
        fields = (
            "pk",
            "organization",
            "event",
            "title",
            "image",
            "thumbnails",
            "active",
        )

        extra_kwargs = {"title": {"required": False}}

    def validate_organization(self, value):
        return self.context["request"].organization
