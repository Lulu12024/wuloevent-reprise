# -*- coding: utf-8 -*-
"""
Created on June 05, 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.events.models import (
    ETicket,
    Event,
)
from apps.events.serializers.tickets import LightTicketSerializer

User = get_user_model()

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class ETicketSerializer(serializers.ModelSerializer):
    event = serializers.PrimaryKeyRelatedField(
        queryset=Event.objects.filter(active=True, valid=True)
    )
    ticket = LightTicketSerializer()

    class Meta:
        model = ETicket
        fields = (
            "pk",
            "event",
            "name",
            "related_order_id",
            "expiration_date",
            "is_downloaded",
            "qr_code_data",
            "active",
            "ticket",
        )

        extra_kwargs = {
            "name": {"read_only": True},
            "event": {"read_only": True},
            "expiration_date": {"read_only": True},
            "related_order_id": {"read_only": True},
            "is_downloaded": {"read_only": True},
            "qr_code_data": {"read_only": True},
            "ticket": {"read_only": True},
        }


class ScanETicketSerializer(serializers.Serializer):
    id64 = serializers.CharField(required=True)
    secret_phrase = serializers.CharField(required=True)
