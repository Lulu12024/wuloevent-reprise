# -*- coding: utf-8 -*-
"""
Created on July 13, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.db import models

from apps.organizations.models.organizations import Organization
from commons.models import AbstractCommonBaseModel

# Create your models here.

logger = logging.getLogger(__name__)


class OrganizationFinancialAccount(AbstractCommonBaseModel):
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, verbose_name='Utilisateur',
                                        related_name='financial_account')
    balance = models.DecimalField(
        verbose_name='Solde', default=0, max_digits=12, decimal_places=2)

    # percentage = models.DecimalField(
    #    verbose_name="Pourcentage sur vente par ticket", max_digits=15, decimal_places=5, default=3.0)

    def __str__(self) -> str:
        return str("Compte financier de " + self.organization.name)

    def can_withdraw_amount(self, amount: int) -> bool:
        return self.organization.active and self.balance > amount

    class Meta:
        verbose_name = 'Compte financier'
        verbose_name_plural = 'Comptes financiers'


Organization.get_financial_account = property(
    lambda o: OrganizationFinancialAccount.objects.get_or_create(organization=o)[0])
