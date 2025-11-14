# -*- coding: utf-8 -*-
"""

Modèle pour gérer les soldes (wallets) des vendeurs et super-vendeurs.
"""

import logging
from decimal import Decimal
from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.utils import timezone
from commons.models import AbstractCommonBaseModel

logger = logging.getLogger(__name__)


class WalletTransactionType(models.TextChoices):
    """Types de transactions wallet"""
    SALE = "SALE", "Vente de ticket"
    COMMISSION = "COMMISSION", "Commission"
    WITHDRAWAL = "WITHDRAWAL", "Retrait"
    REFUND = "REFUND", "Remboursement"
    ADJUSTMENT = "ADJUSTMENT", "Ajustement manuel"
    BONUS = "BONUS", "Bonus"


class SellerWallet(AbstractCommonBaseModel):
    """
    Wallet pour gérer les soldes des vendeurs.
    Chaque vendeur a un wallet unique.
    """
    
    # Relation avec le vendeur
    seller = models.OneToOneField(
        to="events.Seller",
        verbose_name="Vendeur",
        related_name="wallet",
        on_delete=models.CASCADE,
    )
    
    # Soldes
    balance = models.DecimalField(
        verbose_name="Solde disponible",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Solde actuel disponible pour retrait"
    )
    
    pending_balance = models.DecimalField(
        verbose_name="Solde en attente",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Solde en attente de traitement (retraits en cours)"
    )
    
    total_earned = models.DecimalField(
        verbose_name="Total gagné",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total cumulé de tous les gains (historique)"
    )
    
    total_withdrawn = models.DecimalField(
        verbose_name="Total retiré",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total cumulé de tous les retraits effectués"
    )
    
    # Métadonnées
    last_transaction_at = models.DateTimeField(
        verbose_name="Dernière transaction",
        blank=True,
        null=True,
    )
    
    class Meta:
        verbose_name = "Portefeuille vendeur"
        verbose_name_plural = "Portefeuilles vendeurs"
        indexes = [
            models.Index(fields=["seller", "-timestamp"]),
            models.Index(fields=["balance"]),
        ]
    
    def __str__(self):
        return f"Wallet de {self.seller.user.get_full_name()} - {self.balance} F CFA"
    
    @transaction.atomic
    def credit(self, amount: Decimal, transaction_type: str, 
               reference: str = None, metadata: dict = None):
        """
        Crédite le wallet et crée une transaction.
        
        Args:
            amount: Montant à créditer (doit être > 0)
            transaction_type: Type de transaction (WalletTransactionType)
            reference: Référence externe (order_id, etc.)
            metadata: Métadonnées supplémentaires
        
        Returns:
            WalletTransaction créée
        """
        if amount <= 0:
            raise ValueError("Le montant doit être supérieur à 0")
        
        # Mettre à jour le solde
        self.balance += amount
        self.total_earned += amount
        self.last_transaction_at = timezone.now()
        self.save(update_fields=["balance", "total_earned", "last_transaction_at"])
        
        # Créer la transaction
        wallet_transaction = WalletTransaction.objects.create(
            wallet=self,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=self.balance,
            reference=reference or "",
            metadata=metadata or {},
        )
        
        logger.info(
            f"Wallet {self.seller.pk} crédité de {amount} F CFA "
            f"(type: {transaction_type}, nouveau solde: {self.balance})"
        )
        
        return wallet_transaction
    
    @transaction.atomic
    def debit(self, amount: Decimal, transaction_type: str,
              reference: str = None, metadata: dict = None):
        """
        Débite le wallet et crée une transaction.
        
        Args:
            amount: Montant à débiter (doit être > 0)
            transaction_type: Type de transaction (WalletTransactionType)
            reference: Référence externe
            metadata: Métadonnées supplémentaires
        
        Returns:
            WalletTransaction créée
        
        Raises:
            ValueError si solde insuffisant
        """
        if amount <= 0:
            raise ValueError("Le montant doit être supérieur à 0")
        
        if self.balance < amount:
            raise ValueError(
                f"Solde insuffisant. Disponible: {self.balance} F CFA, "
                f"Demandé: {amount} F CFA"
            )
        
        # Mettre à jour le solde
        self.balance -= amount
        self.last_transaction_at = timezone.now()
        
        if transaction_type == WalletTransactionType.WITHDRAWAL:
            self.total_withdrawn += amount
            self.save(update_fields=["balance", "total_withdrawn", "last_transaction_at"])
        else:
            self.save(update_fields=["balance", "last_transaction_at"])
        
        # Créer la transaction
        wallet_transaction = WalletTransaction.objects.create(
            wallet=self,
            transaction_type=transaction_type,
            amount=-amount,  # Négatif pour débit
            balance_after=self.balance,
            reference=reference or "",
            metadata=metadata or {},
        )
        
        logger.info(
            f"Wallet {self.seller.pk} débité de {amount} F CFA "
            f"(type: {transaction_type}, nouveau solde: {self.balance})"
        )
        
        return wallet_transaction
    
    @transaction.atomic
    def reserve_for_withdrawal(self, amount: Decimal):
        """
        Réserve un montant pour un retrait en cours.
        Le montant passe du balance au pending_balance.
        """
        if self.balance < amount:
            raise ValueError("Solde insuffisant pour réserver ce montant")
        
        self.balance -= amount
        self.pending_balance += amount
        self.save(update_fields=["balance", "pending_balance"])
        
        logger.info(
            f"Wallet {self.seller.pk}: {amount} F CFA réservé pour retrait "
            f"(balance: {self.balance}, pending: {self.pending_balance})"
        )
    
    @transaction.atomic
    def release_pending(self, amount: Decimal):
        """
        Libère un montant du pending_balance vers le balance.
        Utilisé en cas d'échec de retrait.
        """
        if self.pending_balance < amount:
            raise ValueError("Montant pending insuffisant")
        
        self.pending_balance -= amount
        self.balance += amount
        self.save(update_fields=["balance", "pending_balance"])
        
        logger.info(
            f"Wallet {self.seller.pk}: {amount} F CFA libéré du pending "
            f"(balance: {self.balance}, pending: {self.pending_balance})"
        )
    
    @transaction.atomic
    def confirm_withdrawal(self, amount: Decimal):
        """
        Confirme un retrait en diminuant le pending_balance.
        Le montant sort définitivement du wallet.
        """
        if self.pending_balance < amount:
            raise ValueError("Montant pending insuffisant")
        
        self.pending_balance -= amount
        self.total_withdrawn += amount
        self.save(update_fields=["pending_balance", "total_withdrawn"])
        
        logger.info(
            f"Wallet {self.seller.pk}: retrait de {amount} F CFA confirmé "
            f"(pending: {self.pending_balance}, total retiré: {self.total_withdrawn})"
        )
    
    def can_withdraw(self, amount: Decimal) -> bool:
        """Vérifie si un retrait est possible"""
        return self.balance >= amount
    
    def get_total_balance(self) -> Decimal:
        """Retourne le solde total (disponible + pending)"""
        return self.balance + self.pending_balance


