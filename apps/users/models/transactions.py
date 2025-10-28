# -*- coding: utf-8 -*-
"""
Created on July 11, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import datetime
import logging
from decimal import Decimal, ROUND_UP

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.crypto import get_random_string
from model_utils import FieldTracker
from rest_framework.exceptions import APIException
from simple_history.models import HistoricalRecords

from apps.users.models.utils import get_transaction_default_last_webhook_data, get_transaction_default_coupon_metadata
from apps.users.transactions.payments import PaymentAdapter
from apps.utils.models import CeleryTask
from apps.xlib.enums import (
    TransactionKindEnum,
    TransactionStatusEnum,
    TRANSACTIONS_POSSIBLE_GATEWAYS,
    PAYMENT_METHOD, )
from commons.models import AbstractCommonBaseModel

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class Transaction(AbstractCommonBaseModel):
    type = models.CharField(
        verbose_name="Type de la transaction",
        max_length=220,
        choices=TransactionKindEnum.items(),
    )
    status = models.CharField(
        verbose_name="Statut de la transaction",
        max_length=220,
        choices=TransactionStatusEnum.items(),
        default=TransactionStatusEnum.PENDING.value,
    )
    date = models.DateTimeField(
        verbose_name="Date d' inscription", auto_now_add=True, auto_now=False
    )
    description = models.CharField(max_length=255, blank=True, null=True)
    gateway_id = models.CharField(
        verbose_name="Approbation du réseau (ID)",
        max_length=255,
        blank=True,
        null=False,
    )
    gateway = models.CharField(
        verbose_name="Passerelle de paiement utilisé",
        max_length=255,
        null=True,
        choices=TRANSACTIONS_POSSIBLE_GATEWAYS.items(),
        default=TRANSACTIONS_POSSIBLE_GATEWAYS.FEDAPAY.value,
    )
    payment_method = models.CharField(
        verbose_name="Méthode de paiement",
        max_length=255,
        null=True,
        choices=PAYMENT_METHOD.items(),
        default=PAYMENT_METHOD.MOMO.value,
    )
    local_id = models.CharField(
        verbose_name="Identifiant local", max_length=255, blank=True, null=True
    )
    user = models.ForeignKey(
        to="users.User",
        on_delete=models.CASCADE,
        blank=False,
        verbose_name="Utilisateur",
        related_name="transactions",
    )
    amount = models.CharField(
        verbose_name="Montant", max_length=128, blank=False, null=False
    )
    entity_id = models.CharField(
        verbose_name="Identifiant de l' entité", max_length=255, blank=True, null=True
    )
    payment_url = models.CharField(
        verbose_name="Lien de paiement", max_length=255, blank=True, null=True
    )
    last_webhook_data = models.JSONField(verbose_name="Dernière données de mise à jour", blank=False, null=False,
                                         default=get_transaction_default_last_webhook_data)
    status_updated_at = models.DateTimeField(verbose_name="Dernière mise à jour de status", blank=True, null=True)

    # coupon_metadata = {
    #     "use_coupon": True,
    #     "coupon_id": str(coupon.pk),
    #     "coupon_code": coupon.code,
    #     "calculation_method": calculation_infos,
    #     "initial_amount": str(amount),
    #     "reduced_amount": str(reduced_amount)
    # }
    coupon_metadata = models.JSONField(verbose_name="Données de réduction",
                                       default=get_transaction_default_coupon_metadata)

    tasks = GenericRelation(CeleryTask)

    tracker = FieldTracker()
    history = HistoricalRecords()

    def __str__(self) -> str:
        return str(
            str(self.date)
            + f", Transaction financière {self.local_id} lié au compte de "
            + self.user.get_full_name()
        )

    @property
    def completed(self):
        return self.status in [
            TransactionStatusEnum.PAID.value, TransactionStatusEnum.CANCELED.value,
            TransactionStatusEnum.FAILED.value, TransactionStatusEnum.RESOLVED.value
        ]

    @property
    def paid(self):
        return self.status in [TransactionStatusEnum.PAID.value, TransactionStatusEnum.RESOLVED.value]

    @property
    def get_name_for_receipt(self):
        return f"{self.user.get_short_name()}-Transaction_{self.local_id}-Du_{datetime.datetime.now().date()}"

    def save(self, *args, **kwargs):
        if self.local_id == "" or self.local_id is None:
            self.local_id = get_random_string(15)
        super().save(*args, **kwargs)

    def process_payment(self):
        if self.gateway in [TRANSACTIONS_POSSIBLE_GATEWAYS.INTERNAL_AUTO.value,
                            TRANSACTIONS_POSSIBLE_GATEWAYS.FREE_SHIPPING.value]:
            self.status = TransactionStatusEnum.RESOLVED.value
            self.save(update_fields=["status"])
            return True

        data = {
            "amount": int(Decimal(self.amount).quantize(Decimal('1.'), rounding=ROUND_UP)),
            "firstname": self.user.first_name,
            "lastname": self.user.last_name,
            "email": self.user.email,
            "transaction_id": str(self.pk)
        }
        payment_adapter = PaymentAdapter(gateway=self.gateway)
        payment_instance = payment_adapter.get_gateway_instance()

        request_response = payment_instance.send_request(**data)
        if not request_response:
            raise APIException("Payment failed")

        self.status = TransactionStatusEnum.IN_PROGRESS.value
        self.gateway_id = request_response.id
        self.payment_url = request_response.payment_url
        self.description = request_response.reference
        self.save()
        return request_response

    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"


__all__ = ['Transaction']
