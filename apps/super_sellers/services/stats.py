# -*- coding: utf-8 -*-
"""
Created on November 03, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

from decimal import Decimal
from django.db.models import Sum, Count, F, DecimalField, IntegerField, Value, Q
from django.db.models.functions import Coalesce, TruncDate, TruncWeek, TruncMonth, Concat
from apps.events.models import ETicket, Event
from apps.events.models.ticket_stock import TicketStock, StockTransaction
from apps.events.models.seller import Seller, SellerStatus
from apps.organizations.models import Organization



def _date_filters(date_from, date_to):
    q = Q()
    if date_from:
        q &= Q(timestamp__date__gte=date_from)
    if date_to:
        q &= Q(timestamp__date__lte=date_to)
    return q

def stats_overview(super_seller: Organization, date_from=None, date_to=None):
    tx_qs = (
        StockTransaction.objects
        .filter(
            ticket_stock__seller__super_seller=super_seller,
            transaction_type="SALE",
        )
        .filter(_date_filters(date_from, date_to))
    )

    agg = tx_qs.aggregate(
        tickets_sold=Coalesce(Sum(-F("quantity"), output_field=IntegerField()), 0),
        revenue=Coalesce(Sum(F("sale_price") * -F("quantity"), output_field=DecimalField(max_digits=12, decimal_places=2)), Decimal("0.00")),
        commission=Coalesce(Sum(F("commission_amount"), output_field=DecimalField(max_digits=12, decimal_places=2)), Decimal("0.00")),
    )

    sellers_active = Seller.objects.filter(
        super_seller=super_seller,
        status=SellerStatus.ACTIVE,
        active=True
    ).count()

    # Count distinct events (excluding ephemeral events)
    """
     t
    """
    events_count = Event.objects.filter(
        ephemeral_events__isnull=True
    ).filter(
        pk__in=tx_qs.values_list("ticket_stock__event_id", flat=True).distinct()
    ).count()

    return {
        "total_tickets_sold": agg["tickets_sold"],
        "total_revenue": agg["revenue"],
        "total_commission": agg["commission"],
        "sellers_active": sellers_active,
        "events_count": events_count,
    }

def stats_by_event(super_seller: Organization, date_from=None, date_to=None):
    qs = (
        StockTransaction.objects
        .filter(
            ticket_stock__seller__super_seller=super_seller,
            transaction_type="SALE",
        )
        .filter(_date_filters(date_from, date_to))
        .values("ticket_stock__event_id", "ticket_stock__event__name")
        .annotate(
            tickets_sold=Coalesce(Sum(-F("quantity"), output_field=IntegerField()), 0),
            revenue=Coalesce(Sum(F("sale_price") * -F("quantity"), output_field=DecimalField(max_digits=12, decimal_places=2)), Decimal("0.00")),
            commission=Coalesce(Sum(F("commission_amount"), output_field=DecimalField(max_digits=12, decimal_places=2)), Decimal("0.00")),
        )
        .order_by("-revenue")
    )
    return [
        {
            "event_id": row["ticket_stock__event_id"],
            "event_name": row["ticket_stock__event__name"],
            "tickets_sold": row["tickets_sold"],
            "revenue": row["revenue"],
            "commission": row["commission"],
        } for row in qs
    ]

def stats_by_seller(super_seller: Organization, date_from=None, date_to=None):
    qs = (
        StockTransaction.objects
        .filter(
            ticket_stock__seller__super_seller=super_seller,
            transaction_type="SALE",
        )
        .filter(_date_filters(date_from, date_to))
        .values("ticket_stock__seller_id", "ticket_stock__seller__user__first_name", "ticket_stock__seller__user__last_name")
        .annotate(
            tickets_sold=Coalesce(Sum(-F("quantity"), output_field=IntegerField()), 0),
            revenue=Coalesce(Sum(F("sale_price") * -F("quantity"), output_field=DecimalField(max_digits=12, decimal_places=2)), Decimal("0.00")),
            commission=Coalesce(Sum(F("commission_amount"), output_field=DecimalField(max_digits=12, decimal_places=2)), Decimal("0.00")),
        )
        .order_by("-revenue")
    )
    return [
        {
            "seller_id": row["ticket_stock__seller_id"],
            "seller_name": f'{row["ticket_stock__seller__user__first_name"]} {row["ticket_stock__seller__user__last_name"]}'.strip(),
            "tickets_sold": row["tickets_sold"],
            "revenue": row["revenue"],
            "commission": row["commission"],
        } for row in qs
    ]

def stats_by_period(super_seller: Organization, granularity="day", date_from=None, date_to=None):
    qs = (
        StockTransaction.objects
        .filter(
            ticket_stock__seller__super_seller=super_seller,
            transaction_type="SALE",
        )
        .filter(_date_filters(date_from, date_to))
    )

    if granularity == "week":
        qs = qs.annotate(p=TruncWeek("timestamp"))
    elif granularity == "month":
        qs = qs.annotate(p=TruncMonth("timestamp"))
    else:
        qs = qs.annotate(p=TruncDate("timestamp"))

    qs = qs.values("p").annotate(
        tickets_sold=Coalesce(Sum(-F("quantity"), output_field=IntegerField()), 0),
        revenue=Coalesce(Sum(F("sale_price") * -F("quantity"), output_field=DecimalField(max_digits=12, decimal_places=2)), Decimal("0.00")),
        commission=Coalesce(Sum(F("commission_amount"), output_field=DecimalField(max_digits=12, decimal_places=2)), Decimal("0.00")),
    ).order_by("p")

    return [
        {
            "period": row["p"].strftime("%Y-%m-%d") if granularity == "day"
                      else (row["p"].strftime("%Y-W%W") if granularity == "week"
                            else row["p"].strftime("%Y-%m")),
            "tickets_sold": row["tickets_sold"],
            "revenue": row["revenue"],
            "commission": row["commission"],
        } for row in qs
    ]
