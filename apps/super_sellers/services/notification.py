# -*- coding: utf-8 -*-
"""
Created on October 29, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

import logging

logger = logging.getLogger(__name__)

def notify_seller_stock_allocated(seller, stock, quantity):
    """
    Tampon de notification (email/SMS/WhatsApp).
    Branche tes intégrations ici (sendgrid, twilio, whatsapp, etc.).
    """
    try:
        # TODO: implémentations spécifiques
        # send_invitation_email(...) / 

        # #send_sms(...) / 

        # #send_whatsapp(...)

        logger.info(
            f"[NOTIFY] Stock alloué: seller={seller.id} event={stock.event_id} "
            f"ticket={stock.ticket_id} qty={quantity}"
        )
    except Exception as e:
        logger.exception(f"Notification seller stock failed: {e}")
