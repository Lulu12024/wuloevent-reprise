# -*- coding: utf-8 -*-
"""
Created on July 11, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging
from decimal import Decimal, ROUND_UP

from django.db import models
from model_utils import FieldTracker
from rest_framework.exceptions import APIException
from simple_history.models import HistoricalRecords

from apps.users.transactions.withdraws import WithdrawAdapter
from apps.utils.validators import PhoneNumberValidator
from apps.xlib.enums import (
    WithdrawStatusEnum, WithdrawMethodEnum,
)
from commons.models import AbstractCommonBaseModel

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class Withdraw(AbstractCommonBaseModel):
    # FREE_MONEY_SENEGAL = 'free-money-senegal'
    # EXPRESSO_SENEGAL = 'expresso-senegal'
    # MTN_CI = 'mtn-ci'
    # MOOV_CI = 'moov-ci'
    # T_MONEY_TOGO = 't-money-togo'
    # ORANGE_MONEY_CI = 'orange-money-ci'

    amount = models.CharField(
        verbose_name="Montant", max_length=128, blank=False, null=False
    )
    method = models.CharField(
        verbose_name="Moyen Utilisé Pour la transaction",
        max_length=220,
        choices=WithdrawMethodEnum.items(),
        blank=False,
    )
    disburse_token = models.CharField(
        verbose_name="Token de retrait", max_length=220, blank=True
    )
    payment_phone = models.CharField(
        verbose_name="Numéro de téléphone",
        max_length=25,
        blank=False,
        null=False,
        validators=[PhoneNumberValidator()],
    )
    organization = models.ForeignKey(
        to="organizations.Organization",
        verbose_name="Compte Financier Relatif",
        related_name="withdraws",
        on_delete=models.DO_NOTHING,
    )

    status = models.CharField(
        max_length=120, choices=WithdrawStatusEnum.items(), default=WithdrawStatusEnum.CREATED.value
    )

    tracker = FieldTracker()
    history = HistoricalRecords()

    @property
    def completed(self):
        return self.status in [WithdrawStatusEnum.FINISHED.value, WithdrawStatusEnum.FAILED.value]

    @property
    def paid(self):
        return self.status == WithdrawStatusEnum.FINISHED.value

    def process(self):
        mode = {"MTN_BENIN": "mtn_open", "MOOV_BENIN": "moov"}
        data = {
            "amount": int(Decimal(self.amount).quantize(Decimal('1.'), rounding=ROUND_UP)),
            "withdraw_mode": mode[self.method],
            "firstname": self.organization.name,
            "lastname": self.organization.name,
            "email": self.organization.email,
            "phone": self.payment_phone,
        }

        logger.warning(data)

        withdraw_adapter = WithdrawAdapter()
        withdraw_instance = withdraw_adapter.get_gateway_instance()

        initialization = withdraw_instance.initialize(**data)
        logger.warning(initialization)

        if not initialization:
            raise APIException("Withdraw failed")

        self.status = WithdrawStatusEnum.INITIALIZED.value
        self.save()

        return initialization

    def disburse(self, gateway_id: str):
        withdraw_adapter = WithdrawAdapter()
        withdraw_instance = withdraw_adapter.get_gateway_instance()

        withdraw_instance.disburse(**{"transaction_id": gateway_id})
        self.status = WithdrawStatusEnum.PROCESSING.value
        self.save()

    def can_be_processed(self):
        financial_account = self.organization.get_financial_account
        return financial_account.can_withdraw_amount(int(self.amount))

    def update_user_financial_account(self):
        financial_account = self.organization.get_financial_account
        financial_account.balance -= Decimal(self.amount)
        financial_account.save()

    def __str__(self) -> str:
        return f"Retrait du compte financier de l' organisation {self.organization.__str__()}"

    class Meta:
        verbose_name = "Paiement de Retrait"
        verbose_name_plural = "Paiements de Retraits"
