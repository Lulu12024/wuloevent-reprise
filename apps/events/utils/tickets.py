# -*- coding: utf-8 -*-
"""
Created on 12/05/2025

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
import logging
import os
from datetime import datetime
from io import BytesIO

import qrcode
import requests
from django.conf import settings
from reportlab.lib.colors import black, blue
from reportlab.lib.pagesizes import A6
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

font_path_bold = os.path.join(settings.BASE_DIR, 'assets', 'fonts', 'Montserrat-Bold.ttf')
font_path_regular = os.path.join(settings.BASE_DIR, 'assets', 'fonts', 'Montserrat-Regular.ttf')
font_path_medium_italic = os.path.join(settings.BASE_DIR, 'assets', 'fonts', 'Montserrat-MediumItalic.ttf')

pdfmetrics.registerFont(TTFont('Montserrat-Bold', font_path_bold))
pdfmetrics.registerFont(TTFont('Montserrat', font_path_regular))
pdfmetrics.registerFont(TTFont('Montserrat-MediumItalic', font_path_medium_italic))


def generate_e_ticket_pdf(logo_url, event_name, location, qrcode_data, ticket_name, ticket_price, ticket_number,
                          order_code):
    """
    Use to generate a ticket as pdf from ticket information

    :param logo_url:
    :param event_name:
    :param location:
    :param qrcode_data:
    :param ticket_name:
    :param ticket_price:
    :param ticket_number:
    :param order_code:
    :return: buffer ( the generated pdf buffer )
    """

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A6)
    width, height = A6

    margin = 0.8 * cm
    y = height - margin - 0.3 * cm

    # Draw border
    c.setStrokeColor(blue)
    c.rect(margin / 2, margin / 2, width - margin, height - margin)

    # Title: Ticket N° X – Commande Y
    c.setFont("Montserrat", 11)
    title = f"Ticket N° {ticket_number} – Commande {order_code}"
    c.drawCentredString(width / 2, y, title)
    y -= 1.0 * cm

    # Logo
    if logo_url:
        try:
            logo_resp = requests.get(logo_url)
            if logo_resp.status_code == 200:
                logo_img = ImageReader(BytesIO(logo_resp.content))
                logo_width = 3.5 * cm
                logo_height = 2 * cm
                c.drawImage(logo_img, (width - logo_width) / 2, y - logo_height,
                            width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')
                y -= logo_height + 0.3 * cm
        except Exception as e:
            logger.info(f"Error loading logo: {e}")

    # QR Code
    qr_size = 3.5 * cm
    qr = qrcode.make(qrcode_data)
    qr_buffer = BytesIO()
    qr.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    qr_img = ImageReader(qr_buffer)
    c.drawImage(qr_img, (width - qr_size) / 2, y - qr_size,
                width=qr_size, height=qr_size)
    y -= qr_size + 1 * cm

    # Ticket Infos
    c.setFillColor(blue)
    c.setFont("Montserrat-Bold", 10)
    c.drawCentredString(width / 2, y, f"{ticket_name[:35]} | {ticket_price}")
    y -= 1 * cm

    # Reset color
    c.setFillColor(black)

    # Event Name
    c.setFont("Montserrat-Bold", 11)
    c.drawCentredString(width / 2, y, event_name[:35])
    y -= 0.7 * cm

    # Location
    c.setFont("Montserrat", 10)
    location_lines = location.split('\n') if '\n' in location else [location]
    for line in location_lines:
        c.drawCentredString(width / 2, y, line[:40])
        y -= 0.5 * cm

    # Final Text
    y -= 1.2 * cm
    c.setFont("Montserrat", 9)
    c.drawCentredString(width / 2, y, "Faites scanner ce code pour accéder à l'événement")
    y -= 0.4 * cm
    c.drawCentredString(width / 2, y, "Contactez-nous au +229 01 91 11 43 43")

    # Generation date
    c.setFont("Montserrat-MediumItalic", 8)
    generated_on = datetime.now().strftime("Généré le %d/%m/%Y à %Hh%M")
    c.drawCentredString(width / 2, y - 1.2 * cm, generated_on)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
