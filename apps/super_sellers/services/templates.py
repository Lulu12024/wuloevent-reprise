# -*- coding: utf-8 -*-
"""

    
Templates de messages pour l'envoi automatique de tickets.
"""

import logging
from typing import Dict, List
from django.conf import settings

logger = logging.getLogger(__name__)


class MessageTemplate:
    """Classe de base pour les templates de messages"""
    
    @staticmethod
    def format_ticket_list(etickets: List) -> str:
        """Formate la liste des tickets pour l'affichage"""
        if len(etickets) == 1:
            return f"votre billet électronique"
        else:
            return f"vos {len(etickets)} billets électroniques"


class EmailTemplate:
    """Templates pour les emails d'envoi de tickets"""
    
    @staticmethod
    def get_subject(order, etickets: List) -> str:
        """Génère l'objet de l'email"""
        ticket_text = MessageTemplate.format_ticket_list(etickets)
        event_name = etickets[0].event.name if etickets else "votre événement"
        return f"🎟️ {ticket_text.capitalize()} pour {event_name}"
    
    @staticmethod
    def get_body_text(recipient_name: str, order, etickets: List) -> str:
        """Génère le corps de l'email en texte brut"""
        ticket_text = MessageTemplate.format_ticket_list(etickets)
        event = etickets[0].event if etickets else None
        
        if not event:
            return "Erreur: Aucun ticket trouvé."
        
        # Informations de l'événement
        event_date = event.date.strftime("%d/%m/%Y") if event.date else "Date à confirmer"
        event_time = event.hour.strftime("%Hh%M") if event.hour else ""
        event_location = event.location_name or "Lieu à confirmer"
        
        body = f"""
Bonjour {recipient_name},

Merci pour votre achat ! 🎉

Vous trouverez ci-joint {ticket_text} pour :

📅 Événement : {event.name}
📍 Lieu : {event_location}
🗓️ Date : {event_date}
⏰ Heure : {event_time}

📝 Détails de votre commande :
   • Commande N° : {order.order_id}
   • Nombre de billets : {len(etickets)}
   • Montant payé : {order.item.line_total} F CFA

IMPORTANT :
• Présentez le QR code de chaque billet à l'entrée de l'événement
• Les billets sont nominatifs et non remboursables
• Conservez précieusement vos billets jusqu'au jour de l'événement

💡 Conseils :
✓ Arrivez 30 minutes avant le début de l'événement
✓ Assurez-vous que votre téléphone est chargé pour présenter vos billets
✓ Vous pouvez également imprimer vos billets si nécessaire

📱 Besoin d'aide ?
Contactez notre support : +229 01 91 11 43 43
Email : support@wuloevents.com

Nous vous souhaitons un excellent événement !

L'équipe WuloEvents
"""
        return body.strip()
    
    @staticmethod
    def get_body_html(recipient_name: str, order, etickets: List) -> str:
        """Génère le corps de l'email en HTML"""
        ticket_text = MessageTemplate.format_ticket_list(etickets)
        event = etickets[0].event if etickets else None
        
        if not event:
            return "<p>Erreur: Aucun ticket trouvé.</p>"
        
        # Informations de l'événement
        event_date = event.date.strftime("%d/%m/%Y") if event.date else "Date à confirmer"
        event_time = event.hour.strftime("%Hh%M") if event.hour else ""
        event_location = event.location_name or "Lieu à confirmer"
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vos billets WuloEvents</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #0066cc;
        }}
        .header h1 {{
            color: #0066cc;
            margin: 0;
            font-size: 24px;
        }}
        .event-info {{
            background-color: #f8f9fa;
            border-left: 4px solid #0066cc;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .event-info h2 {{
            color: #0066cc;
            margin-top: 0;
            font-size: 20px;
        }}
        .info-row {{
            display: flex;
            margin: 10px 0;
            align-items: center;
        }}
        .info-icon {{
            font-size: 20px;
            margin-right: 10px;
            min-width: 30px;
        }}
        .order-details {{
            background-color: #fff3cd;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
        }}
        .order-details h3 {{
            margin-top: 0;
            color: #856404;
        }}
        .important-box {{
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
        }}
        .important-box h3 {{
            color: #856404;
            margin-top: 0;
        }}
        .tips-box {{
            background-color: #d1ecf1;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
        }}
        .tips-box h3 {{
            color: #0c5460;
            margin-top: 0;
        }}
        .tips-box ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .tips-box li {{
            margin: 5px 0;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
            color: #6c757d;
            font-size: 14px;
        }}
        .contact {{
            background-color: #e7f3ff;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
            text-align: center;
        }}
        .contact h3 {{
            color: #0066cc;
            margin-top: 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎟️ Vos billets WuloEvents</h1>
            <p>Merci pour votre achat !</p>
        </div>
        
        <p>Bonjour <strong>{recipient_name}</strong>,</p>
        
        <p>Votre commande a été confirmée ! Vous trouverez ci-joint <strong>{ticket_text}</strong> pour :</p>
        
        <div class="event-info">
            <h2>{event.name}</h2>
            <div class="info-row">
                <span class="info-icon">📍</span>
                <span><strong>Lieu :</strong> {event_location}</span>
            </div>
            <div class="info-row">
                <span class="info-icon">🗓️</span>
                <span><strong>Date :</strong> {event_date}</span>
            </div>
            <div class="info-row">
                <span class="info-icon">⏰</span>
                <span><strong>Heure :</strong> {event_time}</span>
            </div>
        </div>
        
        <div class="order-details">
            <h3>📝 Détails de votre commande</h3>
            <p><strong>Commande N° :</strong> {order.order_id}</p>
            <p><strong>Nombre de billets :</strong> {len(etickets)}</p>
            <p><strong>Montant payé :</strong> {order.item.line_total} F CFA</p>
        </div>
        
        <div class="important-box">
            <h3>⚠️ IMPORTANT</h3>
            <ul>
                <li>Présentez le QR code de chaque billet à l'entrée de l'événement</li>
                <li>Les billets sont nominatifs et non remboursables</li>
                <li>Conservez précieusement vos billets jusqu'au jour de l'événement</li>
            </ul>
        </div>
        
        <div class="tips-box">
            <h3>💡 Conseils pratiques</h3>
            <ul>
                <li>✓ Arrivez 30 minutes avant le début de l'événement</li>
                <li>✓ Assurez-vous que votre téléphone est chargé pour présenter vos billets</li>
                <li>✓ Vous pouvez également imprimer vos billets si nécessaire</li>
            </ul>
        </div>
        
        <div class="contact">
            <h3>📱 Besoin d'aide ?</h3>
            <p><strong>Téléphone :</strong> +229 01 91 11 43 43</p>
            <p><strong>Email :</strong> support@wuloevents.com</p>
        </div>
        
        <div class="footer">
            <p>Nous vous souhaitons un excellent événement ! 🎉</p>
            <p><strong>L'équipe WuloEvents</strong></p>
            <p style="font-size: 12px; margin-top: 15px;">
                Cet email a été envoyé automatiquement. Merci de ne pas y répondre directement.
            </p>
        </div>
    </div>
</body>
</html>
"""
        return html.strip()


class WhatsAppTemplate:
    """Templates pour les messages WhatsApp"""
    
    @staticmethod
    def get_message(recipient_name: str, order, etickets: List) -> str:
        """Génère le message WhatsApp"""
        ticket_text = MessageTemplate.format_ticket_list(etickets)
        event = etickets[0].event if etickets else None
        
        if not event:
            return "❌ Erreur: Aucun ticket trouvé."
        
        # Informations de l'événement
        event_date = event.date.strftime("%d/%m/%Y") if event.date else "Date à confirmer"
        event_time = event.hour.strftime("%Hh%M") if event.hour else ""
        event_location = event.location_name or "Lieu à confirmer"
        
        # Message WhatsApp optimisé (court et direct)
        message = f"""
🎟️ *WuloEvents - Vos billets*

Bonjour {recipient_name} ! 👋

Votre commande est confirmée ! ✅
Vous recevrez {ticket_text} par email.

📅 *{event.name}*
📍 {event_location}
🗓️ {event_date} à {event_time}

💰 *Commande {order.order_id}*
• {len(etickets)} billet(s)
• {order.item.line_total} F CFA

⚠️ *Important :*
• Présentez le QR code à l'entrée
• Arrivez 30 min en avance
• Billets non remboursables

📧 Vérifiez votre email pour les billets PDF complets.

💬 Besoin d'aide ? 
📞 +229 01 91 11 43 43

Bon événement ! 🎉
_L'équipe WuloEvents_
"""
        return message.strip()
    
    @staticmethod
    def get_reminder_message(recipient_name: str, event_name: str, event_date: str) -> str:
        """Message de rappel avant l'événement"""
        message = f"""
⏰ *Rappel WuloEvents*

Bonjour {recipient_name} ! 

🎟️ N'oubliez pas votre événement :
*{event_name}*

📅 C'est pour demain : {event_date}

✓ Préparez vos billets
✓ Chargez votre téléphone
✓ Arrivez à l'heure

À très bientôt ! 🎉
"""
        return message.strip()


class SMSTemplate:
    """Templates pour les SMS (optionnel pour l'instant)"""
    
    @staticmethod
    def get_message(recipient_name: str, order, event_name: str) -> str:
        """Message SMS court et concis (160 caractères max recommandé)"""
        message = (
            f"WuloEvents: Billets pour {event_name} confirmés! "
            f"Commande {order.order_id}. "
            f"Vérifiez votre email pour les détails. "
            f"Info: 01911143"
        )
        return message[:160]  # Limite SMS standard


# Fonctions utilitaires pour récupérer les templates
def get_email_template(recipient_name: str, order, etickets: List) -> Dict[str, str]:
    """Récupère tous les éléments d'un email de ticket"""
    return {
        "subject": EmailTemplate.get_subject(order, etickets),
        "body_text": EmailTemplate.get_body_text(recipient_name, order, etickets),
        "body_html": EmailTemplate.get_body_html(recipient_name, order, etickets),
    }


def get_whatsapp_template(recipient_name: str, order, etickets: List) -> str:
    """Récupère le message WhatsApp"""
    return WhatsAppTemplate.get_message(recipient_name, order, etickets)


def get_sms_template(recipient_name: str, order, event_name: str) -> str:
    """Récupère le message SMS"""
    return SMSTemplate.get_message(recipient_name, order, event_name)