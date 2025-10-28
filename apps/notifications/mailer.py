# -*- coding: utf-8 -*-
"""
Created on June 28 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging
from string import digits

from django.utils.crypto import get_random_string

from apps.notifications.smtp import TemplateEmail

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


def send(params: dict, email_type: str) -> dict:
    email = params["email"]
    full_name = params["full_name"]
    code = params.get("code", None) or get_random_string(length=6, allowed_chars=digits)
    match email_type:
        case "welcome":
            context = {
                "fullName": full_name,
            }
            template_name = "welcome_email"
            subject = "Wulo Events Bienvenu."
        case "account_validation_request":
            context = {
                "fullName": full_name,
                "wuloEventsAccountValidationCode": code,
                "wuloEventsAccountValidationCodeExpiryTime": "10 minutes",
            }
            template_name = "account_validation_email"
            subject = "Validation de  de Compte"
        case "password_reset_request":
            context = {
                "fullName": full_name,
                "wuloEventsPasswordChangeRequestValidationCode": code,
                "wuloEventsPasswordChangeRequestValidationCodeExpiryTime": "10 minutes",
            }
            template_name = "password_reset_request_email"
            subject = "Confirmation de la demande de changement de mot de passe"
        case "password_reset_successful":
            context = {
                "fullName": full_name,
            }
            template_name = "password_reset_successful_email"
            subject = "Changement de mot de passe effectué avec succès"
        case _:
            raise ValueError("Email send type is not valid")

    try:
        template = TemplateEmail(
            to=email,
            subject=subject,
            template=template_name,
            context=context,
            from_email="WuloEvents <info@wuloevents.com>",
        )
        template.send()
    except Exception as exc:
        logger.exception(exc.__str__())

    return {"code": code}
