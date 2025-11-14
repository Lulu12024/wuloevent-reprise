
"""
Created on November 03, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""
import logging
from decimal import Decimal

from django.db.models import Sum, Max, F, DecimalField, IntegerField
from django.db.models.functions import Abs
from django.utils import timezone

from apps.events.models.seller import Seller
from apps.events.models.ticket_stock import TicketStock, StockTransaction, StockTransactionType

logger = logging.getLogger(__name__)


def _date_range_filter(qs, date_from=None, date_to=None, field_name="timestamp"):

    if date_from:
        qs = qs.filter(**{f"{field_name}__date__gte": date_from})
    if date_to:
        qs = qs.filter(**{f"{field_name}__date__lte": date_to})
    return qs


def seller_stats_overview(seller: Seller, date_from=None, date_to=None) -> dict:
    """
    Totaux pour un vendeur sur une période:
    - total_tickets_sold
    - total_revenue
    - total_commission
    """
    tx = (
        StockTransaction.objects.filter(
            ticket_stock__seller=seller,
            transaction_type=StockTransactionType.SALE,
        )
        .select_related("ticket_stock", "ticket_stock__event")
    )
    tx = _date_range_filter(tx, date_from, date_to, field_name="timestamp")

    agg = tx.aggregate(
        tickets_sold=Sum(Abs(F("quantity")), output_field=IntegerField()),
        revenue=Sum(
            F("sale_price") * Abs(F("quantity")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        commission=Sum(
            F("commission_amount"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
    )

    return {
        "total_tickets_sold": agg.get("tickets_sold") or 0,
        "total_revenue": str(agg.get("revenue") or Decimal("0.00")),
        "total_commission": str(agg.get("commission") or Decimal("0.00")),
    }


def seller_stats_by_event(seller: Seller, date_from=None, date_to=None):
    """
    Agrégation par évènement:
    - event_id, event_name, event_date
    - tickets_sold
    - revenue
    - last_sale_at
    Retourne une liste à sérialiser.
    """
    tx = (
        StockTransaction.objects.filter(
            ticket_stock__seller=seller,
            transaction_type=StockTransactionType.SALE,
        )
        .select_related("ticket_stock__event")
        .values(
            "ticket_stock__event_id",
            "ticket_stock__event__name",
            "ticket_stock__event__date",
        )
    )
    tx = _date_range_filter(tx, date_from, date_to, field_name="timestamp")

    rows = (
        tx.annotate(
            tickets_sold=Sum(Abs(F("quantity")), output_field=IntegerField()),
            revenue=Sum(
                F("sale_price") * Abs(F("quantity")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            last_sale_at=Max("timestamp"),
        )
        .order_by()
    )

    out = []
    for r in rows:
        out.append(
            {
                "event_id": r["ticket_stock__event_id"],
                "event_name": r["ticket_stock__event__name"],
                "event_date": r["ticket_stock__event__date"],
                "tickets_sold": r["tickets_sold"] or 0,
                "revenue": str(r["revenue"] or Decimal("0.00")),
                "last_sale_at": r["last_sale_at"],
            }
        )
    return out


def seller_stocks_current(seller: Seller):
    """
    Liste les stocks alloués du vendeur avec:
    - event_id, event_name
    - ticket_id, ticket_name
    - authorized_sale_price, commission_rate
    - total_allocated, total_sold, available_quantity
    """
    stocks = (
        TicketStock.objects.filter(seller=seller)
        .select_related("event", "ticket")
        .order_by("-allocated_at")
    )

    rows = []
    for st in stocks:
        rows.append(
            {
                "event_id": st.event_id,
                "event_name": st.event.name if st.event else None,
                "ticket_id": st.ticket_id,
                "ticket_name": st.ticket.name if st.ticket else None,
                "authorized_sale_price": str(st.authorized_sale_price),
                "commission_rate": str(st.commission_rate),
                "total_allocated": st.total_allocated,
                "total_sold": st.total_sold,
                "available_quantity": st.available_quantity,
            }
        )
    return rows
