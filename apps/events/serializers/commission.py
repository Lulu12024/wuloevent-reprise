
"""
Serializers pour la gestion des commissions
"""

from rest_framework import serializers
from django.utils import timezone
from apps.events.models.commission import EventCommissionOffer, SuperSellerOfferAcceptance
from apps.events.serializers import LightEventSerializer
from apps.organizations.serializers import OrganizationSerializer


class EventCommissionOfferSerializer(serializers.ModelSerializer):
    """Serializer pour les offres de commission"""
    
    event_details = LightEventSerializer(source='event', read_only=True)
    organization_details = OrganizationSerializer(source='organization', read_only=True)
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = EventCommissionOffer
        fields = [
            'uuid', 'event', 'event_details', 'organization', 'organization_details',
            'commission_percentage', 'status', 'description', 'valid_until',
            'total_accepted', 'is_expired', 'timestamp', 'updated', 'metadata'
        ]
        read_only_fields = ['uuid', 'organization', 'total_accepted', 'timestamp', 'updated']
    
    def get_is_expired(self, obj):
        """Vérifier si l'offre a expiré"""
        if obj.valid_until:
            return timezone.now() > obj.valid_until
        return False
    
    def validate_commission_percentage(self, value):
        """Valider que la commission est au minimum 10%"""
        if value < 10:
            raise serializers.ValidationError("La commission minimale est de 10%")
        return value
    
    def validate_event(self, value):
        """Vérifier que l'événement n'a pas déjà une offre"""
        if self.instance is None:  # Création
            if hasattr(value, 'commission_offer'):
                raise serializers.ValidationError(
                    "Cet événement a déjà une offre de commission active"
                )
        return value
    
    def create(self, validated_data):
        """Créer une offre et envoyer notifications"""
        # Ajouter l'organisation depuis le contexte
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            # Récupérer l'organisation de l'evenement
            from apps.organizations.models import OrganizationMembership
            membership = OrganizationMembership.objects.filter(
                user=request.user,
                roles__name__in=['OWNER', 'ADMIN']
            ).first()

            print(membership)


            event = validated_data.get('event')
            print(event)

            if event:
                validated_data['organization'] = event.organization
        
        offer = super().create(validated_data)
        
        # Envoyer notifications aux super-vendeurs
        from apps.events.services.commission_service import CommissionNotificationService
        CommissionNotificationService.notify_new_offer(offer)
        
        return offer
    
    def update(self, instance, validated_data):
        """Mettre à jour une offre et notifier si changement de commission"""
        old_percentage = instance.commission_percentage
        offer = super().update(instance, validated_data)
        
        # Si le pourcentage a changé, notifier
        if 'commission_percentage' in validated_data and old_percentage != offer.commission_percentage:
            from apps.events.services.commission_service import CommissionNotificationService
            CommissionNotificationService.notify_offer_updated(offer, old_percentage)
        
        return offer


class SuperSellerOfferAcceptanceSerializer(serializers.ModelSerializer):
    """Serializer pour l'acceptation d'offres par les super-vendeurs"""
    
    offer_details = EventCommissionOfferSerializer(source='offer', read_only=True)
    super_seller_details = OrganizationSerializer(source='super_seller', read_only=True)
    
    class Meta:
        model = SuperSellerOfferAcceptance
        fields = [
            'uuid', 'offer', 'offer_details', 'super_seller', 'super_seller_details',
            'status', 'seller_commission_percentage', 'accepted_at', 'rejected_at',
            'rejection_reason', 'notes', 'timestamp', 'updated', 'metadata'
        ]
        read_only_fields = [
            'uuid', 'super_seller', 'accepted_at', 'rejected_at',
            'timestamp', 'updated'
        ]
    
    def validate(self, attrs):
        """Validation globale"""
        status = attrs.get('status', self.instance.status if self.instance else None)
        seller_commission = attrs.get('seller_commission_percentage')
        offer = attrs.get('offer', self.instance.offer if self.instance else None)
        
        # Si accepté, commission vendeur obligatoire
        if status == SuperSellerOfferAcceptance.AcceptanceStatus.ACCEPTED:
            if seller_commission is None:
                raise serializers.ValidationError({
                    'seller_commission_percentage': 'Vous devez définir la commission pour vos vendeurs'
                })
            
            # Vérifier que la commission vendeur ne dépasse pas l'offre
            if offer and seller_commission > offer.commission_percentage:
                raise serializers.ValidationError({
                    'seller_commission_percentage': f'La commission vendeur ne peut pas dépasser {offer.commission_percentage}%'
                })
        
        # Si rejeté, raison obligatoire
        if status == SuperSellerOfferAcceptance.AcceptanceStatus.REJECTED:
            if not attrs.get('rejection_reason'):
                raise serializers.ValidationError({
                    'rejection_reason': 'Veuillez indiquer la raison du rejet'
                })
        
        return attrs
    
    def create(self, validated_data):
        """Créer une acceptation"""
        # Ajouter le super-vendeur depuis le contexte
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            from apps.organizations.models import OrganizationMembership
            membership = OrganizationMembership.objects.filter(
                user=request.user,
                organization__organization_type='SUPER_SELLER'
            ).first()
            
            if membership:
                validated_data['super_seller'] = membership.organization
        
        acceptance = super().create(validated_data)
        
        # Notifier l'organisation standard
        if acceptance.status == SuperSellerOfferAcceptance.AcceptanceStatus.ACCEPTED:
            from apps.events.services.commission_service import CommissionNotificationService
            CommissionNotificationService.notify_offer_accepted(acceptance)
        
        return acceptance


class AvailableOfferSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les offres disponibles pour les super-vendeurs"""
    
    event_details = LightEventSerializer(source='event', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    has_accepted = serializers.SerializerMethodField()
    my_acceptance = serializers.SerializerMethodField()
    
    class Meta:
        model = EventCommissionOffer
        fields = [
            'uuid', 'event_details', 'organization_name', 'commission_percentage',
            'description', 'valid_until', 'total_accepted', 'has_accepted',
            'my_acceptance', 'timestamp'
        ]
    
    def get_has_accepted(self, obj):
        """Vérifier si le super-vendeur a déjà accepté"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            from apps.organizations.models import OrganizationMembership
            membership = OrganizationMembership.objects.filter(
                user=request.user,
                organization__organization_type='SUPER_SELLER'
            ).first()
            
            if membership:
                return obj.acceptances.filter(
                    super_seller=membership.organization,
                    status=SuperSellerOfferAcceptance.AcceptanceStatus.ACCEPTED
                ).exists()
        return False
    
    def get_my_acceptance(self, obj):
        """Récupérer l'acceptation de ce super-vendeur si elle existe"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            from apps.organizations.models import OrganizationMembership
            membership = OrganizationMembership.objects.filter(
                user=request.user,
                organization__organization_type='SUPER_SELLER'
            ).first()
            
            if membership:
                acceptance = obj.acceptances.filter(
                    super_seller=membership.organization
                ).first()
                
                if acceptance:
                    return {
                        'uuid': str(acceptance.uuid),
                        'status': acceptance.status,
                        'seller_commission_percentage': acceptance.seller_commission_percentage
                    }
        return None