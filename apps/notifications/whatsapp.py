"""
Created on November 5, 2025
@author:
    Beaudelaire LAHOUME, alias root-lr
"""
from django.conf import settings
from apps.notifications.gupshup import GupshupWhatsAppClient

client = GupshupWhatsAppClient()

def send_simple_text(phone: str, text: str):
    return client.send_text(phone, text)

def send_ticket_pdf_link(phone: str, file_url: str, caption: str = "Voici votre e-ticket 🎫"):
    return client.send_media_url(phone, media_type="document", url=file_url, caption=caption)

def send_sale_receipt_template(phone: str, order_id: str, total: str, event_name: str):
    params = [order_id, total, event_name]
    return client.send_template(phone, template_name="sale_receipt", language="fr", params=params)

