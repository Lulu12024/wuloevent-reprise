# -*- coding: utf-8 -*-
"""
Created on November 06, 2025

@author:
    Implementation Ticket-010
    
Views pour accès public aux tickets et téléchargement PDF.
"""

import logging
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from apps.events.models import ETicket
from apps.events.models.ticket_delivery import TicketDelivery
from apps.super_sellers.serializers.tickets import (
    PublicETicketSerializer,
    TicketDeliverySerializer,
    TicketDeliveryDetailSerializer
)

logger = logging.getLogger(__name__)


class PublicTicketViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet en lecture seule pour accéder aux tickets via leur ID unique.
    
    Endpoints:
    - GET /api/tickets/{uuid}/          -> Détails du ticket
    - GET /api/tickets/{uuid}/download/ -> Télécharger le PDF du ticket
    - GET /api/tickets/{uuid}/verify/   -> Vérifier la validité du ticket
    
    Permissions: AllowAny (accès public avec UUID)
    """
    
    queryset = ETicket.objects.filter(active=True).select_related(
        "event", "ticket", "related_order"
    )
    serializer_class = PublicETicketSerializer
    permission_classes = [AllowAny]
    lookup_field = "pk"
    
    @extend_schema(
        summary="Détails d'un ticket",
        description="Récupère les détails d'un ticket via son ID unique.",
        tags=["Tickets"],
        responses={
            200: OpenApiResponse(
                response=PublicETicketSerializer,
                description="Détails du ticket",
                examples=[
                    OpenApiExample(
                        "Ticket valide",
                        value={
                            "pk": "550e8400-e29b-41d4-a716-446655440000",
                            "name": "E-Ticket N° 42 | Concert de Jazz",
                            "qr_code_data": '{"id64":"...", "secret_phrase":"..."}',
                            "expiration_date": "2025-12-31T23:59:59Z",
                            "is_downloaded": True,
                            "event_name": "Concert de Jazz",
                            "event_date": "2025-12-31",
                            "event_hour": "21:00:00",
                            "event_location": "Palais des Congrès",
                            "order_id": "CMD-ABC123",
                            "download_url": "https://api.example.com/v1/api/tickets/.../download/",
                            "app_deep_link": "wuloevents://ticket/550e8400-e29b-41d4-a716-446655440000"
                        }
                    )
                ]
            ),
            404: OpenApiResponse(description="Ticket non trouvé"),
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Récupère les détails d'un ticket"""
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        summary="Télécharger le PDF du ticket",
        description="Télécharge le ticket au format PDF avec QR code.",
        tags=["Tickets"],
        responses={
            200: OpenApiResponse(
                description="PDF du ticket"
            ),
            404: OpenApiResponse(description="Ticket non trouvé"),
        }
    )
    @action(detail=True, methods=["get"], url_path="download")
    def download_pdf(self, request, pk=None):
        """
        Télécharge le ticket en PDF.
        Marque le ticket comme téléchargé.
        """
        try:
            from apps.events.utils.tickets import generate_e_ticket_pdf
            
            # Récupérer le ticket
            eticket = self.get_object()
            event = eticket.event
            ticket = eticket.ticket
            order = eticket.related_order
            
            # Marquer comme téléchargé
            if not eticket.is_downloaded:
                eticket.is_downloaded = True
                eticket.save(update_fields=["is_downloaded"])
            
            # Logo de l'événement
            logo_url = None
            if event.cover_image:
                logo_url = event.cover_image.url if hasattr(event.cover_image, 'url') else str(event.cover_image)
            
            # Générer le PDF
            pdf_buffer = generate_e_ticket_pdf(
                logo_url=logo_url,
                event_name=event.name,
                location=f"{event.location_name}\n{event.date.strftime('%d/%m/%Y')} à {event.hour.strftime('%Hh%M') if event.hour else ''}",
                qrcode_data=eticket.qr_code_data,
                ticket_name=ticket.name if ticket else "Ticket",
                ticket_price=f"{ticket.price} F CFA" if ticket else "",
                ticket_number=eticket.name.split('N° ')[-1].split(' |')[0] if 'N° ' in eticket.name else "1",
                order_code=order.order_id,
            )
            
            # Créer la réponse HTTP avec le PDF
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type="application/pdf"
            )
            response["Content-Disposition"] = (
                f'attachment; filename="Ticket-{order.order_id}-{eticket.pk}.pdf"'
            )
            
            logger.info(f"Ticket {eticket.pk} téléchargé")
            
            return response
            
        except Exception as e:
            logger.exception(f"Erreur téléchargement ticket {pk}: {e}")
            return Response(
                {"detail": "Erreur lors de la génération du PDF"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Vérifier la validité d'un ticket",
        description="Vérifie si un ticket est valide et n'a pas encore été utilisé.",
        tags=["Tickets"],
        responses={
            200: OpenApiResponse(
                description="Statut de validité du ticket",
                examples=[
                    OpenApiExample(
                        "Ticket valide",
                        value={
                            "valid": True,
                            "message": "Ticket valide",
                            "event_name": "Concert de Jazz",
                            "ticket_name": "E-Ticket N° 42",
                            "expiration_date": "2025-12-31T23:59:59Z"
                        }
                    ),
                    OpenApiExample(
                        "Ticket expiré",
                        value={
                            "valid": False,
                            "message": "Ticket expiré",
                            "expiration_date": "2024-12-31T23:59:59Z"
                        }
                    )
                ]
            ),
            404: OpenApiResponse(description="Ticket non trouvé"),
        }
    )
    @action(detail=True, methods=["get"], url_path="verify")
    def verify_ticket(self, request, pk=None):
        """
        Vérifie la validité d'un ticket.
        Utilisé pour le scan à l'entrée des événements.
        """
        from django.utils import timezone
        
        eticket = self.get_object()
        
        # Vérifier si le ticket est actif
        if not eticket.active:
            return Response({
                "valid": False,
                "message": "Ce ticket a été désactivé",
            }, status=status.HTTP_200_OK)
        
        # Vérifier l'expiration
        if eticket.expiration_date and eticket.expiration_date < timezone.now():
            return Response({
                "valid": False,
                "message": "Ce ticket a expiré",
                "expiration_date": eticket.expiration_date,
            }, status=status.HTTP_200_OK)
        
        # Vérifier si l'événement est valide
        if not eticket.event.valid:
            return Response({
                "valid": False,
                "message": "L'événement associé n'est pas valide",
            }, status=status.HTTP_200_OK)
        
        # Ticket valide
        return Response({
            "valid": True,
            "message": "Ticket valide",
            "event_name": eticket.event.name,
            "ticket_name": eticket.name,
            "expiration_date": eticket.expiration_date,
            "order_id": eticket.related_order.order_id,
        }, status=status.HTTP_200_OK)


class TicketDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour consulter l'état des envois de tickets.
    Permet de suivre les livraisons et les retries.
    
    Endpoints:
    - GET /api/ticket-deliveries/               -> Liste des envois
    - GET /api/ticket-deliveries/{id}/          -> Détails d'un envoi
    - POST /api/ticket-deliveries/{id}/retry/   -> Forcer un retry manuel
    """
    
    queryset = TicketDelivery.objects.all().select_related(
        "eticket", "order"
    ).order_by("-timestamp")
    
    serializer_class = TicketDeliverySerializer
    permission_classes = [AllowAny]  # TODO: Ajouter IsAuthenticated + permissions
    
    def get_serializer_class(self):
        """Utilise le serializer détaillé pour retrieve"""
        if self.action == "retrieve":
            return TicketDeliveryDetailSerializer
        return self.serializer_class
    
    @extend_schema(
        summary="Forcer un nouveau retry d'envoi",
        description="Force un nouveau tentative d'envoi pour un ticket échoué.",
        tags=["Tickets"],
        responses={
            200: OpenApiResponse(
                description="Retry programmé avec succès",
                examples=[
                    OpenApiExample(
                        "Succès",
                        value={
                            "message": "Retry programmé avec succès",
                            "delivery_id": "123",
                            "status": "RETRY"
                        }
                    )
                ]
            ),
            400: OpenApiResponse(description="Retry impossible"),
        }
    )
    @action(detail=True, methods=["post"], url_path="retry")
    def retry_delivery(self, request, pk=None):
        """
        Force un nouveau retry manuel pour un envoi échoué.
        """
        from apps.super_sellers.services.delivery import TicketDeliveryService
        
        delivery = self.get_object()
        
        if not delivery.can_retry():
            return Response({
                "message": "Retry impossible pour cet envoi",
                "reason": f"Statut actuel: {delivery.status}, "
                          f"Tentatives: {delivery.retry_count}/{delivery.max_retry_count}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Traiter l'envoi
        success = TicketDeliveryService.process_delivery(delivery)
        
        if success:
            return Response({
                "message": "Envoi réussi",
                "delivery_id": str(delivery.pk),
                "status": delivery.status,
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "message": "Envoi échoué, un nouveau retry a été programmé",
                "delivery_id": str(delivery.pk),
                "status": delivery.status,
                "next_retry_at": delivery.next_retry_at,
            }, status=status.HTTP_200_OK)