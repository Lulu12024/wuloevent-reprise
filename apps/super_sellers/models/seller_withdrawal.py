# -*- coding: utf-8 -*-
"""
   
Modèle pour gérer les demandes de retrait des vendeurs et super-vendeurs.
"""

import logging
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from commons.models import AbstractCommonBaseModel
from django.db import models, transaction
logger = logging.getLogger(__name__)


class WithdrawalMethod(models.TextChoices):
    """Méthodes de retrait disponibles"""
    MOBILE_MONEY_MTN = "MOBILE_MONEY_MTN", "Mobile Money MTN"
    MOBILE_MONEY_MOOV = "MOBILE_MONEY_MOOV", "Mobile Money MOOV"
    BANK_TRANSFER = "BANK_TRANSFER", "Virement bancaire"


class WithdrawalStatus(models.TextChoices):
    """États d'une demande de retrait"""
    PENDING = "PENDING", "En attente"
    APPROVED = "APPROVED", "Approuvé"
    PROCESSING = "PROCESSING", "En cours de traitement"
    COMPLETED = "COMPLETED", "Terminé"
    FAILED = "FAILED", "Échoué"
    CANCELLED = "CANCELLED", "Annulé"
    REJECTED = "REJECTED", "Rejeté"


class SellerWithdrawal(AbstractCommonBaseModel):
    """
    Demande de retrait d'un vendeur.
    Gère tout le workflow de la demande au paiement final.
    """
    
    # Relation avec le vendeur
    seller = models.ForeignKey(
        to="events.Seller",
        verbose_name="Vendeur",
        related_name="withdrawals",
        on_delete=models.SET_NULL,
        null=True,
    )
    
    # Montant
    amount = models.DecimalField(
        verbose_name="Montant demandé",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("1000.00"))],
        help_text="Montant minimum: 1000 F CFA"
    )
    
    fees = models.DecimalField(
        verbose_name="Frais de traitement",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Frais facturés pour ce retrait"
    )
    
    net_amount = models.DecimalField(
        verbose_name="Montant net à recevoir",
        max_digits=12,
        decimal_places=2,
        help_text="Montant après déduction des frais"
    )
    
    # Méthode de paiement
    method = models.CharField(
        max_length=30,
        choices=WithdrawalMethod.choices,
        verbose_name="Méthode de retrait",
    )
    
    # Détails du paiement
    payment_phone = models.CharField(
        max_length=20,
        verbose_name="Numéro de téléphone",
        blank=True,
        null=True,
        help_text="Pour Mobile Money uniquement"
    )
    
    bank_account_name = models.CharField(
        max_length=255,
        verbose_name="Nom du compte bancaire",
        blank=True,
        null=True,
    )
    
    bank_account_number = models.CharField(
        max_length=50,
        verbose_name="Numéro de compte bancaire",
        blank=True,
        null=True,
    )
    
    bank_name = models.CharField(
        max_length=100,
        verbose_name="Nom de la banque",
        blank=True,
        null=True,
    )
    
    # Statut et workflow
    status = models.CharField(
        max_length=20,
        choices=WithdrawalStatus.choices,
        default=WithdrawalStatus.PENDING,
        verbose_name="Statut",
    )
    
    # Dates importantes
    requested_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Demandé le",
    )
    
    approved_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Approuvé le",
    )
    
    processed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Traité le",
    )
    
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Complété le",
    )
    
    # Approbation/Rejet
    approved_by = models.ForeignKey(
        to="users.User",
        verbose_name="Approuvé par",
        related_name="approved_withdrawals",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    
    rejection_reason = models.TextField(
        verbose_name="Raison du rejet",
        blank=True,
        null=True,
    )
    
    # Gestion des erreurs et retry
    retry_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Nombre de tentatives",
    )
    
    max_retry_count = models.PositiveIntegerField(
        default=3,
        verbose_name="Nombre maximum de tentatives",
    )
    
    error_message = models.TextField(
        verbose_name="Message d'erreur",
        blank=True,
        null=True,
    )
    
    # Métadonnées et logs
    processing_logs = models.JSONField(
        default=list,
        verbose_name="Logs de traitement",
        help_text="Historique détaillé de toutes les tentatives"
    )
    
    provider_reference = models.CharField(
        max_length=255,
        verbose_name="Référence fournisseur",
        blank=True,
        null=True,
        help_text="Référence de transaction du provider (FedaPay, etc.)"
    )
    
    provider_response = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Réponse du fournisseur",
        help_text="Réponse complète de l'API de paiement"
    )
    
    notes = models.TextField(
        verbose_name="Notes",
        blank=True,
        null=True,
        help_text="Notes internes administratives"
    )
    
    class Meta:
        verbose_name = "Demande de retrait vendeur"
        verbose_name_plural = "Demandes de retrait vendeurs"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["seller", "-requested_at"]),
            models.Index(fields=["status", "-requested_at"]),
            models.Index(fields=["method", "status"]),
            models.Index(fields=["provider_reference"]),
        ]
    
    def __str__(self):
        return (
            f"Retrait de {self.amount} F CFA - "
            f"{self.seller.user.get_full_name()} - "
            f"{self.get_status_display()}"
        )
    
    @transaction.atomic
    def save(self, *args, **kwargs):
        """Calcule automatiquement le net_amount si pas défini"""
        if not self.net_amount:
            self.net_amount = self.amount - self.fees
        super().save(*args, **kwargs)
    
    def add_log(self, message: str, level: str = "INFO"):
        """Ajoute une entrée dans les logs de traitement"""
        log_entry = {
            "timestamp": timezone.now().isoformat(),
            "level": level,
            "message": message,
            "status": self.status,
            "retry_count": self.retry_count,
        }
        self.processing_logs.append(log_entry)
        self.save(update_fields=["processing_logs"])
    
    @transaction.atomic
    def approve(self, approved_by):
        """Approuve la demande de retrait"""
        if self.status != WithdrawalStatus.PENDING:
            raise ValueError(f"Impossible d'approuver un retrait avec le statut {self.status}")
        
        self.status = WithdrawalStatus.APPROVED
        self.approved_by = approved_by
        self.approved_at = timezone.now()
        self.add_log(f"Retrait approuvé par {approved_by.get_full_name()}", "INFO")
        self.save(update_fields=["status", "approved_by", "approved_at"])
        
        logger.info(f"Retrait {self.pk} approuvé par {approved_by.email}")
    
    def reject(self, reason: str, rejected_by):
        """Rejette la demande de retrait"""
        if self.status != WithdrawalStatus.PENDING:
            raise ValueError(f"Impossible de rejeter un retrait avec le statut {self.status}")
        
        self.status = WithdrawalStatus.REJECTED
        self.rejection_reason = reason
        self.add_log(f"Retrait rejeté par {rejected_by.get_full_name()}: {reason}", "WARNING")
        self.save(update_fields=["status", "rejection_reason"])
        
        # Libérer le montant réservé dans le wallet
        wallet = self.seller.wallet
        wallet.release_pending(self.amount)
        
        logger.info(f"Retrait {self.pk} rejeté: {reason}")
    
    def mark_as_processing(self):
        """Marque le retrait comme en cours de traitement"""
        if self.status != WithdrawalStatus.APPROVED:
            raise ValueError("Seuls les retraits approuvés peuvent être traités")
        
        self.status = WithdrawalStatus.PROCESSING
        self.processed_at = timezone.now()
        self.add_log("Début du traitement du retrait", "INFO")
        self.save(update_fields=["status", "processed_at"])
    
    def mark_as_completed(self, provider_reference: str = None, provider_response: dict = None):
        """Marque le retrait comme complété avec succès"""
        self.status = WithdrawalStatus.COMPLETED
        self.completed_at = timezone.now()
        
        if provider_reference:
            self.provider_reference = provider_reference
        if provider_response:
            self.provider_response = provider_response
        
        self.add_log("Retrait complété avec succès", "SUCCESS")
        self.save(update_fields=[
            "status", "completed_at", 
            "provider_reference", "provider_response"
        ])
        
        # Confirmer dans le wallet
        wallet = self.seller.wallet
        wallet.confirm_withdrawal(self.amount)
        
        # Créer une transaction wallet
        wallet.debit(
            amount=self.amount,
            transaction_type="WITHDRAWAL",
            reference=str(self.pk),
            metadata={
                "method": self.method,
                "provider_reference": provider_reference,
            }
        )
        
        logger.info(f"Retrait {self.pk} complété avec succès")
    
    def mark_as_failed(self, error_message: str, schedule_retry: bool = True):
        """Marque le retrait comme échoué"""
        self.error_message = error_message
        self.retry_count += 1
        
        self.add_log(f"Échec: {error_message}", "ERROR")
        
        # Programmer un retry si possible
        if schedule_retry and self.retry_count < self.max_retry_count:
            self.status = WithdrawalStatus.APPROVED  # Retour à approuvé pour retry
            self.add_log(
                f"Retry #{self.retry_count} programmé ({self.retry_count}/{self.max_retry_count})",
                "INFO"
            )
        else:
            self.status = WithdrawalStatus.FAILED
            self.add_log("Échec définitif (max retries atteint)", "ERROR")
            
            # Libérer le montant dans le wallet
            wallet = self.seller.wallet
            wallet.release_pending(self.amount)
        
        self.save(update_fields=["status", "error_message", "retry_count"])
        
        logger.error(f"Retrait {self.pk} échoué: {error_message}")
    
    def cancel(self, reason: str = None):
        """Annule une demande de retrait"""
        if self.status in [WithdrawalStatus.COMPLETED, WithdrawalStatus.PROCESSING]:
            raise ValueError("Impossible d'annuler un retrait complété ou en cours")
        
        self.status = WithdrawalStatus.CANCELLED
        if reason:
            self.notes = f"Annulé: {reason}"
        
        self.add_log(f"Retrait annulé: {reason or 'Pas de raison'}", "WARNING")
        self.save(update_fields=["status", "notes"])
        
        # Libérer le montant dans le wallet
        wallet = self.seller.wallet
        wallet.release_pending(self.amount)
        
        logger.info(f"Retrait {self.pk} annulé")
    
    def can_retry(self) -> bool:
        """Vérifie si un retry est possible"""
        return (
            self.status == WithdrawalStatus.APPROVED
            and self.retry_count < self.max_retry_count
        )
    
    def is_mobile_money(self) -> bool:
        """Vérifie si c'est un retrait Mobile Money"""
        return self.method in [
            WithdrawalMethod.MOBILE_MONEY_MTN,
            WithdrawalMethod.MOBILE_MONEY_MOOV,
        ]
    
    def is_bank_transfer(self) -> bool:
        """Vérifie si c'est un virement bancaire"""
        return self.method == WithdrawalMethod.BANK_TRANSFER
    
    @classmethod
    def get_pending_for_approval(cls):
        """Récupère tous les retraits en attente d'approbation"""
        return cls.objects.filter(status=WithdrawalStatus.PENDING).select_related("seller", "seller__user")
    
    @classmethod
    def get_approved_for_processing(cls):
        """Récupère tous les retraits approuvés prêts à être traités"""
        return cls.objects.filter(status=WithdrawalStatus.APPROVED).select_related("seller", "seller__wallet")