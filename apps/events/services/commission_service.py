"""
Service de gestion des commissions en cascade
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.events.models.commission import EventCommissionOffer, SuperSellerOfferAcceptance


class CommissionCalculationService:
    """
    Service pour calculer les commissions en cascade :
    Prix Ticket → Retenue WuloEvents → Commission Org Standard → Commission Vendeur
    """
    
    @staticmethod
    def calculate_distribution(
        ticket_price: Decimal,
        wulo_percentage: Decimal,
        event_commission_offer: EventCommissionOffer = None,
        seller_acceptance: SuperSellerOfferAcceptance = None
    ) -> dict:
        """
        Calcule la distribution des montants pour une vente de ticket.
        
        Args:
            ticket_price: Prix du ticket
            wulo_percentage: Pourcentage retenu par WuloEvents
            event_commission_offer: Offre de commission de l'événement
            seller_acceptance: Acceptation du vendeur
        
        Returns:
            dict avec la distribution détaillée
        """
        
        # 1. Retenue WuloEvents
        wulo_amount = ticket_price * (wulo_percentage / Decimal('100'))
        remaining_after_wulo = ticket_price - wulo_amount
        
        # 2. Commission Organisation Standard (si offre existe)
        org_commission_amount = Decimal('0')
        if event_commission_offer and event_commission_offer.status == EventCommissionOffer.OfferStatus.ACTIVE:
            org_commission_amount = remaining_after_wulo * (
                event_commission_offer.commission_percentage / Decimal('100')
            )
        
        remaining_after_org = remaining_after_wulo - org_commission_amount
        
        # 3. Commission Super-Vendeur (ce qui reste après org)
        super_seller_amount = remaining_after_org
        
        # 4. Commission Vendeur (sur la part super-vendeur)
        seller_commission_amount = Decimal('0')
        if seller_acceptance and seller_acceptance.status == SuperSellerOfferAcceptance.AcceptanceStatus.ACCEPTED:
            seller_commission_amount = super_seller_amount * (
                seller_acceptance.seller_commission_percentage / Decimal('100')
            )
        
        # 5. Part finale du super-vendeur (après avoir payé le vendeur)
        final_super_seller_amount = super_seller_amount - seller_commission_amount
        
        return {
            'ticket_price': float(ticket_price),
            'wulo_amount': float(wulo_amount),
            'wulo_percentage': float(wulo_percentage),
            'remaining_after_wulo': float(remaining_after_wulo),
            
            'org_commission_percentage': float(event_commission_offer.commission_percentage) if event_commission_offer else 0,
            'org_commission_amount': float(org_commission_amount),
            'remaining_after_org': float(remaining_after_org),
            
            'seller_commission_percentage': float(seller_acceptance.seller_commission_percentage) if seller_acceptance else 0,
            'seller_commission_amount': float(seller_commission_amount),
            
            'super_seller_total_amount': float(super_seller_amount),
            'super_seller_final_amount': float(final_super_seller_amount),
            
            'breakdown': {
                'wulo_events': float(wulo_amount),
                'organization': float(org_commission_amount),
                'seller': float(seller_commission_amount),
                'super_seller': float(final_super_seller_amount)
            }
        }
    
    @staticmethod
    def get_commission_info_for_event(event_id):
        """
        Récupère les informations de commission pour un événement.
        """
        try:
            from apps.events.models import Event
            event = Event.objects.select_related('commission_offer').get(pk=event_id)
            
            if hasattr(event, 'commission_offer'):
                offer = event.commission_offer
                return {
                    'has_offer': True,
                    'commission_percentage': float(offer.commission_percentage),
                    'status': offer.status,
                    'total_accepted': offer.total_accepted,
                    'description': offer.description
                }
            
            return {'has_offer': False}
        
        except Exception:
            return {'has_offer': False}
    
    @staticmethod
    def get_seller_commission_info(seller, event):
        """
        Récupère les informations de commission pour un vendeur sur un événement.
        """
        try:
            # Récupérer le super-vendeur du vendeur
            super_seller = seller.super_seller
            
            # Récupérer l'offre de l'événement
            if not hasattr(event, 'commission_offer'):
                return {'has_commission': False}
            
            offer = event.commission_offer
            
            # Récupérer l'acceptation du super-vendeur
            acceptance = SuperSellerOfferAcceptance.objects.filter(
                offer=offer,
                super_seller=super_seller,
                status=SuperSellerOfferAcceptance.AcceptanceStatus.ACCEPTED
            ).first()
            
            if acceptance:
                return {
                    'has_commission': True,
                    'seller_percentage': float(acceptance.seller_commission_percentage),
                    'org_percentage': float(offer.commission_percentage),
                    'super_seller_name': super_seller.name
                }
            
            return {'has_commission': False}
        
        except Exception:
            return {'has_commission': False}


class CommissionNotificationService:
    """Service pour gérer les notifications liées aux commissions"""
    
    @staticmethod
    def notify_new_offer(offer: EventCommissionOffer):

        # TODO 
        """
        Notifier tous les super-vendeurs qu'une nouvelle offre est disponible.
        """
        # from apps.organizations.models import Organization
        # from apps.notifications.services import NotificationService
        
        # # Récupérer tous les super-vendeurs actifs
        # super_sellers = Organization.objects.filter(
        #     organization_type='SUPER_SELLER',
        #     active=True
        # )
        
        # for super_seller in super_sellers:
        #     # Récupérer le propriétaire de l'organisation
        #     owner = super_seller.owner
            
        #     NotificationService.create_notification(
        #         user=owner,
        #         notification_type='NEW_COMMISSION_OFFER',
        #         title='Nouvelle offre de commission disponible',
        #         message=f"L'événement '{offer.event.name}' propose {offer.commission_percentage}% de commission.",
        #         data={
        #             'offer_id': str(offer.uuid),
        #             'event_id': str(offer.event.pk),
        #             'event_name': offer.event.name,
        #             'commission_percentage': float(offer.commission_percentage),
        #             'organization_name': offer.organization.name
        #         }
        #     )
        pass
    
    @staticmethod
    def notify_offer_updated(offer: EventCommissionOffer, old_percentage: Decimal):
        # TODO 
        """
        Notifier les super-vendeurs ayant accepté qu'une offre a été modifiée.
        """
        # from apps.notifications.services import NotificationService
        
        # # Récupérer toutes les acceptations actives
        # acceptances = offer.acceptances.filter(
        #     status=SuperSellerOfferAcceptance.AcceptanceStatus.ACCEPTED
        # ).select_related('super_seller')
        
        # for acceptance in acceptances:
        #     owner = acceptance.super_seller.owner
            
        #     # TODO 
        #     NotificationService.create_notification(
        #         user=owner,
        #         notification_type='COMMISSION_OFFER_UPDATED',
        #         title='Offre de commission modifiée',
        #         message=f"L'offre pour '{offer.event.name}' est passée de {old_percentage}% à {offer.commission_percentage}%.",
        #         data={
        #             'offer_id': str(offer.uuid),
        #             'event_id': str(offer.event.pk),
        #             'event_name': offer.event.name,
        #             'old_percentage': float(old_percentage),
        #             'new_percentage': float(offer.commission_percentage)
        #         }
        #     )
        pass
    @staticmethod
    def notify_offer_accepted(acceptance: SuperSellerOfferAcceptance):
        # TODO 
        # """
        # Notifier l'organisation standard qu'un super-vendeur a accepté son offre.
        # """
        # from apps.notifications.services import NotificationService
        
        # offer = acceptance.offer
        # org_owner = offer.organization.owner
        
        # NotificationService.create_notification(
        #     user=org_owner,
        #     notification_type='OFFER_ACCEPTED',
        #     title='Offre acceptée par un super-vendeur',
        #     message=f"{acceptance.super_seller.name} a accepté votre offre pour '{offer.event.name}'.",
        #     data={
        #         'acceptance_id': str(acceptance.uuid),
        #         'offer_id': str(offer.uuid),
        #         'event_id': str(offer.event.pk),
        #         'event_name': offer.event.name,
        #         'super_seller_name': acceptance.super_seller.name,
        #         'seller_commission': float(acceptance.seller_commission_percentage)
        #     }
        # )
        pass
    @staticmethod
    def notify_low_stock(seller, event, remaining_quantity: int, threshold: int = 10):

        # TODO 
        # """
        # Notifier un vendeur que son stock est faible.
        # """
        # from apps.notifications.services import NotificationService
        
        # NotificationService.create_notification(
        #     user=seller.user,
        #     notification_type='LOW_STOCK_ALERT',
        #     title='Stock faible',
        #     message=f"Il ne reste que {remaining_quantity} tickets pour '{event.name}'.",
        #     data={
        #         'event_id': str(event.pk),
        #         'event_name': event.name,
        #         'remaining_quantity': remaining_quantity,
        #         'threshold': threshold
        #     }
        # )
        pass
    @staticmethod
    def notify_super_seller_low_stock(super_seller, event, total_remaining: int, threshold: int = 50):

        # TODO 
        
        """
        Notifier un super-vendeur que le stock total de ses vendeurs est faible.
        """
        # from apps.notifications.services import NotificationService
        
        # NotificationService.create_notification(
        #     user=super_seller.owner,
        #     notification_type='SUPER_SELLER_LOW_STOCK',
        #     title='Stock global faible',
        #     message=f"Stock total restant pour '{event.name}': {total_remaining} tickets.",
        #     data={
        #         'event_id': str(event.pk),
        #         'event_name': event.name,
        #         'total_remaining': total_remaining,
        #         'threshold': threshold
        #     }
        # )
        pass