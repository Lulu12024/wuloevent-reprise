# -*- coding: utf-8 -*-
"""
Created on July 14, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import json
import logging
from typing import Tuple, Any

from cryptography.fernet import Fernet
from django.db import models
from django.utils.encoding import force_bytes, force_str as force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from commons.models import AbstractCommonBaseModel

logger = logging.getLogger(__name__)


class ETicket(AbstractCommonBaseModel):
    event = models.ForeignKey(
        to="events.Event",
        verbose_name="Évènement connexe",
        related_name="e_tickets",
        on_delete=models.DO_NOTHING,
    )
    ticket = models.ForeignKey(
        to="events.Ticket",
        verbose_name="Ticket connexe",
        related_name="e_tickets",
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
    )
    # old_related_order_id = models.CharField(max_length=120, verbose_name="Commende relative")
    related_order = models.ForeignKey(to="events.Order", verbose_name="Commende relative",
                                      related_name="related_e_tickets", on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=220, blank=True, verbose_name="Nom")
    secret_key = models.BinaryField(max_length=256, blank=True, editable=True, verbose_name="Clé secrete")
    secret_phrase = models.CharField(max_length=1024, blank=True, verbose_name="Secret")
    qr_code_data = models.CharField(max_length=512, blank=True, verbose_name="Données de QR code")
    expiration_date = models.DateTimeField(blank=True, verbose_name="Date d' expiration")
    is_downloaded = models.BooleanField(default=False, verbose_name="Désigne si le ticket a été téléchargé")

    def __str__(self) -> str:
        return f"{self.name}"

    @staticmethod
    def format_name(event):
        return f"E-Ticket N° {len(ETicket.objects.filter(event=event)) + 1} | {event.__str__()} "

    def format_informations(self):
        return f"{self.name} @ {int(round(self.expiration_date.timestamp()))}"

    def make_qr_code_data(self):
        fernet = Fernet(bytes(self.secret_key))
        encode_secret_phrase = fernet.encrypt(force_bytes(self.secret_phrase))
        return json.dumps(
            {
                "id64": urlsafe_base64_encode(force_bytes(self.pk)),
                "secret_phrase": force_text(encode_secret_phrase),
            }
        )

    @staticmethod
    def verify_secret_phrase(data, organization_pk: str = None) -> Tuple[bool, Any]:
        """
            Used to verify e-ticket data. data param is the data got from scanning an e-ticket.
            Return the E - ticket instance if found, and whether the secret phrase is valid
        :param data:{id64, secret_phrase}
        :param organization_pk:
        :return: ( bool, ETicket | None )
        """
        try:
            instance_id = urlsafe_base64_decode(force_text(data.get("id64")))
            instance_id = instance_id.decode() if type(instance_id) is bytes else instance_id
            query_kwargs = {"pk": instance_id}
            if organization_pk:
                query_kwargs["event__organization_id"] = organization_pk

            instance = ETicket.objects.get(**query_kwargs)
            fernet = Fernet(bytes(instance.secret_key))
            secret_phrase = force_text(
                fernet.decrypt(force_bytes(data.get("secret_phrase")))
            )
            return instance.secret_phrase == secret_phrase, instance
        except Exception as exc:
            logger.warning(exc)
            return False, None

    def set_secret_phrase(self):
        self.secret_phrase = self.format_informations()

    def set_name(self):
        self.name = self.format_name(self.event)

    def save(self, *args, **kwargs):
        if self.name is None or self.name == "":
            self.set_name()

        if self.secret_key is None or self.secret_key == b"":
            self.secret_key = Fernet.generate_key()

        if self.secret_phrase is None or self.secret_phrase == "":
            self.set_secret_phrase()

        return super().save(*args, **kwargs)

    def generate_qr_code(self):
        self.qr_code_data = self.make_qr_code_data()
        self.save()

    class Meta:
        verbose_name = "E-ticket"
        verbose_name_plural = "E-tickets"
