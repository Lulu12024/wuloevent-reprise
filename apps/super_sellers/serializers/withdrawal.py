# -*- coding: utf-8 -*-
"""

Serializers pour les demandes de retrait des vendeurs.
"""

import logging
from decimal import Decimal
from rest_framework import serializers
from apps.super_sellers.models.seller_withdrawal import (
    SellerWithdrawal,
    WithdrawalMethod,
    WithdrawalStatus
)
from apps.super_sellers.services.withdrawal import SellerWithdrawalService

logger = logging.getLogger(__name__)


class WithdrawalCreateSerializer(serializers.Serializer):
    """
    Serializer pour créer une demande de retrait.
    POST /api/withdrawals/request
    """
    
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("1000.00"),
        help_text="Montant à retirer (minimum 1000 F CFA)"
    )
    
    method = serializers.ChoiceField(
        choices=WithdrawalMethod.choices,
        help_text="Méthode de retrait"
    )
    
    # Pour Mobile Money
    payment_phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        help_text="Numéro de téléphone pour Mobile Money"
    )
    
    # Pour virement bancaire
    bank_account_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Nom du titulaire du compte"
    )
    
    bank_account_number = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        help_text="Numéro de compte bancaire"
    )
    
    bank_name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text="Nom de la banque"
    )
    
    def validate_amount(self, value):
        """Valider le montant minimum"""
        min_amount = SellerWithdrawalService.MIN_WITHDRAWAL_AMOUNT
        if value < min_amount:
            raise serializers.ValidationError(
                f"Le montant minimum de retrait est {min_amount} F CFA"
            )
        return value
    
    def validate(self, attrs):
        """Validation globale selon la méthode choisie"""
        method = attrs.get("method")
        
        # Validation pour Mobile Money
        if method in [WithdrawalMethod.MOBILE_MONEY_MTN, WithdrawalMethod.MOBILE_MONEY_MOOV]:
            if not attrs.get("payment_phone"):
                raise serializers.ValidationError({
                    "payment_phone": "Le numéro de téléphone est requis pour Mobile Money"
                })
        
        # Validation pour virement bancaire
        elif method == WithdrawalMethod.BANK_TRANSFER:
            required_fields = ["bank_account_name", "bank_account_number", "bank_name"]
            missing_fields = [
                field for field in required_fields
                if not attrs.get(field)
            ]
            
            if missing_fields:
                raise serializers.ValidationError({
                    field: "Ce champ est requis pour un virement bancaire"
                    for field in missing_fields
                })
        
        return attrs
    
    def create(self, validated_data):
        """Créer la demande de retrait via le service"""
        seller = self.context["request"].seller
        
        payment_details = {
            "payment_phone": validated_data.get("payment_phone"),
            "bank_account_name": validated_data.get("bank_account_name"),
            "bank_account_number": validated_data.get("bank_account_number"),
            "bank_name": validated_data.get("bank_name"),
        }
        
        withdrawal = SellerWithdrawalService.create_withdrawal_request(
            seller=seller,
            amount=validated_data["amount"],
            method=validated_data["method"],
            payment_details=payment_details
        )
        
        return withdrawal


class WithdrawalSerializer(serializers.ModelSerializer):
    """
    Serializer pour lister les demandes de retrait.
    GET /api/withdrawals
    """
    
    seller_name = serializers.CharField(
        source="seller.user.get_full_name",
        read_only=True
    )
    
    method_display = serializers.CharField(
        source="get_method_display",
        read_only=True
    )
    
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True
    )
    
    can_cancel = serializers.SerializerMethodField()
    can_retry = serializers.SerializerMethodField()
    
    class Meta:
        model = SellerWithdrawal
        fields = (
            "pk",
            "seller_name",
            "amount",
            "fees",
            "net_amount",
            "method",
            "method_display",
            "status",
            "status_display",
            "requested_at",
            "approved_at",
            "processed_at",
            "completed_at",
            "retry_count",
            "max_retry_count",
            "can_cancel",
            "can_retry",
        )
        read_only_fields = fields
    
    def get_can_cancel(self, obj) -> bool:
        """Indique si le retrait peut être annulé"""
        return obj.status in [
            WithdrawalStatus.PENDING,
            WithdrawalStatus.APPROVED,
        ]
    
    def get_can_retry(self, obj) -> bool:
        """Indique si un retry est possible"""
        return obj.can_retry()


