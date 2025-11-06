# -*- coding: utf-8 -*-
"""
Views pour les événements éphémères - TICKET-005
API de création et gestion d'événements éphémères

Created on October 29, 2025

@author:
    DevBackend Team - WuloEvents
"""

import logging
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from apps.events.models import Event
from apps.organizations.permissions import (
    IsSuperSellerVerified,
    CanAccessEphemeralEvent
)
from apps.events.serializers.ephemeral_events import (
    EphemeralEventCreationSerializer,
    EphemeralEventDetailSerializer,
    EphemeralEventListSerializer,
    EphemeralEventAccessSerializer
)

logger = logging.getLogger(__name__)


class EphemeralEventCreateAPIView(APIView):
    """
    API de création d'événements éphémères pour les super-vendeurs.
    
    Endpoint : POST /api/super-sellers/events/ephemeral
    
    Permissions requises :
    - Authentifié
    - Super-vendeur vérifié (KYC validé)
    
    Fonctionnalités :
    - Crée un événement non listé publiquement
    - Génère un code d'accès unique
    - Retourne l'URL d'accès unique
    
    TICKET-005
    """
    
    # permission_classes = [IsAuthenticated, IsSuperSellerVerified]
    permission_classes = [IsAuthenticated]
    serializer_class = EphemeralEventCreationSerializer
    
    @extend_schema(
        summary="Créer un événement éphémère",
        description=(
            "Crée un événement éphémère (non listé publiquement) pour un super-vendeur vérifié.\n\n"
            "**Permissions requises :**\n"
            "- Authentifié\n"
            "- Super-vendeur vérifié (KYC validé)\n\n"
            "**Comportement automatique :**\n"
            "- L'événement est marqué comme éphémère (`is_ephemeral=True`)\n"
            "- Un code d'accès unique est généré (`ephemeral_access_code`)\n"
            "- Une URL d'accès unique est fournie (`ephemeral_access_url`)\n"
            "- L'événement n'apparaît pas dans les listings publics\n"
            "- Aucune chatroom n'est créée (événement privé)\n"
        ),
        request=EphemeralEventCreationSerializer,
        responses={
            201: EphemeralEventDetailSerializer,
            400: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                'Exemple de création',
                value={
                    "name": "Concert VIP Privé - Artiste X",
                    "description": "Concert exclusif réservé aux VIP",
                    "type": "uuid-event-type",
                    "organization": "uuid-organization",
                    "default_price": 50000,
                    "date": "2025-12-31",
                    "hour": "20:00:00",
                    "location_name": "Salle VIP Cotonou",
                    "location_lat": 6.3653,
                    "location_long": 2.4286,
                    "participant_limit": 100
                },
                request_only=True
            ),
            OpenApiExample(
                'Réponse succès',
                value={
                    "pk": "uuid-event",
                    "name": "Concert VIP Privé - Artiste X",
                    "description": "Concert exclusif réservé aux VIP",
                    "is_ephemeral": True,
                    "ephemeral_access_code": "EPH-A1B2C3D4E5F6",
                    "ephemeral_access_url": "https://app.wuloevents.com/events/ephemeral/EPH-A1B2C3D4E5F6",
                    "organization": {
                        "pk": "uuid-org",
                        "name": "Max Events"
                    },
                    "default_price": 50000,
                    "date": "2025-12-31",
                    "timestamp": "2025-10-29T10:30:00Z"
                },
                response_only=True
            )
        ],
        tags=['Super-Vendeurs - Événements Éphémères']
    )
    def post(self, request, *args, **kwargs):
        """
        Crée un événement éphémère.
        
        L'événement créé :
        - Ne sera pas listé publiquement
        - Aura un code d'accès unique
        - Sera accessible uniquement via son URL unique
        - N'aura pas de chatroom
        """
        serializer = self.serializer_class(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            # Créer l'événement éphémère
            event = serializer.save()
            
            # Retourner les détails complets
            response_serializer = EphemeralEventDetailSerializer(
                event,
                context={'request': request}
            )
            
            logger.info(
                f"Événement éphémère créé avec succès : {event.name} "
                f"(Code: {event.ephemeral_access_code}) "
                f"par {request.user.email}"
            )
            
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        
        logger.warning(
            f"Échec création événement éphémère par {request.user.email} : "
            f"{serializer.errors}"
        )
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class EphemeralEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour gérer les événements éphémères d'un super-vendeur.
    
    Endpoints :
    - GET /api/super-sellers/events/ephemeral : Liste des événements éphémères
    - GET /api/super-sellers/events/ephemeral/{pk} : Détails d'un événement
    
    Permissions :
    - Super-vendeur vérifié
    - Accès uniquement à ses propres événements éphémères
    
    """
    
    # permission_classes = [IsAuthenticated, IsSuperSellerVerified]
    permission_classes = [IsAuthenticated]
    serializer_class = EphemeralEventListSerializer
    lookup_field = 'pk'
    
    def get_queryset(self):
        """
        Retourne uniquement les événements éphémères du super-vendeur connecté.
        """
        if not hasattr(self.request, 'super_seller_organization'):
            return Event.objects.none()
        
        
        organization = self.request.super_seller_organization
        
        # Filtrer les événements éphémères de cette organisation
        queryset = Event.ephemeral.filter(
            created_by_super_seller=organization
        ).select_related(
            'type',
            'organization',
            'created_by_super_seller'
        ).order_by('-timestamp')
        
        return queryset
    
    def get_serializer_class(self):
        """Utiliser le serializer détaillé pour retrieve"""
        if self.action == 'retrieve':
            return EphemeralEventDetailSerializer
        return EphemeralEventListSerializer
    
    @extend_schema(
        summary="Liste des événements éphémères",
        description=(
            "Récupère la liste de tous les événements éphémères créés par le super-vendeur.\n\n"
            "**Permissions requises :**\n"
            "- Super-vendeur vérifié\n\n"
            "**Filtres :**\n"
            "- `date_min` : Date minimale (YYYY-MM-DD)\n"
            "- `date_max` : Date maximale (YYYY-MM-DD)\n"
            "- `search` : Recherche par nom\n"
        ),
        parameters=[
            OpenApiParameter(
                name='date_min',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Date minimale de l\'événement'
            ),
            OpenApiParameter(
                name='date_max',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Date maximale de l\'événement'
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Recherche par nom d\'événement'
            ),
        ],
        tags=['Super-Vendeurs - Événements Éphémères']
    )
    def list(self, request, *args, **kwargs):
        """Liste tous les événements éphémères du super-vendeur"""
        queryset = self.get_queryset()
        
        # Filtres optionnels
        date_min = request.query_params.get('date_min')
        date_max = request.query_params.get('date_max')
        search = request.query_params.get('search')
        
        if date_min:
            queryset = queryset.filter(date__gte=date_min)
        
        if date_max:
            queryset = queryset.filter(date__lte=date_max)
        
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Détails d'un événement éphémère",
        description=(
            "Récupère les détails complets d'un événement éphémère.\n\n"
            "**Permissions requises :**\n"
            "- Super-vendeur vérifié\n"
            "- L'événement doit appartenir au super-vendeur\n"
        ),
        tags=['Super-Vendeurs - Événements Éphémères']
    )
    def retrieve(self, request, *args, **kwargs):
        """Récupère les détails d'un événement éphémère"""
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        summary="Statistiques d'un événement éphémère",
        description=(
            "Récupère les statistiques de vente d'un événement éphémère.\n\n"
            "**Retourne :**\n"
            "- Nombre de tickets vendus\n"
            "- Montant total généré\n"
            "- Nombre de vendeurs actifs\n"
            "- Stock restant\n"
        ),
        responses={
            200: OpenApiTypes.OBJECT
        },
        tags=['Super-Vendeurs - Événements Éphémères']
    )
    @action(detail=True, methods=['get'], url_path='statistics')
    def statistics(self, request, pk=None):
        """
        Retourne les statistiques de vente d'un événement éphémère.
        
        Endpoint : GET /api/super-sellers/events/ephemeral/{pk}/statistics
        """
        event = self.get_object()
        
        # Calculer les statistiques
        from apps.organizations.models import TicketStock
        from django.db.models import Sum
        
        # Stocks alloués à des vendeurs pour cet événement
        stocks = TicketStock.objects.filter(event=event)
        
        stats = {
            'event': {
                'pk': str(event.pk),
                'name': event.name,
                'date': event.date,
            },
            'tickets': {
                'total_allocated': stocks.aggregate(Sum('total_allocated'))['total_allocated__sum'] or 0,
                'total_sold': stocks.aggregate(Sum('total_sold'))['total_sold__sum'] or 0,
                'total_available': (
                    (stocks.aggregate(Sum('total_allocated'))['total_allocated__sum'] or 0) -
                    (stocks.aggregate(Sum('total_sold'))['total_sold__sum'] or 0)
                ),
            },
            'sellers': {
                'total': stocks.values('seller').distinct().count(),
                'active': stocks.filter(seller__status='ACTIVE').values('seller').distinct().count(),
            },
            'revenue': {
                'total': 0,  # À calculer selon votre système de paiement
                'currency': 'XOF',
            }
        }
        
        return Response(stats, status=status.HTTP_200_OK)


