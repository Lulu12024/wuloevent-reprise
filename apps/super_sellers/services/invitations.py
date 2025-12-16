# -*- coding: utf-8 -*-
"""
Created on October 29, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

# -*- coding: utf-8 -*-
"""
Created on October 29, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

import logging
from typing import Dict
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from apps.notifications.whatsapp import send_simple_text
from apps.notifications.gupshup import GupshupError

logger = logging.getLogger(__name__)


class SellerInvitationService:
    """
    Service pour l'envoi d'invitations vendeur.
    """
    
    @staticmethod
    def send_invitation_email(invitation) -> bool:
        """
        Envoie une invitation par email avec boutons Accepter/Décliner.
        
        Args:
            invitation: Instance de SellerInvitation
            
        Returns:
            True si envoi réussi, False sinon
        """
        try:
            # URL de base pour les actions
            frontend_url = getattr(settings, 'FRONTEND_URL', 'https://wuloevents.com')
            accept_url = f"{frontend_url}/seller/invitation/{invitation.token}/accept"
            decline_url = f"{frontend_url}/seller/invitation/{invitation.token}/decline"
            
            # Informations sur l'organisation
            org_name = invitation.super_seller.name
            invited_by_name = invitation.invited_by.get_full_name() if invitation.invited_by else "L'équipe"
            expires_at = invitation.expires_at.strftime("%d/%m/%Y à %H:%M")
            
            # Message personnalisé si présent
            custom_message = ""
            if invitation.message:
                custom_message = f"""
                    <div style="background-color: #f8f9fa; border-left: 4px solid #0066cc; padding: 15px; margin: 20px 0; border-radius: 5px;">
                        <p style="margin: 0; font-style: italic;">"{invitation.message}"</p>
                    </div>
                """
            
            # Sujet
            subject = f"🎟️ Invitation - Devenir vendeur pour {org_name}"
            
            # Corps texte brut
            body_text = f"""
Invitation à devenir vendeur - WuloEvents

Bonjour,

{invited_by_name} de {org_name} vous invite à rejoindre leur équipe de vendeurs sur WuloEvents !

En acceptant cette invitation, vous pourrez :
• Vendre des billets pour les événements de {org_name}
• Gérer votre stock de tickets
• Suivre vos ventes en temps réel
• Retirer vos gains facilement

Pour accepter cette invitation, cliquez sur ce lien :
{accept_url}

Pour décliner, utilisez ce lien :
{decline_url}

⚠️ Cette invitation expire le {expires_at}

Pour toute question, contactez-nous :
📞 +229 01 91 11 43 43
📧 support@wuloevents.com

L'équipe WuloEvents
            """.strip()
            
            # Corps HTML
            body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Invitation Vendeur - WuloEvents</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 600px;">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #0066cc 0%, #004999 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                            <h1 style="color: white; margin: 0; font-size: 28px;">🎟️ Invitation Vendeur</h1>
                            <p style="color: #e3f2fd; margin: 10px 0 0 0; font-size: 16px;">WuloEvents</p>
                        </td>
                    </tr>
                    
                    <!-- Contenu principal -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="font-size: 16px; color: #333; line-height: 1.6; margin-top: 0;">
                                Bonjour,
                            </p>
                            
                            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                                <strong>{invited_by_name}</strong> de <strong style="color: #0066cc;">{org_name}</strong> 
                                vous invite à rejoindre leur équipe de vendeurs sur WuloEvents ! 🎉
                            </p>
                            
                            {custom_message}
                            
                            <!-- Avantages -->
                            <div style="background-color: #e7f3ff; border-radius: 8px; padding: 20px; margin: 25px 0;">
                                <h3 style="color: #0066cc; margin-top: 0; font-size: 18px;">✨ En devenant vendeur, vous pourrez :</h3>
                                <ul style="color: #333; line-height: 1.8; margin: 15px 0; padding-left: 20px;">
                                    <li>Vendre des billets pour les événements de <strong>{org_name}</strong></li>
                                    <li>Gérer votre stock de tickets en temps réel</li>
                                    <li>Suivre vos ventes et commissions</li>
                                    <li>Retirer vos gains facilement via Mobile Money</li>
                                    <li>Accéder à un espace vendeur dédié</li>
                                </ul>
                            </div>
                            
                            <!-- Boutons d'action -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
                                <tr>
                                    <td align="center">
                                        <table cellpadding="0" cellspacing="0">
                                            <tr>
                                                <!-- Bouton Accepter -->
                                                <td style="padding: 0 10px;">
                                                    <a href="{accept_url}" 
                                                       style="display: inline-block; 
                                                              background: linear-gradient(135deg, #28a745 0%, #218838 100%); 
                                                              color: white; 
                                                              text-decoration: none; 
                                                              padding: 15px 40px; 
                                                              border-radius: 8px; 
                                                              font-weight: bold; 
                                                              font-size: 16px;
                                                              box-shadow: 0 4px 6px rgba(40, 167, 69, 0.3);
                                                              transition: all 0.3s ease;">
                                                        ✅ Accepter l'invitation
                                                    </a>
                                                </td>
                                                
                                                <!-- Bouton Décliner -->
                                                <td style="padding: 0 10px;">
                                                    <a href="{decline_url}" 
                                                       style="display: inline-block; 
                                                              background-color: #f8f9fa; 
                                                              color: #6c757d; 
                                                              text-decoration: none; 
                                                              padding: 15px 40px; 
                                                              border-radius: 8px; 
                                                              font-weight: bold; 
                                                              font-size: 16px;
                                                              border: 2px solid #dee2e6;">
                                                        ❌ Décliner
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Note d'expiration -->
                            <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 25px 0; border-radius: 5px;">
                                <p style="margin: 0; color: #856404; font-size: 14px;">
                                    ⏰ <strong>Attention :</strong> Cette invitation expire le <strong>{expires_at}</strong>
                                </p>
                            </div>
                            
                            <!-- Liens alternatifs si boutons ne marchent pas -->
                            <p style="font-size: 13px; color: #6c757d; line-height: 1.6; margin-top: 25px; padding-top: 20px; border-top: 1px solid #dee2e6;">
                                Si les boutons ci-dessus ne fonctionnent pas, copiez et collez ces liens dans votre navigateur :
                                <br><br>
                                <strong>Accepter :</strong> <a href="{accept_url}" style="color: #0066cc; word-break: break-all;">{accept_url}</a>
                                <br>
                                <strong>Décliner :</strong> <a href="{decline_url}" style="color: #0066cc; word-break: break-all;">{decline_url}</a>
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Support -->
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 25px 30px; border-top: 1px solid #dee2e6;">
                            <h3 style="color: #0066cc; margin-top: 0; font-size: 16px; text-align: center;">📱 Besoin d'aide ?</h3>
                            <p style="text-align: center; margin: 10px 0; color: #333; font-size: 14px;">
                                <strong>Téléphone :</strong> +229 01 91 11 43 43<br>
                                <strong>Email :</strong> support@wuloevents.com<br>
                                <strong>Site web :</strong> <a href="https://wuloevents.com" style="color: #0066cc;">wuloevents.com</a>
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #0066cc; padding: 20px; text-align: center; border-radius: 0 0 10px 10px;">
                            <p style="color: white; margin: 0; font-size: 14px;">
                                <strong>WuloEvents</strong> - Votre plateforme de billetterie
                            </p>
                            <p style="color: #e3f2fd; margin: 5px 0 0 0; font-size: 12px;">
                                © 2025 WuloEvents. Tous droits réservés.
                            </p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
            """
            
            # Créer et envoyer l'email
            email = EmailMultiAlternatives(
                subject=subject,
                body=body_text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[invitation.email],
            )
            
            email.attach_alternative(body_html, "text/html")
            email.send()
            
            # Mettre à jour l'invitation
            invitation.sent_at = timezone.now()
            invitation.save(update_fields=['sent_at'])
            
            logger.info(f"✅ Email d'invitation envoyé à {invitation.email}")
            return True
            
        except Exception as e:
            logger.exception(f"❌ Erreur envoi email invitation à {invitation.email}: {e}")
            return False
    
    @staticmethod
    def send_invitation_whatsapp(invitation) -> Dict[str, any]:
        """
        Envoie une invitation par WhatsApp.
        
        Args:
            invitation: Instance de SellerInvitation
            
        Returns:
            Dict avec success, message_id ou error
        """
        try:
            if not invitation.phone:
                logger.warning(f"⚠️ Pas de numéro de téléphone pour l'invitation {invitation.id}")
                return {"success": False, "error": "Pas de numéro de téléphone"}
            
            # URL pour accepter/décliner
            frontend_url = getattr(settings, 'FRONTEND_URL', 'https://wuloevents.com')
            invitation_url = f"{frontend_url}/seller/invitation/{invitation.token}"
            
            # Informations
            org_name = invitation.super_seller.name
            invited_by_name = invitation.invited_by.get_full_name() if invitation.invited_by else "L'équipe"
            expires_at = invitation.expires_at.strftime("%d/%m/%Y à %H:%M")
            
            # Construire le message WhatsApp
            message = f"""🎟️ *Invitation Vendeur - WuloEvents*

Bonjour ! 👋

*{invited_by_name}* de *{org_name}* vous invite à rejoindre leur équipe de vendeurs ! 🎉
"""
            
            # Ajouter message personnalisé si présent
            if invitation.message:
                message += f'\n📝 _{invitation.message}_\n'
            
            message += f"""
✨ *Avantages vendeur :*
✅ Vendez des billets pour {org_name}
✅ Gérez votre stock en temps réel
✅ Suivez vos ventes et commissions
✅ Retirez vos gains via Mobile Money
✅ Espace vendeur dédié

🔗 *Acceptez l'invitation ici :*
{invitation_url}

⏰ Expire le : {expires_at}

💬 Questions ? Contactez-nous :
📞 +229 01 91 11 43 43
📧 support@wuloevents.com

---
_WuloEvents - Votre plateforme de billetterie_
"""
            
            # Envoyer via Gupshup
            result = send_simple_text(
                phone=invitation.phone,
                text=message.strip()
            )
            
            # Mettre à jour l'invitation
            invitation.sent_at = timezone.now()
            invitation.save(update_fields=['sent_at'])
            
            logger.info(
                f"✅ WhatsApp d'invitation envoyé à {invitation.phone} "
                f"(message_id: {result.get('messageId')})"
            )
            
            return {
                "success": True,
                "message_id": result.get('messageId'),
                "phone": invitation.phone
            }
            
        except GupshupError as e:
            logger.error(f"❌ Erreur Gupshup pour invitation {invitation.id}: {e}")
            return {
                "success": False,
                "error": f"Erreur Gupshup: {str(e)}"
            }
        except Exception as e:
            logger.exception(f"❌ Erreur envoi WhatsApp invitation {invitation.id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def send_invitation_sms(invitation) -> Dict[str, any]:
        """
        Envoie une invitation par SMS.
        (Placeholder pour future implémentation)
        
        Args:
            invitation: Instance de SellerInvitation
            
        Returns:
            Dict avec success et message
        """
        # TODO: Implémenter l'envoi SMS plus tard
        logger.info(f"TODO: Envoi SMS pour invitation {invitation.id}")
        
        return {
            "success": False,
            "error": "Service SMS pas encore implémenté"
        }
    
    @staticmethod
    def send_invitation(invitation) -> Dict[str, any]:
        """
        Envoie une invitation via le canal approprié.
        
        Args:
            invitation: Instance de SellerInvitation
            
        Returns:
            Dict avec résultat de l'envoi
        """
        from apps.super_sellers.models import InvitationChannel
        
        if invitation.channel == InvitationChannel.EMAIL:
            success = SellerInvitationService.send_invitation_email(invitation)
            return {
                "success": success,
                "channel": "EMAIL",
                "recipient": invitation.email
            }
            
        elif invitation.channel == InvitationChannel.WHATSAPP:
            result = SellerInvitationService.send_invitation_whatsapp(invitation)
            result["channel"] = "WHATSAPP"
            return result
            
        elif invitation.channel == InvitationChannel.SMS:
            result = SellerInvitationService.send_invitation_sms(invitation)
            result["channel"] = "SMS"
            return result
            
        else:
            return {
                "success": False,
                "error": f"Canal non supporté: {invitation.channel}"
            }


# Fonctions raccourcies pour import facile
def send_invitation_email(invitation):
    """Envoie une invitation par email"""
    return SellerInvitationService.send_invitation_email(invitation)


def send_invitation_whatsapp(invitation):
    """Envoie une invitation par WhatsApp"""
    return SellerInvitationService.send_invitation_whatsapp(invitation)


def send_invitation_sms(invitation):
    """Envoie une invitation par SMS"""
    return SellerInvitationService.send_invitation_sms(invitation)


def send_invitation(invitation):
    """Envoie une invitation via le canal approprié"""
    return SellerInvitationService.send_invitation(invitation)