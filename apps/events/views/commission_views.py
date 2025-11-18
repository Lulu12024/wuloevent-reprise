"""
ViewSets pour la gestion des commissions
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone

from apps.events.models.commission import EventCommissionOffer, SuperSellerOfferAcceptance
from apps.events.serializers.commission import (
    EventCommissionOfferSerializer,
    SuperSellerOfferAcceptanceSerializer,
    AvailableOfferSerializer
)
from apps.events.services.commission_service import CommissionCalculationService


class EventCommissionOfferViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des offres de commission par les organisateurs standard.
    
    Liste des endpoints:
    - GET /api/v1/commission-offers/ - Liste des offres de l'org
    - POST /api/v1/commission-offers/ - Créer une offre
    - GET /api/v1/commission-offers/{uuid}/ - Détails d'une offre
    - PUT/PATCH /api/v1/commission-offers/{uuid}/ - Modifier une offre
    - DELETE /api/v1/commission-offers/{uuid}/ - Supprimer une offre
    - GET /api/v1/commission-offers/{uuid}/acceptances/ - Liste des acceptations
    - POST /api/v1/commission-offers/{uuid}/pause/ - Mettre en pause
    - POST /api/v1/commission-offers/{uuid}/activate/ - Réactiver
    """
    
    serializer_class = EventCommissionOfferSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'uuid'
    
    def get_queryset(self):
        """Filtrer les offres de l'organisation de l'utilisateur"""
        user = self.request.user
        
        # Récupérer l'organisation de l'utilisateur
        from apps.organizations.models import OrganizationMembership
        memberships = OrganizationMembership.objects.filter(
            user=user,
            roles__in=['OWNER', 'ADMIN']
        ).values_list('organization_id', flat=True)
        print(memberships)
        return EventCommissionOffer.objects.filter(
            organization_id__in=memberships
        ).select_related('event', 'organization').prefetch_related('acceptances')
    
    def perform_create(self, serializer):
        """Créer une offre pour l'organisation de l'utilisateur"""
        serializer.save()
    
    @action(detail=True, methods=['get'])
    def acceptances(self, request, uuid=None):
        """Liste des super-vendeurs ayant accepté l'offre"""
        offer = self.get_object()
        acceptances = offer.acceptances.select_related('super_seller').all()
        serializer = SuperSellerOfferAcceptanceSerializer(acceptances, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def pause(self, request, uuid=None):
        """Mettre l'offre en pause"""
        offer = self.get_object()
        offer.status = EventCommissionOffer.OfferStatus.PAUSED
        offer.save(update_fields=['status'])
        
        return Response({
            'message': 'Offre mise en pause',
            'status': offer.status
        })
    
    @action(detail=True, methods=['post'])
    def activate(self, request, uuid=None):
        """Réactiver l'offre"""
        offer = self.get_object()
        offer.status = EventCommissionOffer.OfferStatus.ACTIVE
        offer.save(update_fields=['status'])
        
        return Response({
            'message': 'Offre réactivée',
            'status': offer.status
        })
    
    @action(detail=True, methods=['get'])
    def stats(self, request, uuid=None):
        """Statistiques sur l'offre"""
        offer = self.get_object()
        
        acceptances = offer.acceptances.all()
        total_accepted = acceptances.filter(
            status=SuperSellerOfferAcceptance.AcceptanceStatus.ACCEPTED
        ).count()
        total_pending = acceptances.filter(
            status=SuperSellerOfferAcceptance.AcceptanceStatus.PENDING
        ).count()
        total_rejected = acceptances.filter(
            status=SuperSellerOfferAcceptance.AcceptanceStatus.REJECTED
        ).count()
        
        return Response({
            'total_acceptances': acceptances.count(),
            'accepted': total_accepted,
            'pending': total_pending,
            'rejected': total_rejected,
            'commission_percentage': offer.commission_percentage,
            'status': offer.status,
            'is_expired': offer.valid_until and timezone.now() > offer.valid_until if offer.valid_until else False
        })


class SuperSellerOfferViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les super-vendeurs pour voir et accepter les offres.
    
    Liste des endpoints:
    - GET /api/v1/super-seller/offers/available/ - Offres disponibles
    - GET /api/v1/super-seller/offers/my-acceptances/ - Mes acceptations
    - POST /api/v1/super-seller/offers/{uuid}/accept/ - Accepter une offre
    - POST /api/v1/super-seller/offers/{uuid}/reject/ - Rejeter une offre
    - PATCH /api/v1/super-seller/offers/acceptances/{uuid}/ - Modifier commission vendeur
    """
    
    serializer_class = AvailableOfferSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'uuid'
    
    def get_queryset(self):
        """Récupérer les offres disponibles pour les super-vendeurs"""
        # Offres actives et non expirées
        queryset = EventCommissionOffer.objects.filter(
            status=EventCommissionOffer.OfferStatus.ACTIVE
        ).select_related('event', 'organization')
        
        # Filtrer les offres expirées
        now = timezone.now()
        queryset = queryset.filter(
            Q(valid_until__isnull=True) | Q(valid_until__gt=now)
        )
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Liste des offres disponibles"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_acceptances(self, request):
        """Liste de mes acceptations"""
        # Récupérer l'organisation super-vendeur de l'utilisateur
        from apps.organizations.models import OrganizationMembership
        membership = OrganizationMembership.objects.filter(
            user=request.user,
            organization__organization_type='SUPER_SELLER'
        ).first()
        
        if not membership:
            return Response(
                {'error': 'Vous devez être membre d\'une organisation super-vendeur'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        acceptances = SuperSellerOfferAcceptance.objects.filter(
            super_seller=membership.organization
        ).select_related('offer', 'offer__event', 'offer__organization')
        
        serializer = SuperSellerOfferAcceptanceSerializer(acceptances, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def accept(self, request, uuid=None):
        """Accepter une offre"""
        offer = self.get_object()
        
        # Récupérer l'organisation super-vendeur
        from apps.organizations.models import OrganizationMembership
        membership = OrganizationMembership.objects.filter(
            user=request.user,
            organization__organization_type='SUPER_SELLER'
        ).first()
        
        if not membership:
            return Response(
                {'error': 'Vous devez être membre d\'une organisation super-vendeur'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Vérifier si déjà accepté
        existing = SuperSellerOfferAcceptance.objects.filter(
            offer=offer,
            super_seller=membership.organization
        ).first()
        
        if existing and existing.status == SuperSellerOfferAcceptance.AcceptanceStatus.ACCEPTED:
            return Response(
                {'error': 'Vous avez déjà accepté cette offre'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Récupérer la commission vendeur depuis la requête
        seller_commission = request.data.get('seller_commission_percentage')
        if not seller_commission:
            return Response(
                {'error': 'Vous devez définir la commission pour vos vendeurs'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        seller_commission = float(seller_commission)
        if seller_commission > float(offer.commission_percentage):
            return Response(
                {'error': f'La commission vendeur ne peut pas dépasser {offer.commission_percentage}%'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Créer ou mettre à jour l'acceptation
        if existing:
            existing.status = SuperSellerOfferAcceptance.AcceptanceStatus.ACCEPTED
            existing.seller_commission_percentage = seller_commission
            existing.save()
            acceptance = existing
        else:
            acceptance = SuperSellerOfferAcceptance.objects.create(
                offer=offer,
                super_seller=membership.organization,
                status=SuperSellerOfferAcceptance.AcceptanceStatus.ACCEPTED,
                seller_commission_percentage=seller_commission
            )
        
        serializer = SuperSellerOfferAcceptanceSerializer(acceptance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, uuid=None):
        """Rejeter une offre"""
        offer = self.get_object()
        
        # Récupérer l'organisation super-vendeur
        from apps.organizations.models import OrganizationMembership
        membership = OrganizationMembership.objects.filter(
            user=request.user,
            organization__organization_type='SUPER_SELLER'
        ).first()
        
        if not membership:
            return Response(
                {'error': 'Vous devez être membre d\'une organisation super-vendeur'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        rejection_reason = request.data.get('rejection_reason', '')
        
        # Créer ou mettre à jour l'acceptation
        acceptance, created = SuperSellerOfferAcceptance.objects.update_or_create(
            offer=offer,
            super_seller=membership.organization,
            defaults={
                'status': SuperSellerOfferAcceptance.AcceptanceStatus.REJECTED,
                'rejection_reason': rejection_reason
            }
        )
        
        serializer = SuperSellerOfferAcceptanceSerializer(acceptance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['patch'], url_path='acceptances/(?P<acceptance_uuid>[^/.]+)')
    def update_acceptance(self, request, acceptance_uuid=None):
        """Modifier la commission vendeur d'une acceptation"""
        # Récupérer l'acceptation
        try:
            acceptance = SuperSellerOfferAcceptance.objects.get(uuid=acceptance_uuid)
        except SuperSellerOfferAcceptance.DoesNotExist:
            return Response(
                {'error': 'Acceptation non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Vérifier que c'est bien son acceptation
        from apps.organizations.models import OrganizationMembership
        membership = OrganizationMembership.objects.filter(
            user=request.user,
            organization=acceptance.super_seller
        ).first()
        
        if not membership:
            return Response(
                {'error': 'Non autorisé'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Mettre à jour la commission vendeur
        new_commission = request.data.get('seller_commission_percentage')
        if new_commission:
            new_commission = float(new_commission)
            if new_commission > float(acceptance.offer.commission_percentage):
                return Response(
                    {'error': f'La commission ne peut pas dépasser {acceptance.offer.commission_percentage}%'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            acceptance.seller_commission_percentage = new_commission
            acceptance.save()
        
        serializer = SuperSellerOfferAcceptanceSerializer(acceptance)
        return Response(serializer.data)


class CommissionCalculationViewSet(viewsets.ViewSet):
    """
    ViewSet pour calculer les commissions.
    
    Endpoint:
    - POST /api/v1/commissions/calculate/ - Calculer la distribution
    """
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """
        Calculer la distribution des commissions pour une vente.
        
        Body:
        {
            "ticket_price": 10000,
            "event_id": "uuid",
            "seller_id": "uuid" (optionnel)
        }
        """
        ticket_price = request.data.get('ticket_price')
        event_id = request.data.get('event_id')
        seller_id = request.data.get('seller_id')
        
        if not ticket_price or not event_id:
            return Response(
                {'error': 'ticket_price et event_id sont requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.events.models import Event
            from apps.events.models.seller import Seller
            from decimal import Decimal
            
            ticket_price = Decimal(str(ticket_price))
            event = Event.objects.get(pk=event_id)
            
            # Récupérer le pourcentage WuloEvents de l'organisation
            wulo_percentage = event.organization.percentage or Decimal('15')
            
            # Récupérer l'offre de commission
            offer = None
            if hasattr(event, 'commission_offer'):
                offer = event.commission_offer
            
            # Récupérer l'acceptation du vendeur si fourni
            acceptance = None
            if seller_id and offer:
                seller = Seller.objects.get(pk=seller_id)
                acceptance = SuperSellerOfferAcceptance.objects.filter(
                    offer=offer,
                    super_seller=seller.super_seller,
                    status=SuperSellerOfferAcceptance.AcceptanceStatus.ACCEPTED
                ).first()
            
            # Calculer
            distribution = CommissionCalculationService.calculate_distribution(
                ticket_price=ticket_price,
                wulo_percentage=wulo_percentage,
                event_commission_offer=offer,
                seller_acceptance=acceptance
            )
            
            return Response(distribution)
        
        except Event.DoesNotExist:
            return Response(
                {'error': 'Événement non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Seller.DoesNotExist:
            return Response(
                {'error': 'Vendeur non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )