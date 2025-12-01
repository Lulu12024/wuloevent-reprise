# -*- coding: utf-8 -*-
"""
Created on October 29, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

import logging
from decimal import Decimal
from django.db import transaction
from django.db.models import F
from django.core.exceptions import ValidationError
from apps.events.models import Ticket, Event
from apps.events.models.ticket_stock import TicketStock, StockTransaction, StockTransactionType
from apps.events.models.seller import Seller

logger = logging.getLogger(__name__)

class StockAllocationError(Exception):
    pass

@transaction.atomic
def allocate_ticket_stock(
    *,
    super_seller_org,
    seller: Seller,
    ticket: Ticket,
    quantity: int,
    authorized_sale_price: Decimal,
    commission_rate: Decimal,
    notes: str = "",
    initiated_by=None,
):
    """
    Alloue `quantity` unités d'un Ticket à un Seller.
      1) verrouille le ticket (select_for_update)
      2) vérifie le stock dispo (Ticket.available_quantity)
      3) crée/maj TicketStock (unique (seller, event, ticket))
      4) crée transaction StockTransaction (ALLOCATION)
      5) décrémente Ticket.available_quantity
    """
    print(seller.super_seller_id, super_seller_org.pk)
    if seller.super_seller_id != super_seller_org.pk:
        raise StockAllocationError("Ce vendeur n'appartient pas à votre organisation.")

    # Verrou dur sur le ticket pour empêcher la surallocation concurrente
    ticket_locked = (
        Ticket.objects.select_for_update()
        .select_related("event")
        .get(pk=ticket.pk)
    )

    if ticket_locked.available_quantity < quantity:
        raise StockAllocationError("Stock insuffisant sur le ticket à allouer.")

    # get or create TicketStock (clé unique (seller, event, ticket))
    stock, created = TicketStock.objects.select_for_update().get_or_create(
        seller=seller,
        event=ticket_locked.event,
        ticket=ticket_locked,
        defaults=dict(
            total_allocated=0,
            total_sold=0,
            authorized_sale_price=authorized_sale_price,
            commission_rate=commission_rate,
            notes=notes or "",
        ),
    )

    # Si le stock existant a un prix/commission différents, on met à jour
    updates = {}
    if stock.authorized_sale_price != authorized_sale_price:
        updates["authorized_sale_price"] = authorized_sale_price
    if stock.commission_rate != commission_rate:
        updates["commission_rate"] = commission_rate
    if notes and notes != stock.notes:
        updates["notes"] = notes

    if updates:
        for k, v in updates.items():
            setattr(stock, k, v)

    # quantité dispo AVANT allocation (pour logs/transactions)
    before = stock.available_quantity  # total_allocated - total_sold

    # Incrémente l’allocation
    stock.total_allocated = F("total_allocated") + quantity
    stock.save(update_fields=["total_allocated"])
    stock.refresh_from_db()

    # Transaction d’historique
    StockTransaction.create_allocation_transaction(
        ticket_stock=stock,
        quantity=quantity,
        initiated_by=initiated_by,
        notes=notes or "",
    )

    # Décrémente le stock global ticket
    ticket_locked.available_quantity = F("available_quantity") - quantity
    ticket_locked.save(update_fields=["available_quantity"])

    logger.info(
        f"[STOCK] Allocation OK: seller={seller.pk} ticket={ticket.pk} qty={quantity} org={super_seller_org.pk}"
    )
    return stock
