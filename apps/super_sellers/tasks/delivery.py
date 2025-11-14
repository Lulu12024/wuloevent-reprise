# -*- coding: utf-8 -*-
"""

    
Tâches Celery pour l'envoi automatique de tickets avec retry.
"""

import logging
from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone

logger = get_task_logger(__name__)


@shared_task(name="process_ticket_delivery_retries")
def process_ticket_delivery_retries():
    """
    Tâche Celery pour traiter tous les envois en attente de retry.
    
    À exécuter périodiquement (toutes les 5-10 minutes).
    
    
    CELERY_BEAT_SCHEDULE = {
        'process-ticket-delivery-retries': {
            'task': 'process_ticket_delivery_retries',
            'schedule': crontab(minute='*/10'),  # Toutes les 10 minutes
        },
    }
    """
    try:
        from apps.super_sellers.services.delivery import TicketDeliveryService
        
        logger.info("Début du traitement des retries de tickets")
        
        success_count, fail_count = TicketDeliveryService.process_pending_retries()
        
        logger.info(
            f"Traitement des retries terminé : "
            f"{success_count} succès, {fail_count} échecs"
        )
        
        return {
            "success": True,
            "processed": success_count + fail_count,
            "success_count": success_count,
            "fail_count": fail_count,
            "timestamp": timezone.now().isoformat(),
        }
        
    except Exception as e:
        logger.exception(f"Erreur lors du traitement des retries : {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": timezone.now().isoformat(),
        }


@shared_task(name="send_tickets_async")
def send_tickets_async(order_id: str):
    """
    Tâche Celery pour envoyer les tickets d'une commande de manière asynchrone.
    
    Args:
        order_id: UUID de la commande
    
    Usage:
        from apps.super_sellers.tasks.delivery import send_tickets_async
        send_tickets_async.delay(str(order.pk))
    """
    try:
        from apps.events.models import Order
        from apps.super_sellers.services.delivery import send_tickets_for_order
        
        logger.info(f"Envoi asynchrone des tickets pour commande {order_id}")
        
        # Récupérer la commande
        order = Order.objects.prefetch_related("related_e_tickets").get(pk=order_id)
        etickets = list(order.related_e_tickets.all())
        
        if not etickets:
            logger.warning(f"Aucun ticket trouvé pour la commande {order_id}")
            return {
                "success": False,
                "message": "Aucun ticket trouvé",
                "order_id": order_id,
            }
        
        # Envoyer les tickets
        stats = send_tickets_for_order(order, etickets)
        
        logger.info(
            f"Envoi terminé pour commande {order_id} : "
            f"{stats['sent']} envoyés, {stats['failed']} échoués, "
            f"{stats['pending']} en attente"
        )
        
        return {
            "success": True,
            "order_id": order_id,
            "stats": stats,
            "timestamp": timezone.now().isoformat(),
        }
        
    except Exception as e:
        logger.exception(f"Erreur envoi tickets pour commande {order_id} : {e}")
        return {
            "success": False,
            "error": str(e),
            "order_id": order_id,
            "timestamp": timezone.now().isoformat(),
        }


@shared_task(name="send_ticket_reminder")
def send_ticket_reminder(eticket_id: str):
    """
    Envoie un rappel pour un événement à venir.
    À exécuter 24h avant l'événement.
    
    Args:
        eticket_id: UUID du ticket
    """
    try:
        from apps.events.models import ETicket
        from apps.super_sellers.services.templates import WhatsAppTemplate
        
        logger.info(f"Envoi rappel pour ticket {eticket_id}")
        
        eticket = ETicket.objects.select_related("event", "related_order").get(pk=eticket_id)
        
        # Vérifier si l'événement est dans les prochaines 24-48h
        event = eticket.event
        if not event.date:
            logger.warning(f"Pas de date pour l'événement du ticket {eticket_id}")
            return {"success": False, "message": "Pas de date d'événement"}
        
        # Générer le message de rappel
        order = eticket.related_order
        recipient_name = order.name or "Cher client"
        event_date = event.date.strftime("%d/%m/%Y")
        
        message = WhatsAppTemplate.get_reminder_message(
            recipient_name=recipient_name,
            event_name=event.name,
            event_date=event_date
        )
        
        # TODO: Envoyer le message WhatsApp
        # Pour l'instant, on log uniquement
        logger.info(f"Message de rappel préparé pour {order.phone}: {message[:50]}...")
        
        return {
            "success": True,
            "eticket_id": eticket_id,
            "message": "Rappel préparé (WhatsApp non encore implémenté)",
            "timestamp": timezone.now().isoformat(),
        }
        
    except Exception as e:
        logger.exception(f"Erreur envoi rappel pour ticket {eticket_id} : {e}")
        return {
            "success": False,
            "error": str(e),
            "eticket_id": eticket_id,
            "timestamp": timezone.now().isoformat(),
        }


@shared_task(name="cleanup_old_delivery_logs")
def cleanup_old_delivery_logs(days: int = 90):
    """
    Nettoie les logs d'envoi de plus de X jours.
    À exécuter périodiquement (une fois par semaine).
    
    Args:
        days: Nombre de jours à conserver
    
    Ajouter dans CELERY_BEAT_SCHEDULE:
    'cleanup-old-delivery-logs': {
        'task': 'cleanup_old_delivery_logs',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Dimanche à 3h
        'kwargs': {'days': 90},
    }
    """
    try:
        from apps.events.models.ticket_delivery import TicketDelivery, DeliveryStatus
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        logger.info(f"Nettoyage des logs d'envoi avant {cutoff_date}")
        
        # Supprimer les envois réussis anciens
        deleted_count = TicketDelivery.objects.filter(
            status=DeliveryStatus.SENT,
            sent_at__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"{deleted_count} anciens logs d'envoi supprimés")
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
            "timestamp": timezone.now().isoformat(),
        }
        
    except Exception as e:
        logger.exception(f"Erreur nettoyage logs : {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": timezone.now().isoformat(),
        }