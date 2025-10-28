# -*- coding: utf-8 -*-
"""
Created on July 13, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import datetime
import logging

from django.db import models
from simple_history.models import HistoricalRecords

from apps.organizations.managers import SubscriptionManager
from apps.users.models import Transaction
from apps.xlib.enums import TransactionKindEnum
from commons.models import AbstractCommonBaseModel

# Create your models here.

logger = logging.getLogger(__name__)


class SubscriptionType(AbstractCommonBaseModel):
    # Todo: Add a field for handling efault selected subscription type
    name = models.CharField(verbose_name="Nom", max_length=128)
    price = models.DecimalField(
        verbose_name="Prix", max_digits=15, default=1000.00, decimal_places=2
    )
    validity_days_range = models.IntegerField(
        verbose_name="Nombre de jours de validité", blank=True, null=False
    )
    order = models.SmallIntegerField(default=1, verbose_name="Ordre")

    def __str__(self) -> str:
        return str("Abonnement de type " + self.name)

    def get_purchase_cost(self, quantity: int):
        return self.price * quantity

    @property
    def get_entity_info(self):
        return {"name": self.name}

    class Meta:
        verbose_name = "Type d' abonnement"
        verbose_name_plural = "Types d' abonnements"
        ordering = ("order",)


class Subscription(AbstractCommonBaseModel):
    organization = models.ForeignKey(
        to="organizations.Organization",
        verbose_name="Organisation",
        related_name="subscriptions",
        on_delete=models.DO_NOTHING,
    )
    subscription_type = models.ForeignKey(
        to=SubscriptionType,
        verbose_name="Type d' abonnement",
        related_name="subscriptions",
        on_delete=models.DO_NOTHING,
    )
    start_date = models.DateField(verbose_name="Date de début de validité", blank=True)
    end_date = models.DateField(verbose_name="Date de fin de validité", blank=True)
    unity_time_number = models.PositiveIntegerField(
        default=1, verbose_name="Nombre d' unité de temps."
    )
    date = models.DateTimeField(
        verbose_name="Date d' activation", auto_now_add=True, auto_now=False
    )
    updated = models.DateTimeField(
        verbose_name="Date de modification", auto_now_add=False, auto_now=True
    )
    active_status = models.BooleanField(default=False)

    objects = SubscriptionManager()
    history = HistoricalRecords()

    def __str__(self) -> str:
        return str(
            "Abonnement de "
            + self.organization.name
            + " le "
            + str(self.date.date())
            + " à "
            + str(self.date.time())
        )

    @property
    def name(self):
        return str(
            "Abonnement de "
            + self.organization.name
            + " le "
            + str(self.date.strftime('%d/%m/%Y  à  %H:%M '))
        )

    @property
    def get_entity_info(self):
        return {"name": self.name}

    @property
    def active(self):
        subscription_paid = False
        try:
            related_subscription_transaction = Transaction.objects.get(type=TransactionKindEnum.SUBSCRIPTION.value,
                                                                       entity_id=self.pk)
            subscription_paid = related_subscription_transaction.paid

        except Exception as exc:
            logger.info(exc.__str__())

        now = datetime.datetime.now()

        computed_status = (
                subscription_paid and self.start_date <= now.date() <= self.end_date
        )
        if computed_status != self.active_status:
            self.active_status = computed_status
            self.save()

        return self.active_status

    def save(self, *args, **kwargs) -> None:
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Abonnement"
        verbose_name_plural = "Abonnements"
