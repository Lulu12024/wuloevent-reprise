
"""
Created on November 05, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

import io
import datetime
from decimal import Decimal
from django.db.models import Sum, Count
from django.utils import timezone

from apps.events.models import Order, ETicket
from apps.super_sellers.models.reporting import SalesReport, ReportFormat
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
import csv


def compute_period(frequency: str, now=None):
    now = now or timezone.now()
    today = now.date()

    if frequency == "DAILY":
        start = today
        end = today
    elif frequency == "WEEKLY":
        # lundi au dimanche
        start = today - datetime.timedelta(days=today.weekday())
        end = start + datetime.timedelta(days=6)
    else:  # MONTHLY
        start = today.replace(day=1)
        # fin de mois
        next_month = (start.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        end = next_month - datetime.timedelta(days=1)
    return start, end

def fetch_sales_data(super_seller, start, end):
    """
    Données agrégées de ventes pour la période [start, end]
    """
    qs_orders = Order.objects.select_related("item", "item__ticket", "item__ticket__event")\
        .filter(item__ticket__event__organization=super_seller,
                status="FINISHED",
                timestamp__date__gte=start,
                timestamp__date__lte=end)

    total_revenue = qs_orders.aggregate(s=Sum("item__line_total"))["s"] or Decimal("0.00")
    total_tickets = qs_orders.aggregate(q=Sum("item__quantity"))["q"] or 0

    qs_etk = ETicket.objects.select_related("ticket", "event", "related_order")\
        .filter(event__organization=super_seller,
                related_order__status="FINISHED",
                related_order__timestamp__date__gte=start,
                related_order__timestamp__date__lte=end)

    by_seller = (
        qs_etk.values("related_order__user")
        .annotate(tickets=Count("pk"))  
        .order_by("-tickets")
    )

    by_event = (
        qs_etk.values("event__pk", "event__name") 
        .annotate(tickets=Count("pk"))  
        .order_by("-tickets")
    )
    
    print(f"Fetched sales data for {super_seller.name}: {total_tickets} tickets, {total_revenue} revenue")
    return {
        "period": {"start": start, "end": end},
        "totals": {"tickets": total_tickets, "revenue": str(total_revenue)},
        "by_seller": list(by_seller),
        "by_event": list(by_event),
    }

def generate_pdf_report(super_seller, data) -> bytes:
    """
    PDF minimaliste (ReportLab)
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 2*cm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(2*cm, y, f"Rapport de ventes - {super_seller.name}")
    y -= 0.8*cm

    pstart = data["period"]["start"].strftime("%d/%m/%Y")
    pend = data["period"]["end"].strftime("%d/%m/%Y")
    c.setFont("Helvetica", 12)
    c.drawString(2*cm, y, f"Période : {pstart} - {pend}")
    y -= 0.6*cm

    c.drawString(2*cm, y, f"Total tickets : {data['totals']['tickets']}")
    y -= 0.6*cm
    c.drawString(2*cm, y, f"Revenu total : {data['totals']['revenue']} FCFA")
    y -= 1.0*cm

    c.setFont("Helvetica-Bold", 13)
    c.drawString(2*cm, y, "Par évènement")
    y -= 0.6*cm
    c.setFont("Helvetica", 11)
    for row in data["by_event"][:30]:
        line = f"- {row['event__name']} : {row['tickets']} tickets"
        c.drawString(2.2*cm, y, line)
        y -= 0.5*cm
        if y < 3*cm:
            c.showPage(); y = height - 2*cm

    c.setFont("Helvetica-Bold", 13)
    c.drawString(2*cm, y, "Par vendeur (approx.)")
    y -= 0.6*cm
    c.setFont("Helvetica", 11)
    for row in data["by_seller"][:30]:
        line = f"- UserID {row['related_order__user'] or '-'} : {row['tickets']} tickets"
        c.drawString(2.2*cm, y, line)
        y -= 0.5*cm
        if y < 3*cm:
            c.showPage(); y = height - 2*cm

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()

def store_report_file(super_seller, content: bytes, start, end, fmt="PDF") -> str:
    folder = f"reports/{start.year}/{start.month:02d}"
    name = f"{super_seller.pk}_{start.isoformat()}_{end.isoformat()}.{fmt.lower()}"
    path = f"{folder}/{name}"
    default_storage.save(path, ContentFile(content))
    return path

def build_and_archive_report(super_seller, frequency, fmt="PDF"):
    print(f"Building report for {super_seller.name}...")
    start, end = compute_period(frequency)
    print(f"Computed period: {start} to {end}")
    data = fetch_sales_data(super_seller, start, end)
    print(f"Fetched sales data.{data}")
    print(f"Generating {fmt} report for {super_seller.name} from {start} to {end}")
    if fmt == ReportFormat.PDF:
        file_bytes = generate_pdf_report(super_seller, data)
    elif fmt == ReportFormat.CSV:
        file_bytes = generate_csv_report(super_seller, data, delimiter=",")
    else:
        file_bytes = generate_pdf_report(super_seller, data)

    path = store_report_file(super_seller, file_bytes, start, end, fmt)
    report = SalesReport.objects.create(
        super_seller=super_seller,
        period_start=start,
        period_end=end,
        file_path=path,
        file_format=fmt,
    )
    return report, data


def generate_csv_report(super_seller, data, delimiter=",") -> bytes:
    """
    - en-tête (méta)
    - totals (tickets, revenue)
    - by_event (event_id, event_name, tickets)
    - by_seller (user_id, tickets)
    """
    output = io.StringIO()
    writer = csv.writer(output, delimiter=delimiter)

    # ----- Meta header -----
    writer.writerow(["report", f"Sales report - {super_seller.name}"])
    writer.writerow(["period_start", data["period"]["start"].strftime("%Y-%m-%d")])
    writer.writerow(["period_end", data["period"]["end"].strftime("%Y-%m-%d")])
    writer.writerow([])

    # ----- Totals -----
    writer.writerow(["section", "totals"])
    writer.writerow(["total_tickets", data["totals"].get("tickets", 0)])
    writer.writerow(["total_revenue", data["totals"].get("revenue", "0.00")])
    writer.writerow([])

    # ----- By Event -----
    writer.writerow(["section", "by_event"])
    writer.writerow(["event_id", "event_name", "tickets"])
    for row in data.get("by_event", []):
        writer.writerow([
            row.get("event__id", ""),
            row.get("event__name", ""),
            row.get("tickets", 0),
        ])
    writer.writerow([])

    # ----- By Seller -----
    writer.writerow(["section", "by_seller"])
    writer.writerow(["user_id", "tickets"])
    for row in data.get("by_seller", []):
        writer.writerow([
            row.get("related_order__user") or "",
            row.get("tickets", 0),
        ])

    csv_string = output.getvalue()
    csv_bytes = ("\ufeff" + csv_string).encode("utf-8-sig")
    return csv_bytes