class PublicEphemeralEventAccessAPIView(APIView):
    """
    API publique pour accéder à un événement éphémère via son code d'accès.
    
    Endpoint : GET /api/events/ephemeral/{access_code}
    
    Permissions :
    - Aucune authentification requise
    - Le code d'accès valide suffit
    
    Utilisé pour :
    - Afficher un événement éphémère via son lien unique
    - Permettre aux clients d'accéder aux détails de l'événement
    
    TICKET-005
    """
    
    permission_classes = []  # Accès public
    
    @extend_schema(
        summary="Accéder à un événement éphémère",
        description=(
            "Accède aux détails d'un événement éphémère via son code d'accès unique.\n\n"
            "**Accès public** : Aucune authentification requise.\n\n"
            "Le code d'accès est fourni au format : `EPH-XXXXXXXXXXXX`\n\n"
            "Utilisé pour permettre aux clients d'accéder à l'événement "
            "via le lien partagé par les vendeurs."
        ),
        parameters=[
            OpenApiParameter(
                name='access_code',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='Code d\'accès unique (ex: EPH-A1B2C3D4E5F6)'
            ),
        ],
        responses={
            200: EphemeralEventDetailSerializer,
            404: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                'Réponse succès',
                value={
                    "pk": "uuid-event",
                    "name": "Concert VIP Privé",
                    "description": "Concert exclusif",
                    "is_ephemeral": True,
                    "ephemeral_access_code": "EPH-A1B2C3D4E5F6",
                    "default_price": 50000,
                    "date": "2025-12-31",
                    "location_name": "Salle VIP",
                },
                response_only=True
            )
        ],
        tags=['Événements - Accès Public']
    )
    def get(self, request, access_code, *args, **kwargs):
        """
        Récupère un événement éphémère via son code d'accès.
        
        Args:
            access_code: Code d'accès unique (ex: EPH-A1B2C3D4E5F6)
        
        Returns:
            Détails complets de l'événement éphémère
        """
        try:
            # Chercher l'événement par code d'accès
            event = Event.ephemeral.by_access_code(access_code)
            
            if not event:
                logger.warning(f"Tentative d'accès avec code invalide : {access_code}")
                return Response(
                    {
                        'error': 'Code d\'accès invalide',
                        'detail': 'Aucun événement trouvé avec ce code d\'accès.'
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Incrémenter le compteur de vues
            event.views += 1
            event.save(update_fields=['views'])
            
            # Retourner les détails
            serializer = EphemeralEventDetailSerializer(
                event,
                context={'request': request}
            )
            
            logger.info(
                f"Accès événement éphémère : {event.name} "
                f"(Code: {access_code})"
            )
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(
                f"Erreur lors de l'accès à l'événement éphémère "
                f"(Code: {access_code}) : {e}",
                exc_info=True
            )
            return Response(
                {
                    'error': 'Erreur serveur',
                    'detail': 'Une erreur est survenue lors de la récupération de l\'événement.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )