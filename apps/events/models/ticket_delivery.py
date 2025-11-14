# -*- coding: utf-8 -*-
"""

Modèle pour gérer l'envoi de tickets avec retry automatique.
"""

import logging
from django.db import models
from django.utils import timezone
from commons.models import AbstractCommonBaseModel

logger = logging.getLogger(__name__)


class DeliveryStatus(models.TextChoices):
    """États possibles pour l'envoi d'un ticket"""
    PENDING = "PENDING", "En attente"
    SENDING = "SENDING", "En cours d'envoi"
    SENT = "SENT", "Envoyé avec succès"
    FAILED = "FAILED", "Échec"
    RETRY = "RETRY", "En attente de nouvel essai"


class DeliveryChannel(models.TextChoices):
    """Canaux d'envoi disponibles"""
    EMAIL = "EMAIL", "Email"
    WHATSAPP = "WHATSAPP", "WhatsApp"
    SMS = "SMS", "SMS"


class TicketDelivery(AbstractCommonBaseModel):
    """
    Modèle pour tracker tous les envois de tickets.
    Permet le retry automatique et le logging détaillé.
    """
    
    # Relation avec le ticket électronique
    eticket = models.ForeignKey(
        to="events.ETicket",
        verbose_name="E-Ticket",
        related_name="deliveries",
        on_delete=models.CASCADE,
    )
    
    # Relation avec la commande
    order = models.ForeignKey(
        to="events.Order",
        verbose_name="Commande",
        related_name="ticket_deliveries",
        on_delete=models.CASCADE,
    )
    
    # destinataire
    recipient_email = models.EmailField(
        verbose_name="Email destinataire",
        blank=True,
        null=True,
    )
    recipient_phone = models.CharField(
        max_length=20,
        verbose_name="Téléphone destinataire",
        blank=True,
        null=True,
    )
    recipient_name = models.CharField(
        max_length=255,
        verbose_name="Nom destinataire",
        blank=True,
        null=True,
    )
    
    # Canal d'envoi
    channel = models.CharField(
        max_length=20,
        choices=DeliveryChannel.choices,
        verbose_name="Canal d'envoi",
    )
    
    # État de l'envoi
    status = models.CharField(
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        verbose_name="État",
    )
    
    # Gestion des tentatives
    retry_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Nombre de tentatives",
    )
    max_retry_count = models.PositiveIntegerField(
        default=3,
        verbose_name="Nombre maximum de tentatives",
    )
    next_retry_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Prochaine tentative à",
    )
    
    # Dates importantes
    sent_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Envoyé le",
    )
    failed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Échoué le",
    )
    
    # Logging détaillé
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name="Message d'erreur",
    )
    delivery_logs = models.JSONField(
        default=list,
        verbose_name="Logs d'envoi",
        help_text="Historique détaillé de toutes les tentatives",
    )
    
    # Métadonnées
    provider_response = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Réponse du fournisseur",
        help_text="Réponse complète du service d'envoi (Courier, etc.)",
    )
    
    class Meta:
        verbose_name = "Envoi de ticket"
        verbose_name_plural = "Envois de tickets"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["status", "-timestamp"]),
            models.Index(fields=["channel", "status"]),
            models.Index(fields=["order", "-timestamp"]),
            models.Index(fields=["eticket"]),
            models.Index(fields=["next_retry_at"], name="idx_next_retry"),
        ]
    
    def __str__(self):
        return f"Envoi {self.channel} - {self.eticket.name} - {self.status}"
    
    def add_log(self, message: str, level: str = "INFO"):
        """Ajoute une entrée dans les logs d'envoi"""
        log_entry = {
            "timestamp": timezone.now().isoformat(),
            "level": level,
            "message": message,
            "retry_count": self.retry_count,
        }
        self.delivery_logs.append(log_entry)
        self.save(update_fields=["delivery_logs"])
    
    def mark_as_sent(self, provider_response=None):
        """Marque l'envoi comme réussi"""
        self.status = DeliveryStatus.SENT
        self.sent_at = timezone.now()
        if provider_response:
            self.provider_response = provider_response
        self.add_log("Envoi réussi", "SUCCESS")
        self.save(update_fields=["status", "sent_at", "provider_response"])
    
    def mark_as_failed(self, error_message: str, schedule_retry: bool = True):
        """Marque l'envoi comme échoué et programme un retry si possible"""
        self.status = DeliveryStatus.FAILED
        self.failed_at = timezone.now()
        self.error_message = error_message
        self.retry_count += 1
        
        self.add_log(f"Échec: {error_message}", "ERROR")
        
        # Programmer un retry si le max n'est pas atteint
        if schedule_retry and self.retry_count < self.max_retry_count:
            self.status = DeliveryStatus.RETRY
            # Délai exponentiel: 5min, 15min, 30min
            retry_delays = {1: 5, 2: 15, 3: 30}
            delay_minutes = retry_delays.get(self.retry_count, 30)
            self.next_retry_at = timezone.now() + timezone.timedelta(minutes=delay_minutes)
            self.add_log(f"Retry programmé dans {delay_minutes} minutes", "INFO")
        
        self.save(update_fields=[
            "status", "failed_at", "error_message", 
            "retry_count", "next_retry_at"
        ])
    
    def can_retry(self) -> bool:
        """Vérifie si un retry est possible"""
        return (
            self.status in [DeliveryStatus.FAILED, DeliveryStatus.RETRY]
            and self.retry_count < self.max_retry_count
            and (
                self.next_retry_at is None 
                or self.next_retry_at <= timezone.now()
            )
        )
    
    @classmethod
    def get_pending_retries(cls):
        """Récupère tous les envois en attente de retry"""
        now = timezone.now()
        return cls.objects.filter(
            status=DeliveryStatus.RETRY,
            next_retry_at__lte=now,
        ).select_related("eticket", "order")