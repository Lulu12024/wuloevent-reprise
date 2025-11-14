# -*- coding: utf-8 -*-
"""

Tâches Celery pour le traitement asynchrone des retraits.
"""

import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(name="process_pending_withdrawals", bind=True, max_retries=3)
def process_pending_withdrawals(self):
    """
    Traite tous les retraits approuvés en attente.
    
    Cette tâche doit être exécutée périodiquement (ex: toutes les 30 minutes).
    
    Returns:
        dict avec les statistiques de traitement
    """
    from apps.super_sellers.services.withdrawal import SellerWithdrawalService
    
    logger.info("Début du traitement des retraits en attente")
    
    try:
        stats = SellerWithdrawalService.process_pending_withdrawals()
        
        logger.info(
            f"Traitement terminé: {stats['success']} succès, "
            f"{stats['failed']} échecs sur {stats['total']} retraits"
        )
        
        return stats
        
    except Exception as e:
        logger.exception(f"Erreur lors du traitement des retraits: {e}")
        raise self.retry(exc=e, countdown=300)  # Retry après 5 minutes


@shared_task(name="process_single_withdrawal", bind=True, max_retries=3)
def process_single_withdrawal(self, withdrawal_id: str):
    """
    Traite un retrait spécifique de manière asynchrone.
    
    Args:
        withdrawal_id: UUID du retrait à traiter
    
    Returns:
        dict avec le résultat du traitement
    """
    from apps.super_sellers.models.seller_withdrawal import SellerWithdrawal
    from apps.super_sellers.services.withdrawal import SellerWithdrawalService
    
    logger.info(f"Traitement du retrait {withdrawal_id}")
    
    try:
        withdrawal = SellerWithdrawal.objects.get(pk=withdrawal_id)
        
        success = SellerWithdrawalService.process_withdrawal(withdrawal)
        
        if success:
            logger.info(f"Retrait {withdrawal_id} traité avec succès")
            return {
                "withdrawal_id": str(withdrawal_id),
                "status": withdrawal.status,
                "success": True,
            }
        else:
            logger.warning(f"Échec du traitement du retrait {withdrawal_id}")
            return {
                "withdrawal_id": str(withdrawal_id),
                "status": withdrawal.status,
                "success": False,
            }
            
    except SellerWithdrawal.DoesNotExist:
        logger.error(f"Retrait {withdrawal_id} non trouvé")
        return {
            "withdrawal_id": str(withdrawal_id),
            "error": "Retrait non trouvé",
            "success": False,
        }
    except Exception as e:
        logger.exception(f"Erreur lors du traitement du retrait {withdrawal_id}: {e}")
        raise self.retry(exc=e, countdown=600)  # Retry après 10 minutes


@shared_task(name="retry_failed_withdrawals")
def retry_failed_withdrawals():
    """
    Retente les retraits échoués qui ont encore des retries disponibles.
    
    Cette tâche recherche tous les retraits avec status APPROVED qui ont
    échoué mais peuvent encore être retentés.
    
    Returns:
        dict avec les statistiques de retry
    """
    from apps.super_sellers.models.seller_withdrawal import SellerWithdrawal, WithdrawalStatus
    from apps.super_sellers.services.withdrawal import SellerWithdrawalService
    
    logger.info("Recherche des retraits à retenter")
    
    # Récupérer les retraits approuvés avec des retries possibles
    withdrawals = SellerWithdrawal.objects.filter(
        status=WithdrawalStatus.APPROVED,
        retry_count__lt=3,  # max_retry_count
    ).select_related("seller", "seller__wallet")
    
    stats = {"total": withdrawals.count(), "success": 0, "failed": 0}
    
    for withdrawal in withdrawals:
        try:
            if SellerWithdrawalService.process_withdrawal(withdrawal):
                stats["success"] += 1
            else:
                stats["failed"] += 1
        except Exception as e:
            logger.exception(f"Erreur retry retrait {withdrawal.pk}: {e}")
            stats["failed"] += 1
    
    logger.info(
        f"Retry terminé: {stats['success']} succès, "
        f"{stats['failed']} échecs sur {stats['total']} retraits"
    )
    
    return stats


