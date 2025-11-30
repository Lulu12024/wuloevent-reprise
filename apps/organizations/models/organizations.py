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

from apps.organizations.managers import OrganisationManager
from apps.utils.models import Variable
from apps.utils.utils import _upload_to
from apps.utils.validators import PhoneNumberValidator
from apps.xlib.enums import VARIABLE_NAMES_ENUM
from commons.models import AbstractCommonBaseModel

# Create your models here.

logger = logging.getLogger(__name__)


class Organization(AbstractCommonBaseModel):
    name = models.CharField(
        verbose_name="Nom de l'organisation", max_length=70, blank=False
    )
    email = models.EmailField(
        verbose_name="Adresse mail de l'entreprise", blank=True, null=True
    )
    phone = models.CharField(
        verbose_name="Numéro de téléphone",
        max_length=25,
        default="+22900000000",
        blank=False,
        null=False,
        validators=[PhoneNumberValidator()],
    )
    description = models.CharField(
        max_length=255,
        verbose_name="Description de l'entreprise",
        blank=True,
        null=True,
    )
    address = models.CharField(
        max_length=512, verbose_name="Adresse de l'entreprise", blank=True, null=True
    )
    logo = models.ImageField(
        verbose_name="Logo de l' entreprise", upload_to=_upload_to, blank=True
    )
    owner = models.ForeignKey(
        "users.User",
        on_delete=models.DO_NOTHING,
        null=False,
        blank=False,
        related_name="organizations_own",
    )
    country = models.ForeignKey(
        to="utils.Country",
        blank=True,
        null=True,
        verbose_name="Pays de résidence",
        on_delete=models.SET_NULL,
    )
    subscribe_until = models.DateField(null=True, blank=True)
    objects = OrganisationManager()
    phone_number_validated = models.BooleanField(default=False)
    percentage = models.FloatField(
        verbose_name="Pourcentage de Wulo Events", blank=True, null=True, default=None
    )
    percentage_if_discounted = models.FloatField(
        verbose_name="Pourcentage de Wulo Events", blank=True, null=True, default=None
    )

    history = HistoricalRecords()

    class Meta:
        pass

    @property
    def have_active_subscription(self):
        now = datetime.datetime.now()
        return self.subscriptions.filter(
            start_date__lte=now, end_date__gte=now, active_status=True
        ).exists()

    def is_owner(self, user):
        return user == self.owner

    def set_subscribe_until(self, end_date_or_timestamp):
        if isinstance(end_date_or_timestamp, int):
            # input date as timestamp integer
            subscribe_until = datetime.date.fromtimestamp(end_date_or_timestamp)
        elif isinstance(end_date_or_timestamp, str):
            # input date as timestamp string
            subscribe_until = datetime.date.fromtimestamp(int(end_date_or_timestamp))
        else:
            subscribe_until = end_date_or_timestamp

        self.subscribe_until = subscribe_until
        self.save(update_fields=["subscribe_until"])

    def get_retribution_percentage(self, for_discounted_sales: bool = False):
        if for_discounted_sales and self.percentage_if_discounted:
            return self.percentage_if_discounted
        elif not for_discounted_sales and self.percentage:
            return self.percentage

        percentage_variable_name = (
            "PERCENTAGE_ABOUT_A_TICKET_SELLING_WITH_DISCOUNT"
            if for_discounted_sales
            else "PERCENTAGE_ABOUT_A_TICKET_SELLING"
        )

        percentage_variable = Variable.objects.get(
            name=VARIABLE_NAMES_ENUM[percentage_variable_name].value
        )
        percentage_value = percentage_variable.format_value(
            percentage_variable.possible_values.first().value
        )
        return percentage_value

    @property
    def is_owner_verified(self):
        return self.owner.is_active and self.owner.have_validate_account

    @property
    def get_entity_info(self):
        return {"name": self.name}

    def __str__(self) -> str:
        return f"{self.name} créé par {self.owner.get_full_name()}"