class WalletTransaction(AbstractCommonBaseModel):
    """
    Historique de toutes les transactions d'un wallet.
    Permet la traçabilité complète.
    """
    
    wallet = models.ForeignKey(
        to=SellerWallet,
        verbose_name="Portefeuille",
        related_name="transactions",
        on_delete=models.CASCADE,
    )
    
    transaction_type = models.CharField(
        max_length=20,
        choices=WalletTransactionType.choices,
        verbose_name="Type de transaction",
    )
    
    amount = models.DecimalField(
        verbose_name="Montant",
        max_digits=12,
        decimal_places=2,
        help_text="Positif pour crédit, négatif pour débit"
    )
    
    balance_after = models.DecimalField(
        verbose_name="Solde après transaction",
        max_digits=12,
        decimal_places=2,
    )
    
    reference = models.CharField(
        max_length=255,
        verbose_name="Référence",
        blank=True,
        help_text="Référence externe (order_id, withdrawal_id, etc.)"
    )
    
    metadata = models.JSONField(
        default=dict,
        verbose_name="Métadonnées",
        help_text="Données supplémentaires (event_id, ticket_id, etc.)"
    )
    
    class Meta:
        verbose_name = "Transaction wallet"
        verbose_name_plural = "Transactions wallet"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["wallet", "-timestamp"]),
            models.Index(fields=["transaction_type", "-timestamp"]),
            models.Index(fields=["reference"]),
        ]
    
    def __str__(self):
        sign = "+" if self.amount >= 0 else ""
        return (
            f"{self.get_transaction_type_display()} - "
            f"{sign}{self.amount} F CFA - "
            f"Solde: {self.balance_after} F CFA"
        )
    
    def is_credit(self) -> bool:
        """Vérifie si c'est un crédit"""
        return self.amount > 0
    
    def is_debit(self) -> bool:
        """Vérifie si c'est un débit"""
        return self.amount < 0


# Helper pour créer automatiquement un wallet pour chaque vendeur
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.events.models.seller import Seller


@receiver(post_save, sender=Seller)
def create_seller_wallet(sender, instance, created, **kwargs):
    """Crée automatiquement un wallet pour chaque nouveau vendeur"""
    if created:
        SellerWallet.objects.get_or_create(seller=instance)
        logger.info(f"Wallet créé automatiquement pour le vendeur {instance.pk}")