@shared_task(name="send_withdrawal_notifications")
def send_withdrawal_notifications(withdrawal_id: str, notification_type: str):
    """
    Envoie les notifications pour un retrait.
    
    Args:
        withdrawal_id: UUID du retrait
        notification_type: Type de notification (created, approved, completed, failed)
    
    Returns:
        dict avec le résultat de l'envoi
    """
    from apps.super_sellers.models.seller_withdrawal import SellerWithdrawal
    
    logger.info(f"Envoi notification {notification_type} pour retrait {withdrawal_id}")
    
    try:
        withdrawal = SellerWithdrawal.objects.select_related(
            "seller", "seller__user"
        ).get(pk=withdrawal_id)
        
        seller = withdrawal.seller
        user = seller.user
        
        # TODO: Implémenter l'envoi via le système de notifications
        # Exemples selon le type:
        
        if notification_type == "created":
            # Notifier le vendeur que sa demande est créée
            message = (
                f"Votre demande de retrait de {withdrawal.amount} F CFA "
                f"a été créée et est en attente d'approbation."
            )
            
        elif notification_type == "approved":
            # Notifier que la demande est approuvée
            message = (
                f"Votre demande de retrait de {withdrawal.amount} F CFA "
                f"a été approuvée et sera traitée prochainement."
            )
            
        elif notification_type == "completed":
            # Notifier que le paiement est effectué
            message = (
                f"Votre retrait de {withdrawal.amount} F CFA a été effectué avec succès. "
                f"Référence: {withdrawal.provider_reference}"
            )
            
        elif notification_type == "failed":
            # Notifier l'échec
            message = (
                f"Votre demande de retrait de {withdrawal.amount} F CFA a échoué. "
                f"Raison: {withdrawal.error_message}"
            )
        
        elif notification_type == "rejected":
            # Notifier le rejet
            message = (
                f"Votre demande de retrait de {withdrawal.amount} F CFA a été rejetée. "
                f"Raison: {withdrawal.rejection_reason}"
            )
        
        else:
            message = "Mise à jour de votre demande de retrait"
        
        # TODO: Appeler le service de notifications
        # NotificationService.send_email(user.email, "Retrait - WuloEvents", message)
        # NotificationService.send_push(user_id, message)
        
        logger.info(f"Notification {notification_type} envoyée pour retrait {withdrawal_id}")
        
        return {
            "withdrawal_id": str(withdrawal_id),
            "notification_type": notification_type,
            "success": True,
            "message": message,
        }
        
    except SellerWithdrawal.DoesNotExist:
        logger.error(f"Retrait {withdrawal_id} non trouvé pour notification")
        return {
            "withdrawal_id": str(withdrawal_id),
            "error": "Retrait non trouvé",
            "success": False,
        }
    except Exception as e:
        logger.exception(f"Erreur envoi notification pour retrait {withdrawal_id}: {e}")
        return {
            "withdrawal_id": str(withdrawal_id),
            "error": str(e),
            "success": False,
        }


@shared_task(name="cleanup_old_withdrawal_logs")
def cleanup_old_withdrawal_logs(days: int = 90):
    """
    Nettoie les anciens logs de retraits pour optimiser la DB.
    
    Supprime les logs détaillés des retraits complétés depuis plus de X jours,
    en gardant uniquement les informations essentielles.
    
    Args:
        days: Nombre de jours après lesquels nettoyer (défaut: 90)
    
    Returns:
        dict avec le nombre de logs nettoyés
    """
    from apps.super_sellers.models.seller_withdrawal import SellerWithdrawal, WithdrawalStatus
    
    logger.info(f"Nettoyage des logs de retraits de plus de {days} jours")
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # Retraits complétés depuis plus de X jours
    old_withdrawals = SellerWithdrawal.objects.filter(
        status=WithdrawalStatus.COMPLETED,
        completed_at__lt=cutoff_date
    )
    
    count = 0
    for withdrawal in old_withdrawals:
        if withdrawal.processing_logs:
            # Garder uniquement le premier et dernier log
            if len(withdrawal.processing_logs) > 2:
                withdrawal.processing_logs = [
                    withdrawal.processing_logs[0],  # Premier log
                    withdrawal.processing_logs[-1],  # Dernier log
                ]
                withdrawal.save(update_fields=["processing_logs"])
                count += 1
    
    logger.info(f"{count} logs de retraits nettoyés")
    
    return {
        "cleaned_count": count,
        "cutoff_date": cutoff_date.isoformat(),
    }


