
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
from apps.xlib.enums import TransactionKindEnum, OrderStatusEnum
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

    Effets de bord:
    - décrémente stock vendeur (TicketStock.total_sold)
    - décrémente stock event (Ticket.available_quantity)
    - incrémente event.participant_count
    - génère ETicket (avec QR)
    - crée Order/OrderItem/Transaction
    - enregistre StockTransaction SALE
    - envoie email de tickets si email présent
    """

    if not seller.can_sell():
        raise SellerSaleError("Ce vendeur n'est pas autorisé à vendre pour le moment.")

    if ticket.event.organization_id != seller.super_seller_id and not ticket.event.is_ephemeral:
        raise SellerSaleError("Le ticket ne fait pas partie des tickets vendables par ce vendeur.")

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
    tx = Transaction.objects.create(
        type=TransactionKindEnum.ORDER.value,
        entity_id=order.pk,
        paid=True,
        amount=Decimal(paid_amount),
        payment_reference=payment_reference or "",
        payment_channel=payment_channel,
        metadata={
            "sold_by_seller": str(seller.pk),
            "seller_user": str(seller.user_id),
            "notes": notes,
        },
    )

    # 3) Mouvement de stock Vendeur
    quantity_before = stock.available_quantity
    stock.total_sold = F("total_sold") + quantity
    stock.save(update_fields=["total_sold"])
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
    event.participant_count = F("participant_count") + quantity
    event.save(update_fields=["participant_count"])

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

    # 8) Envoi des billets par email
    if order.email:
        try:
            send_e_tickets_email_for_order(
                order_id=order.order_id,
                user_email=order.email,
                user_full_name=order.name or "Cher client",
                e_tickets=e_tickets,
            )
        except Exception as e:
            logger.exception(f"Envoi email tickets échoué pour order={order.pk}: {e}")

    return order, e_tickets, stock
