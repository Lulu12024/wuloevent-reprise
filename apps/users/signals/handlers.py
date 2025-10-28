import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.events.models import Order, EventHighlighting
from apps.notifications import tasks as notification_tasks
from apps.organizations.models import Subscription, Withdraw
from apps.users.models import Transaction
from apps.users.utils.transactions import update_coupon_related_to_transaction_usage
from apps.xlib.enums import TransactionStatusEnum, TransactionKindEnum, OrderStatusEnum, DISCOUNT_USE_ENTITY_TYPES_ENUM

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


@receiver(post_save)
def handle_payment_transaction(sender, instance, created, **kwargs):
    if not isinstance(instance, Transaction):
        return

    if created:
        return

    if instance.tracker.has_changed('status') and instance.tracker.previous('status') in [
        TransactionStatusEnum.PENDING.value, TransactionStatusEnum.IN_PROGRESS.value] and instance.completed:

        message = "Votre transaction n'a pas abouti, veuillez réessayer dans un instant."
        category = "PAYMENT"

        match instance.type:

            # Case Subscriptions
            case TransactionKindEnum.SUBSCRIPTION.value:
                subscription = Subscription.objects.select_related("organization").get(pk=instance.entity_id)
                subscription.active_status = instance.paid
                subscription.save(update_fields=['active_status'])

                message = f"Votre paiement pour {subscription.get_entity_info['name']} a " \
                          f"{'été bien traité.' if instance.paid else 'échoué, veuillez réessayer ultérieurement.'}"
                category = "SUBSCRIPTION_PAYMENT"

                if instance.paid:
                    update_coupon_related_to_transaction_usage(instance, subscription.organization_id,
                                                               DISCOUNT_USE_ENTITY_TYPES_ENUM.ORGANIZATION.value)
                    subscription.organization.set_subscribe_until(end_date_or_timestamp=subscription.end_date)
                    notification_tasks.notify_users_about_end_of_subscription_processing.delay(str(subscription.pk))

            # Case Event Highlighting
            case TransactionKindEnum.EVENT_HIGHLIGHTING.value:
                event_highlighting = EventHighlighting.objects.select_related('event').get(pk=instance.entity_id)
                event_highlighting.active_status = instance.paid
                event_highlighting.save()
                message = f"Votre paiement pour la mise en avant de votre évènement" \
                          f" ( {event_highlighting.event.name} )" \
                          f" a {'été bien traité.' if instance.paid else 'échoué, veuillez réessayer ultérieurement.'}"
                category = "EVENT_HIGHLIGHTING_PAYMENT"

                if instance.paid:
                    update_coupon_related_to_transaction_usage(instance, event_highlighting.event.organization_id,
                                                               DISCOUNT_USE_ENTITY_TYPES_ENUM.ORGANIZATION.value)
                    notification_tasks.notify_users_about_end_of_event_highlight_processing.delay(
                        str(event_highlighting.pk))

            # Case Order
            case TransactionKindEnum.ORDER.value:
                order = Order.objects.select_related("item", "item__ticket").get(pk=instance.entity_id)

                if instance.paid:
                    order.status = OrderStatusEnum.STARTED.value
                    order.save(update_fields=['status'])

                    update_coupon_related_to_transaction_usage(instance, order.item.ticket.organization_id,
                                                               DISCOUNT_USE_ENTITY_TYPES_ENUM.USER.value)

                message = f"Votre paiement pour la commande N° {order.order_id}" \
                          f" a {'été bien traité.' if instance.paid else 'échoué, veuillez réessayer ultérieurement.'}"
                category = "ORDER_PAYMENT"
                # Notification for order moved to an event signal handler

            # Case Withdraw
            case TransactionKindEnum.WITHDRAW.value:
                withdraw = Withdraw.objects.get(pk=instance.entity_id)
                message = f"Votre dernière demande de retrait de {withdraw.amount} F CFA" \
                          f"a {' été bien traité.' if instance.paid else ' échoué, veuillez réessayer ultérieurement.'}"
                category = "WITHDRAW"
                if instance.paid:
                    notification_tasks.notify_users_about_end_of_withdraw_processing.delay(str(instance.pk))

            case _:
                logger.info(instance.type)

        notification_tasks.notify_user_about_transaction_issue.delay(
            transaction_id=str(instance.pk),
            message=message,
            category=category,
            is_success=instance.paid
        )

#
# @receiver(post_save)
# def handle_withdraw_transaction(sender, instance, created, **kwargs):
#     if not isinstance(instance, Withdraw):
#         return
#     if created:
#         return
#
#     if instance.tracker.has_changed('status') and instance.tracker.previous(
#             'status') == WithdrawStatusEnum.PROCESSING.value and instance.completed and instance.completed:
#         # Update User Financial Account Data
#         message = "Nous avons rencontré une erreur lors du traitement de votre demande de retrait. veuillez réessayer"
#         if instance.paid:
#             try:
#                 withdraw_transaction = Transaction.objects.get(type=TransactionKindEnum.WITHDRAW.value,
#                                                                entity_id=instance.pk)
#
#                 withdraw_transaction.status = TransactionStatusEnum.RESOLVED.value
#                 withdraw_transaction.save()
#
#                 # Get the withdraw transaction and update it
#                 instance.update_user_financial_account()
#                 message = "Votre demande de retrait à été bien traité."
#             except Exception as exc:
#                 logger.exception(exc.__str__())
#         notify_user_about_transaction_issue.delay(
#             transaction_id=str(instance.pk),
#             message=message,
#             category="WITHDRAW",
#             is_success=instance.paid
#         )