@shared_task(name="send_daily_withdrawal_summary")
def send_daily_withdrawal_summary():
    """
    Envoie un résumé quotidien des retraits aux administrateurs.
    
    À exécuter une fois par jour (ex: 8h du matin).
    
    Returns:
        dict avec les statistiques du jour
    """
    from apps.super_sellers.models.seller_withdrawal import SellerWithdrawal, WithdrawalStatus
    from django.db.models import Sum, Count
    
    logger.info("Génération du résumé quotidien des retraits")
    
    # Retraits d'hier
    yesterday = timezone.now().date() - timedelta(days=1)
    yesterday_start = timezone.make_aware(
        timezone.datetime.combine(yesterday, timezone.datetime.min.time())
    )
    yesterday_end = timezone.make_aware(
        timezone.datetime.combine(yesterday, timezone.datetime.max.time())
    )
    
    withdrawals = SellerWithdrawal.objects.filter(
        requested_at__range=(yesterday_start, yesterday_end)
    )
    
    stats = {
        "date": yesterday.isoformat(),
        "total_count": withdrawals.count(),
        "total_amount": withdrawals.aggregate(Sum("amount"))["amount__sum"] or 0,
    }
    
    # Par statut
    status_stats = withdrawals.values("status").annotate(
        count=Count("pk"),
        total=Sum("amount")
    )
    
    for stat in status_stats:
        status = stat["status"]
        stats[f"{status}_count"] = stat["count"]
        stats[f"{status}_amount"] = stat["total"]
    
    # Retraits en attente d'action
    pending_approval = SellerWithdrawal.objects.filter(
        status=WithdrawalStatus.PENDING
    ).count()
    
    stats["pending_approval_count"] = pending_approval
    
    # TODO: Envoyer le résumé par email aux admins
    logger.info(f"Résumé quotidien: {stats['total_count']} retraits, {stats['total_amount']} F CFA")
    
    return stats


@shared_task(name="auto_approve_small_withdrawals")
def auto_approve_small_withdrawals(max_amount: float = 10000.0):
    """
    Approuve automatiquement les petits retraits pour accélérer le processus.
    
    Args:
        max_amount: Montant maximum pour approbation automatique (défaut: 10000 F CFA)
    
    Returns:
        dict avec le nombre de retraits auto-approuvés
    """
    from apps.super_sellers.models.seller_withdrawal import SellerWithdrawal, WithdrawalStatus
    from apps.users.models import User
    
    logger.info(f"Auto-approbation des retraits <= {max_amount} F CFA")
    
    # Trouver le user système pour l'approbation
    system_user = User.objects.filter(email="system@wuloevents.com").first()
    if not system_user:
        logger.warning("User système non trouvé, utilisation du premier admin")
        system_user = User.objects.filter(is_staff=True).first()
    
    if not system_user:
        logger.error("Aucun utilisateur disponible pour auto-approbation")
        return {"error": "Pas d'utilisateur système", "count": 0}
    
    # Retraits éligibles
    small_withdrawals = SellerWithdrawal.objects.filter(
        status=WithdrawalStatus.PENDING,
        amount__lte=max_amount
    ).select_related("seller", "seller__user")
    
    count = 0
    for withdrawal in small_withdrawals:
        try:
            # Vérifier que le vendeur a un bon KYC
            if withdrawal.seller.can_sell():
                withdrawal.approve(approved_by=system_user)
                count += 1
                logger.info(f"Retrait {withdrawal.pk} auto-approuvé ({withdrawal.amount} F CFA)")
        except Exception as e:
            logger.exception(f"Erreur auto-approbation retrait {withdrawal.pk}: {e}")
    
    logger.info(f"{count} retraits auto-approuvés")
    
    return {
        "auto_approved_count": count,
        "max_amount": max_amount,
    }