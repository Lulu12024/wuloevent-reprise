# -*- coding: utf-8 -*-
"""

Service pour traiter les retraits vers Mobile Money et virements bancaires.
"""

import logging
from decimal import Decimal
from typing import Optional, Dict
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class WithdrawalProcessingError(Exception):
    """Exception pour les erreurs de traitement de retrait"""
    pass


class SellerWithdrawalService:
    """
    Service principal pour traiter les retraits des vendeurs.
    Gère l'intégration avec les APIs Mobile Money et virements bancaires.
    """
    
    # Montant minimum pour un retrait (en F CFA)
    MIN_WITHDRAWAL_AMOUNT = Decimal("1000.00")
    
    # Frais de retrait par méthode (peut être configuré en DB)
    WITHDRAWAL_FEES = {
        "MOBILE_MONEY_MTN": Decimal("100.00"),
        "MOBILE_MONEY_MOOV": Decimal("100.00"),
        "BANK_TRANSFER": Decimal("500.00"),
    }
    
    @classmethod
    def calculate_fees(cls, amount: Decimal, method: str) -> Decimal:
        """
        Calcule les frais de retrait selon la méthode.
        
        Args:
            amount: Montant demandé
            method: Méthode de retrait
        
        Returns:
            Montant des frais
        """
        base_fee = cls.WITHDRAWAL_FEES.get(method, Decimal("0.00"))
        
        # Possibilité d'ajouter un pourcentage si nécessaire
        # percentage_fee = amount * Decimal("0.01")  # 1%
        # return base_fee + percentage_fee
        
        return base_fee
    
    @classmethod
    @transaction.atomic
    def create_withdrawal_request(
        cls,
        seller,
        amount: Decimal,
        method: str,
        payment_details: Dict,
    ):
        """
        Crée une demande de retrait.
        
        Args:
            seller: Instance de Seller
            amount: Montant demandé
            method: Méthode de retrait
            payment_details: Détails de paiement (phone, bank_account, etc.)
        
        Returns:
            Instance de SellerWithdrawal créée
        
        Raises:
            WithdrawalProcessingError si validation échoue
        """
        from apps.super_sellers.models.seller_withdrawal import (
            SellerWithdrawal,
            WithdrawalMethod
        )
        
        # Validations
        if amount < cls.MIN_WITHDRAWAL_AMOUNT:
            raise WithdrawalProcessingError(
                f"Le montant minimum de retrait est {cls.MIN_WITHDRAWAL_AMOUNT} F CFA"
            )
        
        # Vérifier que le vendeur peut vendre (statut actif + KYC)
        if not seller.can_sell():
            raise WithdrawalProcessingError(
                "Votre compte n'est pas autorisé à effectuer des retraits. "
                "Veuillez vérifier votre statut et votre KYC."
            )
        
        # Vérifier le solde disponible
        wallet = seller.wallet
        if not wallet.can_withdraw(amount):
            raise WithdrawalProcessingError(
                f"Solde insuffisant. Disponible: {wallet.balance} F CFA, "
                f"Demandé: {amount} F CFA"
            )
        
        # Calculer les frais
        fees = cls.calculate_fees(amount, method)
        net_amount = amount - fees
        
        # Valider les détails de paiement selon la méthode
        if method in [WithdrawalMethod.MOBILE_MONEY_MTN, WithdrawalMethod.MOBILE_MONEY_MOOV]:
            if not payment_details.get("payment_phone"):
                raise WithdrawalProcessingError("Numéro de téléphone requis pour Mobile Money")
        
        elif method == WithdrawalMethod.BANK_TRANSFER:
            # Seuls les super-vendeurs peuvent faire des virements bancaires
            if not seller.super_seller.is_super_seller():
                raise WithdrawalProcessingError(
                    "Les virements bancaires sont uniquement disponibles pour les super-vendeurs"
                )
            
            if not all([
                payment_details.get("bank_account_number"),
                payment_details.get("bank_name"),
                payment_details.get("bank_account_name"),
            ]):
                raise WithdrawalProcessingError(
                    "Informations bancaires complètes requises"
                )
        
        # Réserver le montant dans le wallet
        wallet.reserve_for_withdrawal(amount)
        
        # Créer la demande de retrait
        withdrawal = SellerWithdrawal.objects.create(
            seller=seller,
            amount=amount,
            fees=fees,
            net_amount=net_amount,
            method=method,
            payment_phone=payment_details.get("payment_phone"),
            bank_account_name=payment_details.get("bank_account_name"),
            bank_account_number=payment_details.get("bank_account_number"),
            bank_name=payment_details.get("bank_name"),
        )
        
        withdrawal.add_log(
            f"Demande de retrait créée: {amount} F CFA via {method}",
            "INFO"
        )
        
        logger.info(
            f"Demande de retrait {withdrawal.pk} créée pour le vendeur {seller.pk}: "
            f"{amount} F CFA via {method}"
        )
        
        # Notification au vendeur
        cls._notify_withdrawal_created(withdrawal)
        
        return withdrawal
    
    @classmethod
    @transaction.atomic
    def process_mobile_money_withdrawal(cls, withdrawal):
        """
        Traite un retrait via Mobile Money.
        Intégration avec FedaPay ou autre provider.
        
        Args:
            withdrawal: Instance de SellerWithdrawal
        
        Returns:
            bool: True si succès, False sinon
        """
        try:
            # Marquer comme en traitement
            withdrawal.mark_as_processing()
            
            # TODO: Intégrer l'API Mobile Money (FedaPay, etc.)
            # Pour l'instant, simulation
            
            # from apps.utils.adapters.fedapay import WithdrawAdapter
            # withdraw_adapter = WithdrawAdapter()
            # gateway = withdraw_adapter.get_gateway_instance()
            
            # Préparer les données pour l'API
            payment_data = {
                "amount": str(withdrawal.net_amount),
                "phone": withdrawal.payment_phone,
                "description": f"Retrait vendeur - {withdrawal.seller.user.get_full_name()}",
                "reference": str(withdrawal.pk),
            }
            
            # Appel API (à implémenter)
            # response = gateway.disburse(**payment_data)
            
            # Simuler un succès pour le développement
            provider_reference = f"FEDAPAY-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            provider_response = {
                "status": "success",
                "reference": provider_reference,
                "timestamp": timezone.now().isoformat(),
            }
            
            # Marquer comme complété
            withdrawal.mark_as_completed(
                provider_reference=provider_reference,
                provider_response=provider_response
            )
            
            logger.info(f"Retrait {withdrawal.pk} traité avec succès via Mobile Money")
            
            # Notification au vendeur
            cls._notify_withdrawal_completed(withdrawal)
            
            return True
            
        except Exception as e:
            error_message = f"Erreur lors du traitement Mobile Money: {str(e)}"
            logger.exception(error_message)
            
            withdrawal.mark_as_failed(error_message, schedule_retry=True)
            
            # Notification d'échec
            cls._notify_withdrawal_failed(withdrawal)
            
            return False
    
    @classmethod
    @transaction.atomic
    def process_bank_transfer_withdrawal(cls, withdrawal):
        """
        Traite un retrait par virement bancaire.
        Processus principalement manuel avec validation admin.
        
        Args:
            withdrawal: Instance de SellerWithdrawal
        
        Returns:
            bool: True si succès (validation passée), False sinon
        """
        try:
            # Marquer comme en traitement
            withdrawal.mark_as_processing()
            
            # Pour les virements bancaires, le processus est généralement manuel
            # Un admin doit valider et effectuer le virement
            
            withdrawal.add_log(
                "Virement bancaire en attente de traitement manuel par un administrateur",
                "INFO"
            )
            
            logger.info(
                f"Retrait {withdrawal.pk} par virement bancaire en attente de traitement manuel"
            )
            
            # Notification à l'admin
            cls._notify_admin_bank_transfer(withdrawal)
            
            return True
            
        except Exception as e:
            error_message = f"Erreur lors du traitement virement bancaire: {str(e)}"
            logger.exception(error_message)
            
            withdrawal.mark_as_failed(error_message, schedule_retry=False)
            return False
    
    @classmethod
    def process_withdrawal(cls, withdrawal):
        """
        Point d'entrée principal pour traiter un retrait.
        Détermine la méthode et appelle le handler approprié.
        
        Args:
            withdrawal: Instance de SellerWithdrawal
        
        Returns:
            bool: True si succès, False sinon
        """
        if withdrawal.is_mobile_money():
            return cls.process_mobile_money_withdrawal(withdrawal)
        elif withdrawal.is_bank_transfer():
            return cls.process_bank_transfer_withdrawal(withdrawal)
        else:
            logger.error(f"Méthode de retrait non supportée: {withdrawal.method}")
            return False
    
    @classmethod
    def process_pending_withdrawals(cls):
        """
        Traite tous les retraits approuvés en attente.
        À appeler depuis une tâche Celery périodique.
        
        Returns:
            dict avec les stats de traitement
        """
        from apps.super_sellers.models.seller_withdrawal import SellerWithdrawal
        
        pending = SellerWithdrawal.get_approved_for_processing() 
        
        logger.info(f"Traitement de {pending.count()} retrait(s) en attente")
        
        stats = {"success": 0, "failed": 0, "total": pending.count()}
        
        for withdrawal in pending:
            try:
                if cls.process_withdrawal(withdrawal):
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                logger.exception(f"Erreur traitement retrait {withdrawal.pk}: {e}")
                stats["failed"] += 1
        
        logger.info(
            f"Traitement terminé: {stats['success']} succès, {stats['failed']} échecs"
        )
        
        return stats
    
    # Méthodes de notification (à implémenter avec le système de notifications)
    
    @staticmethod
    def _notify_withdrawal_created(withdrawal):
        """Notifie le vendeur de la création de sa demande"""
        # TODO: Implémenter avec le système de notifications
        logger.info(f"TODO: Notifier vendeur {withdrawal.seller.pk} - demande créée")
    
    @staticmethod
    def _notify_withdrawal_completed(withdrawal):
        """Notifie le vendeur que son retrait est complété"""
        # TODO: Implémenter avec le système de notifications
        logger.info(f"TODO: Notifier vendeur {withdrawal.seller.pk} - retrait complété")
    
    @staticmethod
    def _notify_withdrawal_failed(withdrawal):
        """Notifie le vendeur de l'échec de son retrait"""
        # TODO: Implémenter avec le système de notifications
        logger.info(f"TODO: Notifier vendeur {withdrawal.seller.pk} - retrait échoué")
    
    @staticmethod
    def _notify_admin_bank_transfer(withdrawal):
        """Notifie les admins d'une demande de virement bancaire"""
        # TODO: Implémenter avec le système de notifications
        logger.info(f"TODO: Notifier admin - virement bancaire {withdrawal.pk}")