class WithdrawalDetailSerializer(serializers.ModelSerializer):
    """
    Serializer détaillé pour une demande de retrait.
    GET /api/withdrawals/{id}
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
    
    method_display = serializers.CharField(
        source="get_method_display",
        read_only=True
    )
    
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True
    )
    
    approved_by_name = serializers.SerializerMethodField()
    
    can_cancel = serializers.SerializerMethodField()
    can_retry = serializers.SerializerMethodField()
    
    # Détails conditionnels selon la méthode
    payment_details = serializers.SerializerMethodField()
    
    class Meta:
        model = SellerWithdrawal
        fields = (
            "pk",
            "seller_id",
            "seller_name",
            "seller_email",
            "amount",
            "fees",
            "net_amount",
            "method",
            "method_display",
            "payment_details",
            "status",
            "status_display",
            "requested_at",
            "approved_at",
            "approved_by_name",
            "processed_at",
            "completed_at",
            "rejection_reason",
            "retry_count",
            "max_retry_count",
            "error_message",
            "processing_logs",
            "provider_reference",
            "notes",
            "can_cancel",
            "can_retry",
            "timestamp",
            "updated",
        )
        read_only_fields = fields
    
    def get_approved_by_name(self, obj) -> str:
        """Nom de l'approbateur"""
        if obj.approved_by:
            return obj.approved_by.get_full_name()
        return None
    
    def get_can_cancel(self, obj) -> bool:
        """Indique si le retrait peut être annulé"""
        return obj.status in [
            WithdrawalStatus.PENDING,
            WithdrawalStatus.APPROVED,
        ]
    
    def get_can_retry(self, obj) -> bool:
        """Indique si un retry est possible"""
        return obj.can_retry()
    
    def get_payment_details(self, obj) -> dict:
        """Retourne les détails de paiement selon la méthode"""
        if obj.is_mobile_money():
            return {
                "type": "mobile_money",
                "phone": obj.payment_phone,
            }
        elif obj.is_bank_transfer():
            return {
                "type": "bank_transfer",
                "account_name": obj.bank_account_name,
                "account_number": obj.bank_account_number,
                "bank_name": obj.bank_name,
            }
        return {}


class WithdrawalApprovalSerializer(serializers.Serializer):
    """
    Serializer pour approuver une demande de retrait.
    PATCH /api/withdrawals/{id}/approve
    """
    
    notes = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Notes administratives (optionnel)"
    )


class WithdrawalRejectionSerializer(serializers.Serializer):
    """
    Serializer pour rejeter une demande de retrait.
    PATCH /api/withdrawals/{id}/reject
    """
    
    reason = serializers.CharField(
        max_length=500,
        help_text="Raison du rejet"
    )
    
    def validate_reason(self, value):
        """Valider que la raison est fournie"""
        if not value or not value.strip():
            raise serializers.ValidationError(
                "Une raison doit être fournie pour le rejet"
            )
        return value.strip()


class WithdrawalCancelSerializer(serializers.Serializer):
    """
    Serializer pour annuler une demande de retrait.
    PATCH /api/withdrawals/{id}/cancel
    """
    
    reason = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Raison de l'annulation (optionnel)"
    )


class WithdrawalProcessSerializer(serializers.Serializer):
    """
    Serializer pour marquer un retrait comme complété manuellement (virement bancaire).
    PATCH /api/withdrawals/{id}/complete
    """
    
    provider_reference = serializers.CharField(
        max_length=255,
        help_text="Référence de la transaction (numéro de virement, etc.)"
    )
    
    notes = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Notes administratives (optionnel)"
    )
    
    def validate_provider_reference(self, value):
        """Valider que la référence est fournie"""
        if not value or not value.strip():
            raise serializers.ValidationError(
                "La référence de transaction doit être fournie"
            )
        return value.strip()


class WithdrawalStatsSerializer(serializers.Serializer):
    """
    Serializer pour les statistiques de retraits.
    GET /api/withdrawals/stats
    """
    
    total_requested = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_completed = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_pending = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_failed = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    count_total = serializers.IntegerField()
    count_pending = serializers.IntegerField()
    count_approved = serializers.IntegerField()
    count_processing = serializers.IntegerField()
    count_completed = serializers.IntegerField()
    count_failed = serializers.IntegerField()
    count_cancelled = serializers.IntegerField()
    count_rejected = serializers.IntegerField()
    
    # Par méthode
    mobile_money_count = serializers.IntegerField(required=False)
    bank_transfer_count = serializers.IntegerField(required=False)