# -*- coding: utf-8 -*-
"""

Serializers pour les wallets et transactions des vendeurs.
"""

import logging
from rest_framework import serializers
from apps.super_sellers.models.seller_wallet import (
    SellerWallet,
    WalletTransaction,
    WalletTransactionType
)

logger = logging.getLogger(__name__)


class WalletTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer pour les transactions du wallet.
    Utilisé pour afficher l'historique des transactions.
    """
    
    transaction_type_display = serializers.CharField(
        source="get_transaction_type_display",
        read_only=True
    )
    
    is_credit = serializers.SerializerMethodField()
    is_debit = serializers.SerializerMethodField()
    
    class Meta:
        model = WalletTransaction
        fields = (
            "pk",
            "transaction_type",
            "transaction_type_display",
            "amount",
            "balance_after",
            "reference",
            "metadata",
            "is_credit",
            "is_debit",
            "timestamp",
        )
        read_only_fields = fields
    
    def get_is_credit(self, obj) -> bool:
        """Indique si c'est un crédit"""
        return obj.is_credit()
    
    def get_is_debit(self, obj) -> bool:
        """Indique si c'est un débit"""
        return obj.is_debit()


class WalletBalanceSerializer(serializers.ModelSerializer):
    """
    Serializer simple pour consulter le solde du wallet.
    Utilisé pour l'endpoint GET /api/wallet/balance
    """
    
    seller_name = serializers.CharField(
        source="seller.user.get_full_name",
        read_only=True
    )
    
    total_balance = serializers.SerializerMethodField()
    
    class Meta:
        model = SellerWallet
        fields = (
            "pk",
            "seller_name",
            "balance",
            "pending_balance",
            "total_balance",
            "total_earned",
            "total_withdrawn",
            "last_transaction_at",
        )
        read_only_fields = fields
    
    def get_total_balance(self, obj) -> str:
        """Retourne le solde total (disponible + pending)"""
        return str(obj.get_total_balance())


class WalletSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour le wallet avec informations du vendeur.
    """
    
    seller_id = serializers.UUIDField(source="seller.pk", read_only=True)
    seller_name = serializers.CharField(
        source="seller.user.get_full_name",
        read_only=True
    )
    seller_email = serializers.EmailField(
        source="seller.user.email",
        read_only=True
    )
    
    total_balance = serializers.SerializerMethodField()
    transaction_count = serializers.SerializerMethodField()
    can_withdraw = serializers.SerializerMethodField()
    
    # Dernières transactions (optionnel)
    recent_transactions = serializers.SerializerMethodField()
    
    class Meta:
        model = SellerWallet
        fields = (
            "pk",
            "seller_id",
            "seller_name",
            "seller_email",
            "balance",
            "pending_balance",
            "total_balance",
            "total_earned",
            "total_withdrawn",
            "last_transaction_at",
            "transaction_count",
            "can_withdraw",
            "recent_transactions",
            "timestamp",
            "updated",
        )
        read_only_fields = fields
    
    def get_total_balance(self, obj) -> str:
        """Solde total (disponible + pending)"""
        return str(obj.get_total_balance())
    
    def get_transaction_count(self, obj) -> int:
        """Nombre total de transactions"""
        return obj.transactions.count()
    
    def get_can_withdraw(self, obj) -> bool:
        """Indique si le vendeur peut faire un retrait"""
        # Montant minimum de retrait
        from apps.super_sellers.services.withdrawal import SellerWithdrawalService
        min_amount = SellerWithdrawalService.MIN_WITHDRAWAL_AMOUNT
        return obj.balance >= min_amount
    
    def get_recent_transactions(self, obj):
        """Retourne les 5 dernières transactions"""
        # Seulement si demandé dans le contexte
        if self.context.get("include_recent_transactions"):
            recent = obj.transactions.all()[:5]
            return WalletTransactionSerializer(recent, many=True).data
        return None


class WalletStatsSerializer(serializers.Serializer):
    """
    Serializer pour les statistiques complètes du wallet.
    Utilisé pour l'endpoint GET /api/wallet/stats
    """
    
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_earned = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_withdrawn = serializers.DecimalField(max_digits=12, decimal_places=2)
    last_transaction_at = serializers.DateTimeField(allow_null=True)
    transaction_count = serializers.IntegerField()
    
    # Stats par type de transaction
    sales_count = serializers.IntegerField(required=False)
    commission_count = serializers.IntegerField(required=False)
    withdrawal_count = serializers.IntegerField(required=False)
    
    total_sales_amount = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        required=False
    )
    total_commission_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False
    )


class WalletAdjustmentSerializer(serializers.Serializer):
    """
    Serializer pour les ajustements manuels du wallet (admin uniquement).
    """
    
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Montant de l'ajustement (positif ou négatif)"
    )
    
    reason = serializers.CharField(
        max_length=500,
        help_text="Raison de l'ajustement"
    )
    
    def validate_amount(self, value):
        """Valider que le montant n'est pas 0"""
        if value == 0:
            raise serializers.ValidationError(
                "Le montant de l'ajustement ne peut pas être 0"
            )
        return value
    
    def validate_reason(self, value):
        """Valider que la raison est fournie"""
        if not value or not value.strip():
            raise serializers.ValidationError(
                "Une raison doit être fournie pour l'ajustement"
            )
        return value.strip()