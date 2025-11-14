# -*- coding: utf-8 -*-
"""

Service pour gérer automatiquement les soldes des vendeurs après chaque vente.
"""

import logging
from decimal import Decimal
from typing import Tuple
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from apps.super_sellers.models.seller_wallet import SellerWallet, WalletTransactionType
logger = logging.getLogger(__name__)


class SellerWalletService:
    """
    Service pour gérer les opérations de wallet des vendeurs.
    """
    
    # Configuration des commissions (peut être déplacé dans settings.py)
    SELLER_COMMISSION_RATE = Decimal("0.10")  # 10% de commission vendeur
    SUPER_SELLER_COMMISSION_RATE = Decimal("0.05")  # 5% de commission super-vendeur
    
    @staticmethod
    def get_commission_rates() -> Tuple[Decimal, Decimal]:
        """
        Récupère les taux de commission depuis les settings ou la DB.
        
        Returns:
            (seller_rate, super_seller_rate)
        """
        # Tenter de récupérer depuis les variables en DB
        try:
            from apps.utils.models import Variable, VariableValue
            from apps.xlib.enums import VARIABLE_NAMES_ENUM
            
            # Commission vendeur
            seller_var = Variable.objects.filter(
                name=VARIABLE_NAMES_ENUM.PERCENTAGE_ABOUT_A_TICKET_SELLING.value
            ).first()
            
            if seller_var:
                seller_rate = Decimal(seller_var.possible_values.first().value)
            else:
                seller_rate = SellerWalletService.SELLER_COMMISSION_RATE
            
            # Commission super-vendeur (peut être la même ou différente)
            super_seller_rate = SellerWalletService.SUPER_SELLER_COMMISSION_RATE
            
            return seller_rate, super_seller_rate
            
        except Exception as e:
            logger.warning(f"Impossible de récupérer les taux de commission depuis la DB: {e}")
            return (
                SellerWalletService.SELLER_COMMISSION_RATE,
                SellerWalletService.SUPER_SELLER_COMMISSION_RATE
            )
    
    @classmethod
    @transaction.atomic
    def process_sale_commission(
        cls,
        seller,
        order,
        sale_amount: Decimal,
        ticket_quantity: int,
    ):
        """
        Traite les commissions après une vente réussie.
        Crédite le wallet du vendeur avec sa commission.
        
        Args:
            seller: Instance de Seller
            order: Instance de Order
            sale_amount: Montant total de la vente
            ticket_quantity: Nombre de tickets vendus
        
        Returns:
            dict avec les détails de la commission
        """
        # Récupérer ou créer le wallet
        
        
        wallet, created = SellerWallet.objects.get_or_create(seller=seller)
        if created:
            logger.info(f"Wallet créé automatiquement pour le vendeur {seller.pk}")
        
        # Calculer la commission
        seller_rate, _ = cls.get_commission_rates()
        commission_amount = sale_amount * seller_rate
        
        # Créditer le wallet
        wallet_transaction = wallet.credit(
            amount=commission_amount,
            transaction_type=WalletTransactionType.COMMISSION,
            reference=order.order_id,
            metadata={
                "order_id": str(order.pk),
                "sale_amount": str(sale_amount),
                "commission_rate": str(seller_rate),
                "ticket_quantity": ticket_quantity,
                "event_id": str(order.item.ticket.event_id) if order.item and order.item.ticket else None,
            }
        )
        
        logger.info(
            f"Commission de {commission_amount} F CFA créditée au vendeur {seller.pk} "
            f"pour la vente {order.order_id}"
        )
        
        return {
            "commission_amount": commission_amount,
            "commission_rate": seller_rate,
            "new_balance": wallet.balance,
            "transaction_id": str(wallet_transaction.pk),
        }
    
    @classmethod
    @transaction.atomic
    def process_direct_sale_commission(
        cls,
        seller,
        sale_amount: Decimal,
        ticket_name: str,
        event_name: str,
        reference: str = None,
    ):
        """
        Traite une commission pour une vente directe (sans order Django).
        Utilisé pour les ventes via le système de vendeurs.
        
        Args:
            seller: Instance de Seller
            sale_amount: Montant de la vente
            ticket_name: Nom du ticket vendu
            event_name: Nom de l'événement
            reference: Référence externe
        
        Returns:
            dict avec les détails de la commission
        """
        
        wallet, _ = SellerWallet.objects.get_or_create(seller=seller)
        
        # Calculer la commission
        seller_rate, _ = cls.get_commission_rates()
        commission_amount = sale_amount * seller_rate
        
        # Créditer le wallet
        wallet_transaction = wallet.credit(
            amount=commission_amount,
            transaction_type=WalletTransactionType.SALE,
            reference=reference or f"SALE-{timezone.now().strftime('%Y%m%d%H%M%S')}",
            metadata={
                "sale_amount": str(sale_amount),
                "commission_rate": str(seller_rate),
                "ticket_name": ticket_name,
                "event_name": event_name,
            }
        )
        
        logger.info(
            f"Commission directe de {commission_amount} F CFA créditée au vendeur {seller.pk}"
        )
        
        return {
            "commission_amount": commission_amount,
            "commission_rate": seller_rate,
            "new_balance": wallet.balance,
            "transaction_id": str(wallet_transaction.pk),
        }
    
    @staticmethod
    def get_wallet_balance(seller) -> Decimal:
        """
        Récupère le solde du wallet d'un vendeur.
        Crée le wallet s'il n'existe pas.
        
        Args:
            seller: Instance de Seller
        
        Returns:
            Balance actuel
        """
        
        wallet, _ = SellerWallet.objects.get_or_create(seller=seller)
        return wallet.balance
    
    @staticmethod
    def get_wallet_stats(seller) -> dict:
        """
        Récupère les statistiques complètes du wallet.
        
        Args:
            seller: Instance de Seller
        
        Returns:
            dict avec toutes les stats
        """
        
        wallet, _ = SellerWallet.objects.get_or_create(seller=seller)
        
        return {
            "balance": wallet.balance,
            "pending_balance": wallet.pending_balance,
            "total_balance": wallet.get_total_balance(),
            "total_earned": wallet.total_earned,
            "total_withdrawn": wallet.total_withdrawn,
            "last_transaction_at": wallet.last_transaction_at,
            "transaction_count": wallet.transactions.count(),
        }
    
    @staticmethod
    @transaction.atomic
    def adjust_wallet(seller, amount: Decimal, reason: str, admin_user):
        """
        Ajustement manuel du wallet (par un admin).
        
        Args:
            seller: Instance de Seller
            amount: Montant (positif ou négatif)
            reason: Raison de l'ajustement
            admin_user: Utilisateur admin effectuant l'ajustement
        
        Returns:
            WalletTransaction créée
        """
        
        wallet, _ = SellerWallet.objects.get_or_create(seller=seller)
        
        if amount > 0:
            wallet_transaction = wallet.credit(
                amount=amount,
                transaction_type=WalletTransactionType.ADJUSTMENT,
                reference=f"ADJ-{admin_user.pk}",
                metadata={
                    "reason": reason,
                    "adjusted_by": str(admin_user.pk),
                    "admin_email": admin_user.email,
                }
            )
        else:
            wallet_transaction = wallet.debit(
                amount=abs(amount),
                transaction_type=WalletTransactionType.ADJUSTMENT,
                reference=f"ADJ-{admin_user.pk}",
                metadata={
                    "reason": reason,
                    "adjusted_by": str(admin_user.pk),
                    "admin_email": admin_user.email,
                }
            )
        
        logger.warning(
            f"Ajustement manuel de {amount} F CFA sur le wallet du vendeur {seller.pk} "
            f"par {admin_user.email}. Raison: {reason}"
        )
        
        return wallet_transaction