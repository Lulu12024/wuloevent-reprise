# -*- coding: utf-8 -*-
"""
Created on November 06, 2025

@author:
    Implementation Ticket-011
    
Service d'envoi automatique de tickets avec retry et logging.
"""

import logging
from typing import List, Optional, Dict
from django.db import transaction
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from apps.notifications.whatsapp import send_simple_text

logger = logging.getLogger(__name__)


class TicketDeliveryService:
    """
    Service principal pour l'envoi de tickets.
    Gère l'envoi par email avec attachments PDF et le tracking des envois.
    """
    
    @staticmethod
    @transaction.atomic
    def create_delivery_tasks(order, etickets: List) -> List:
        """
        Crée les tâches d'envoi pour une commande.
        
        Args:
            order: Instance de Order
            etickets: Liste des ETickets à envoyer
        
        Returns:
            Liste des instances TicketDelivery créées
        """
        from apps.events.models.ticket_delivery import TicketDelivery, DeliveryChannel
        
        deliveries = []
        recipient_email = order.email
        recipient_phone = order.phone
        recipient_name = order.name or "Cher client"
        
        # Créer une tâche d'envoi par email si disponible
        if recipient_email:
            for eticket in etickets:
                delivery = TicketDelivery.objects.create(
                    eticket=eticket,
                    order=order,
                    recipient_email=recipient_email,
                    recipient_phone=recipient_phone,
                    recipient_name=recipient_name,
                    channel=DeliveryChannel.EMAIL,
                )
                delivery.add_log("Tâche d'envoi créée", "INFO")
                deliveries.append(delivery)
        
        # Créer une tâche WhatsApp si téléphone disponible
        # (désactivé pour l'instant mais structure prête)
        # if recipient_phone:
        #     for eticket in etickets:
        #         delivery = TicketDelivery.objects.create(
        #             eticket=eticket,
        #             order=order,
        #             recipient_email=recipient_email,
        #             recipient_phone=recipient_phone,
        #             recipient_name=recipient_name,
        #             channel=DeliveryChannel.WHATSAPP,
        #         )
        #         delivery.add_log("Tâche d'envoi WhatsApp créée", "INFO")
        #         deliveries.append(delivery)
        
        logger.info(
            f"Créé {len(deliveries)} tâche(s) d'envoi pour la commande {order.order_id}"
        )
        
        return deliveries
    
    @staticmethod
    def send_ticket_by_email(delivery) -> bool:
        """
        Envoie un ticket par email avec PDF en pièce jointe.
        
        Args:
            delivery: Instance TicketDelivery
        
        Returns:
            True si envoi réussi, False sinon
        """
        try:
            from apps.events.models.ticket_delivery import DeliveryStatus
            from apps.super_sellers.services.templates import get_email_template
            from apps.events.utils.tickets import generate_e_ticket_pdf
            
            # Marquer comme en cours d'envoi
            delivery.status = DeliveryStatus.SENDING
            delivery.save(update_fields=["status"])
            delivery.add_log("Début de l'envoi email", "INFO")
            
            # Récupérer les données nécessaires
            eticket = delivery.eticket
            order = delivery.order
            event = eticket.event
            ticket = eticket.ticket
            
            # Générer le template email
            template_data = get_email_template(
                recipient_name=delivery.recipient_name,
                order=order,
                etickets=[eticket],
            )
            
            # Créer l'email
            email = EmailMultiAlternatives(
                subject=template_data["subject"],
                body=template_data["body_text"],
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[delivery.recipient_email],
            )
            
            # Ajouter la version HTML
            email.attach_alternative(template_data["body_html"], "text/html")
            
            # Générer et attacher le PDF du ticket
            try:
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
                
                # Attacher le PDF
                email.attach(
                    f"Ticket-{order.order_id}-{eticket.pk}.pdf",
                    pdf_buffer.getvalue(),
                    "application/pdf"
                )
                
                delivery.add_log("PDF du ticket généré et attaché", "INFO")
                
            except Exception as pdf_error:
                logger.error(f"Erreur génération PDF pour {eticket.pk}: {pdf_error}")
                delivery.add_log(f"Erreur PDF: {str(pdf_error)}", "WARNING")
                # On continue quand même l'envoi sans le PDF
            
            # Envoyer l'email
            email.send()
            
            # Marquer comme envoyé
            delivery.mark_as_sent(provider_response={
                "sent_at": timezone.now().isoformat(),
                "to": delivery.recipient_email,
            })
            
            logger.info(f"Email envoyé avec succès pour {eticket.name} à {delivery.recipient_email}")
            return True
            
        except Exception as e:
            error_message = f"Erreur envoi email: {str(e)}"
            logger.exception(error_message)
            delivery.mark_as_failed(error_message, schedule_retry=True)
            return False
    
    @staticmethod
    def send_ticket_by_whatsapp(delivery) -> bool:
        """
        Envoie un ticket par WhatsApp.
        (Placeholder pour intégration future)
        
        Args:
            delivery: Instance TicketDelivery
        
        Returns:
            True si envoi réussi, False sinon
        """
        try:
            from apps.events.models.ticket_delivery import DeliveryStatus
            from apps.super_sellers.services.templates import get_whatsapp_template
            
            # TODO: Implémenter l'intégration WhatsApp Business API
            
            delivery.status = DeliveryStatus.SENDING
            delivery.save(update_fields=["status"])
            delivery.add_log("Début de l'envoi WhatsApp", "INFO")
            
            # Générer le message
            message = get_whatsapp_template(
                recipient_name=delivery.recipient_name,
                order=delivery.order,
                etickets=[delivery.eticket],
            )
            
            # TODO: Intégrer l'API WhatsApp Business
            response = send_simple_text(
                phone=delivery.recipient_phone,
                text=message
            )
            
            logger.info(
                f"Message WhatsApp préparé pour {delivery.recipient_phone}: "
                f"{message[:50]}..."
            )
            
            delivery.add_log(
                "Service WhatsApp non encore implémenté - Message prêt",
                "WARNING"
            )
            
            # Ne pas marquer comme envoyé car pas vraiment envoyé
            delivery.mark_as_failed(
                "Service WhatsApp pas encore implémenté",
                schedule_retry=False
            )
            
            return False
            
        except Exception as e:
            error_message = f"Erreur WhatsApp: {str(e)}"
            logger.exception(error_message)
            delivery.mark_as_failed(error_message, schedule_retry=False)
            return False
    
    @staticmethod
    def process_delivery(delivery) -> bool:
        """
        Traite une tâche d'envoi selon son canal.
        
        Args:
            delivery: Instance TicketDelivery
        
        Returns:
            True si envoi réussi, False sinon
        """
        from apps.events.models.ticket_delivery import DeliveryChannel
        
        if delivery.channel == DeliveryChannel.EMAIL:
            return TicketDeliveryService.send_ticket_by_email(delivery)
        elif delivery.channel == DeliveryChannel.WHATSAPP:
            return TicketDeliveryService.send_ticket_by_whatsapp(delivery)
        else:
            logger.warning(f"Canal d'envoi non supporté: {delivery.channel}")
            return False
    
    @staticmethod
    def process_pending_retries():
        """
        Traite tous les envois en attente de retry.
        À appeler depuis une tâche Celery périodique.
        """
        from apps.events.models.ticket_delivery import TicketDelivery
        
        pending_retries = TicketDelivery.get_pending_retries()
        
        logger.info(f"Traitement de {pending_retries.count()} retry(s) en attente")
        
        success_count = 0
        fail_count = 0
        
        for delivery in pending_retries:
            delivery.add_log(f"Tentative de retry #{delivery.retry_count + 1}", "INFO")
            
            if TicketDeliveryService.process_delivery(delivery):
                success_count += 1
            else:
                fail_count += 1
        
        logger.info(
            f"Retry terminé: {success_count} succès, {fail_count} échecs"
        )
        
        return success_count, fail_count


def send_tickets_for_order(order, etickets: List) -> Dict[str, int]:
    """
    Fonction principale pour envoyer tous les tickets d'une commande.
    
    Args:
        order: Instance de Order
        etickets: Liste des ETickets à envoyer
    
    Returns:
        Dict avec les stats d'envoi: {"sent": X, "failed": Y, "pending": Z}
    """
    # Créer les tâches d'envoi
    deliveries = TicketDeliveryService.create_delivery_tasks(order, etickets)
    
    # Traiter immédiatement les envois
    stats = {"sent": 0, "failed": 0, "pending": 0}
    
    for delivery in deliveries:
        if TicketDeliveryService.process_delivery(delivery):
            stats["sent"] += 1
        else:
            if delivery.can_retry():
                stats["pending"] += 1
            else:
                stats["failed"] += 1
    
    logger.info(
        f"Envoi terminé pour commande {order.order_id}: "
        f"{stats['sent']} envoyés, {stats['failed']} échoués, "
        f"{stats['pending']} en attente de retry"
    )
    
    return stats