
"""
Signaux pour la gestion automatique des notifications
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from apps.events.models.ticket_stock import TicketStock
from apps.events.services.commission_service import CommissionNotificationService


# Seuils par défaut
LOW_STOCK_THRESHOLD_SELLER = 10  # Alerter le vendeur quand il reste 10 tickets
LOW_STOCK_THRESHOLD_SUPER_SELLER = 50  # Alerter le super-vendeur quand total < 50


@receiver(pre_save, sender=TicketStock)
def check_stock_levels(sender, instance, **kwargs):
    """
    Vérifier les niveaux de stock avant la sauvegarde.
    Envoyer des notifications si le stock est bas.
    """
    
    # Calculer le stock disponible
    available = instance.total_allocated - instance.total_sold
    
    # Si c'est une mise à jour (pas une création)
    if instance.pk:
        try:
            old_instance = TicketStock.objects.get(pk=instance.pk)
            old_available = old_instance.total_allocated - old_instance.total_sold
            
            # Si le stock a baissé et est maintenant sous le seuil
            if old_available > LOW_STOCK_THRESHOLD_SELLER >= available:
                # Notifier le vendeur
                CommissionNotificationService.notify_low_stock(
                    seller=instance.seller,
                    event=instance.event,
                    remaining_quantity=available,
                    threshold=LOW_STOCK_THRESHOLD_SELLER
                )
        except TicketStock.DoesNotExist:
            pass


@receiver(post_save, sender=TicketStock)
def check_super_seller_total_stock(sender, instance, created, **kwargs):
    """
    Vérifier le stock total d'un super-vendeur après chaque vente.
    """
    
    if not created:  # Seulement pour les mises à jour
        # Calculer le stock total restant pour cet événement
        from django.db.models import Sum, F
        
        total_remaining = TicketStock.objects.filter(
            seller__super_seller=instance.seller.super_seller,
            event=instance.event,
            active=True
        ).aggregate(
            total=Sum(F('total_allocated') - F('total_sold'))
        )['total'] or 0
        
        # Si le stock total est bas, notifier le super-vendeur
        if total_remaining <= LOW_STOCK_THRESHOLD_SUPER_SELLER:
            # Vérifier qu'on n'a pas déjà notifié récemment
            # (pour éviter de spammer)
            from django.core.cache import cache
            cache_key = f'low_stock_notif_{instance.seller.super_seller.pk}_{instance.event.pk}'
            
            if not cache.get(cache_key):
                CommissionNotificationService.notify_super_seller_low_stock(
                    super_seller=instance.seller.super_seller,
                    event=instance.event,
                    total_remaining=total_remaining,
                    threshold=LOW_STOCK_THRESHOLD_SUPER_SELLER
                )
                
                # Mettre en cache pour 1 heure
                cache.set(cache_key, True, 3600)