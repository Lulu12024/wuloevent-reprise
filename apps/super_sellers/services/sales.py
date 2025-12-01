
"""
Created on October 29, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

import logging
from decimal import Decimal
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.events.models import Ticket, ETicket, Order, OrderItem
from apps.events.models.tickets import Ticket as TicketModel
from apps.events.models.ticket_stock import TicketStock, StockTransaction, StockTransactionType
from apps.users.models import Transaction
from apps.xlib.enums import PAYMENT_METHOD, TransactionKindEnum, OrderStatusEnum, TransactionStatusEnum
from apps.super_sellers.services.notification import notify_seller_stock_allocated
from apps.notifications.tasks import send_e_tickets_email_for_order

logger = logging.getLogger(__name__)


class SellerSaleError(Exception):
    pass
@transaction.atomic
def sell_tickets_by_seller(
    *, 
    seller, 
    ticket: Ticket, 
    quantity: int,
    paid_amount: Decimal, 
    payment_channel: str = "MOBILE_MONEY",
    payment_reference: str = "", 
    buyer_full_name: str = "",
    buyer_email: str = "", 
    buyer_phone: str = "", 
    notes: str = ""):
    
    """
    Vente atomique d'un ticket par un vendeur.
    """
    from apps.events.models import Event
    # Verrouiller le stock vendeur + ticket d'événement pour éviter la survente
    stock = (
        TicketStock.objects
        .select_for_update()
        .select_related("seller", "event", "ticket")
        .filter(seller=seller, ticket=ticket, event=ticket.event)
        .first()
    )
    if not stock:
        raise SellerSaleError("Aucun stock alloué pour ce ticket chez ce vendeur.")

    if stock.available_quantity < quantity:
        raise SellerSaleError("Stock insuffisant chez le vendeur.")

    # Verrouille aussi le ticket/event pour décrément
    locked_ticket = TicketModel.objects.select_for_update().get(pk=ticket.pk)

    if locked_ticket.initial_quantity != -1:
        if locked_ticket.available_quantity < quantity:
            raise SellerSaleError("Stock insuffisant côté événement.")

    # 1) OrderItem + Order
    order_item = OrderItem.objects.create(
        ticket=locked_ticket,
        quantity=quantity,
        line_total=locked_ticket.price * quantity,
    )

    order = Order.objects.create(
        user=None,
        item=order_item,
        name=buyer_full_name or "",
        email=buyer_email or "",
        phone=buyer_phone or "",
        status=OrderStatusEnum.SUBMITTED.value,
        is_pseudo_anonymous=True,
    )

    # 2) Transaction (marquée payée)
    # ✅ CORRECTION : Utiliser les bons champs du modèle Transaction
    
    # Déterminer la méthode de paiement
    if payment_channel.upper() in ["CASH", "ESPECES"]:
        payment_method_value = PAYMENT_METHOD.CASH.value
    elif payment_channel.upper() in ["MOBILE_MONEY", "MOMO", "MTN", "MOOV"]:
        payment_method_value = PAYMENT_METHOD.MOMO.value
    elif payment_channel.upper() in ["CARD", "CARTE"]:
        payment_method_value = PAYMENT_METHOD.CARD.value
    else:
        payment_method_value = PAYMENT_METHOD.CASH.value
    
    # Construire la description avec toutes les infos
    description_parts = [
        f"Vente par vendeur {seller.user.get_full_name() if seller.user else seller.pk}",
    ]
    if payment_reference:
        description_parts.append(f"Ref: {payment_reference}")
    if notes:
        description_parts.append(f"Notes: {notes}")
    
    tx = Transaction.objects.create(
        type=TransactionKindEnum.ORDER.value,
        entity_id=order.pk,
        user=seller.user,
        status=TransactionStatusEnum.PAID.value,  # Vente directe = déjà payée
        amount=Decimal(paid_amount),
        gateway="MANUAL",  # Vente manuelle par vendeur
        gateway_id=payment_reference or f"SELLER-{seller.pk}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
        payment_method=payment_method_value,
        description=" | ".join(description_parts),
    )

    # 3) Mouvement de stock Vendeur
    stock.total_sold = F("total_sold") + quantity
    stock.last_sale_at = timezone.now()
    stock.save(update_fields=["total_sold", "last_sale_at"])
    stock.refresh_from_db()

    StockTransaction.create_sale_transaction(
        ticket_stock=stock,
        quantity=quantity,
        initiated_by=seller.user,
        order=order,
        sale_price=locked_ticket.price,
        commission_rate=stock.commission_rate,
        notes=notes or f"Vente par vendeur {seller.pk} / tx={tx.pk}",
    )

    # 4) Stock de l'événement
    if locked_ticket.initial_quantity != -1:
        locked_ticket.available_quantity = F("available_quantity") - quantity
        locked_ticket.save(update_fields=["available_quantity"])
        locked_ticket.refresh_from_db()

    # 5) Participant count
    event = locked_ticket.event
    Event.objects.filter(pk=event.pk).update(
        participant_count=F("participant_count") + quantity
    )
    # 6) Génération ETickets immédiate (QR inclus)
    e_tickets = []
    for i in range(quantity):
        e = ETicket.objects.create(
            event=event,
            ticket=locked_ticket,
            related_order=order,
            expiration_date=locked_ticket.expiry_date,
        )
        e.generate_qr_code()
        e_tickets.append(e)

    # 7) Order terminé
    order.status = OrderStatusEnum.FINISHED.value
    order.save(update_fields=["status"])

    # 8) Crédit du wallet du vendeur (commission)
    try:
        from apps.super_sellers.services.wallet import SellerWalletService
        
        # Calcul de la commission
        sale_total = locked_ticket.price * quantity
        commission_amount = sale_total * (stock.commission_rate / Decimal("100"))
        
        # Créditer le wallet
        SellerWalletService.credit_seller(
            seller=seller,
            amount=commission_amount,
            transaction_type="SALE_COMMISSION",
            description=f"Commission vente {quantity} ticket(s) - Order {order.order_id}",
            metadata={
                "order_id": str(order.pk),
                "ticket_id": str(locked_ticket.pk),
                "quantity": quantity,
                "commission_rate": str(stock.commission_rate),
                "payment_channel": payment_channel,
                "payment_reference": payment_reference,
            }
        )
        logger.info(f"Commission {commission_amount} FCFA créditée au vendeur {seller.pk}")
    except Exception as e:
        logger.exception(f"Erreur lors du crédit wallet vendeur {seller.pk}: {e}")

    # 9) Envoi des billets par email
    if order.email:
        try:
            # ✅ Si c'est une tâche Celery asynchrone
            send_e_tickets_email_for_order.delay(
                order_id=order.order_id,
                user_email=order.email,
                user_full_name=order.name or "Cher client",
            )
            logger.info(f"Email de tickets programmé pour {order.email}")
        except AttributeError:
            # ✅ Si c'est une fonction normale (pas Celery)
            send_e_tickets_email_for_order(
                order_id=order.order_id,
                user_email=order.email,
                user_full_name=order.name or "Cher client",
                e_tickets=e_tickets,
            )
        except Exception as e:
            logger.exception(f"Envoi email tickets échoué pour order={order.pk}: {e}")

    logger.info(
        f"[VENTE] Vendeur {seller.pk} a vendu {quantity} tickets "
        f"(Event: {event.name}, Order: {order.order_id}, "
        f"Total: {paid_amount} FCFA, Ref: {payment_reference or 'N/A'})"
    )

    return order, e_tickets, stock