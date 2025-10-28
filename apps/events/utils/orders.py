# -*- coding: utf-8 -*-
"""
Created on 12/05/2025

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from apps.events.utils.tickets import generate_e_ticket_pdf
from apps.utils.utils.codes.utils import format_to_money_string


def send_e_tickets_email_for_order(order_id: str, user_email: str, user_full_name: str, e_tickets):
    logo_url = "https://wulo-events.s3.eu-north-1.amazonaws.com/assets/logo.jpg"

    # Prepare email content
    html_message = render_to_string('notifications/tickets_sending_email.html', {
        'fullName': user_full_name,
        'orderId': order_id,
    })

    email = EmailMessage(
        subject=f"🎫 Billets Générés - Wulo Events",
        body=html_message,
        from_email=f'WuloEvents <{settings.EMAIL_NO_REPLY}>',
        to=[user_email]
    )
    email.content_subtype = "html"

    # Attach all tickets
    for ticket_number, e_ticket in enumerate(e_tickets, start=1):
        # with e_ticket.event.cover_image.open(mode='rb') as event_image_file:
        pdf_buffer = generate_e_ticket_pdf(
            logo_url=logo_url,
            # event_image=event_image_file,
            event_name=e_ticket.event.name,
            location=e_ticket.event.location_name,
            qrcode_data=e_ticket.qr_code_data,
            ticket_name=e_ticket.ticket.name,
            ticket_price=format_to_money_string(e_ticket.ticket.price),  # e_ticket.price,
            ticket_number=ticket_number,
            order_code=order_id
        )
        email.attach(f"Ticket_N°{ticket_number}_Commande_{order_id}.pdf", pdf_buffer.read(), 'application/pdf')

    email.send()
