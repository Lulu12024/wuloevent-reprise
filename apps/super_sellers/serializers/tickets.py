# -*- coding: utf-8 -*-
"""
Created on November 06, 2025

@author:
    Implementation Ticket-010
    
Serializer pour accès public aux tickets via ID unique.
"""

import logging
from rest_framework import serializers
from apps.events.models import ETicket, Event, Order
from apps.events.serializers.tickets import LightTicketSerializer
from apps.events.models.ticket_delivery import TicketDelivery
logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class PublicETicketSerializer(serializers.ModelSerializer):
    """
    Serializer pour accès public à un ticket via son ID unique.
    Utilisé pour l'endpoint GET /api/tickets/:uniqueId
    """
    
    ticket = LightTicketSerializer(read_only=True)
    event_name = serializers.CharField(source="event.name", read_only=True)
    event_date = serializers.DateField(source="event.date", read_only=True)
    event_hour = serializers.TimeField(source="event.hour", read_only=True)
    event_location = serializers.CharField(source="event.location_name", read_only=True)
    event_cover = serializers.ImageField(source="event.cover_image", read_only=True)
    order_id = serializers.CharField(source="related_order.order_id", read_only=True)
    
    # URL pour télécharger le ticket en PDF
    download_url = serializers.SerializerMethodField()
    
    # URL de deep linking pour l'application mobile
    app_deep_link = serializers.SerializerMethodField()
    
    class Meta:
        model = ETicket
        fields = (
            "pk",
            "name",
            "qr_code_data",
            "expiration_date",
            "is_downloaded",
            "ticket",
            "event_name",
            "event_date",
            "event_hour",
            "event_location",
            "event_cover",
            "order_id",
            "download_url",
            "app_deep_link",
        )
        read_only_fields = fields
    
    def get_download_url(self, obj):
        """
        Génère l'URL pour télécharger le ticket en PDF.
        """
        request = self.context.get('request')
        if request:
            # URL pour télécharger le PDF
            return request.build_absolute_uri(
                f"/v1/api/tickets/{obj.pk}/download/"
            )
        return None
    
    def get_app_deep_link(self, obj):
        """
        Génère le lien de deep linking pour ouvrir dans l'app mobile.
        Format: wuloevents://ticket/{ticket_id}
        """
        return f"wuloevents://ticket/{obj.pk}"


class TicketDeliverySerializer(serializers.ModelSerializer):
    """
    Serializer pour les informations d'envoi de tickets.
    """
    
    
    eticket_name = serializers.CharField(source="eticket.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)
    
    class Meta:
        model = TicketDelivery
        fields = (
            "pk",
            "eticket_name",
            "channel",
            "channel_display",
            "status",
            "status_display",
            "retry_count",
            "max_retry_count",
            "sent_at",
            "failed_at",
            "error_message",
            "next_retry_at",
            "timestamp",
        )
        read_only_fields = fields


class TicketDeliveryDetailSerializer(serializers.ModelSerializer):
    """
    Serializer détaillé pour les envois de tickets (avec logs).
    """
    
    
    eticket = PublicETicketSerializer(read_only=True)
    
    class Meta:
        model = TicketDelivery
        fields = (
            "pk",
            "eticket",
            "recipient_email",
            "recipient_phone",
            "recipient_name",
            "channel",
            "status",
            "retry_count",
            "max_retry_count",
            "next_retry_at",
            "sent_at",
            "failed_at",
            "error_message",
            "delivery_logs",
            "provider_response",
            "timestamp",
            "updated",
        )
        read_only_fields = fields