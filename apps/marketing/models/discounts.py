# -*- coding: utf-8 -*-
"""
Created on 08/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
import logging

from django.db import models

from apps.marketing.managers import DiscountManager
from apps.marketing.models.discount_usages import DiscountUsage
from apps.xlib.enums import DISCOUNT_TARGET_TYPES_ENUM
from commons.models import AbstractCommonBaseModel

logger = logging.getLogger(__name__)


class Discount(AbstractCommonBaseModel):
    # Todo, remove unity constraint and change it by unique together with organization
    label = models.CharField(verbose_name="Label de la reduction", max_length=256, unique=True)
    target_type = models.CharField(verbose_name="Type de réduction", max_length=220,
                                   choices=DISCOUNT_TARGET_TYPES_ENUM.items(),
                                   default=DISCOUNT_TARGET_TYPES_ENUM.TICKET.value)
    # Validity period
    starts_at = models.DateTimeField(verbose_name="Date de début", blank=True, null=True)
    ends_at = models.DateTimeField(verbose_name="Date de fin", blank=True, null=True)

    # Usage of many coupon for the same discount
    is_dynamic = models.BooleanField(verbose_name="Désigne si la reduction est dynamique", default=True)

    # Montant minimal requis pour bénéficier de la réduction
    minimal_amount = models.DecimalField(verbose_name="Montant minimal requis", default=0, max_digits=9,
                                         decimal_places=2, blank=True, null=True)

    # Usage limite count if not usage limite rules defined
    usage_limit = models.BigIntegerField(verbose_name="Limite d' usage", default=None, blank=True, null=True)
    usages_count = models.BigIntegerField(verbose_name="Nombre d' usage", default=0, blank=True, null=True)
    usage_rule = models.OneToOneField(to="marketing.DiscountUsageRule", on_delete=models.SET_NULL,
                                      verbose_name="Règle sur la limite d' usage", blank=True, null=True,
                                      related_name="discount")
    # Validation rule
    validation_rule = models.OneToOneField(to="marketing.DiscountValidationRule", on_delete=models.SET_NULL,
                                           verbose_name="Règle de validation", blank=True, null=True,
                                           related_name="discount"
                                           )
    # Organization that create the discount none if admin
    organization = models.ForeignKey(to="organizations.Organization", on_delete=models.CASCADE,
                                     verbose_name="Organisation relative", blank=True, null=True,
                                     related_name="discounts"
                                     )
    # Field to track if discount should be applied automatically
    is_automatic = models.BooleanField(verbose_name="Appliquer automatiquement", default=False,
                                     help_text="Si activé, la réduction sera appliquée automatiquement aux commandes éligibles")
    # objects = DiscountManager()

    def __str__(self):
        return f"{self.label} pour les ({self.target_type}) "

    class Meta:
        verbose_name = "Reduction"
        verbose_name_plural = "Reductions"


__all__ = ["Discount", "DiscountUsage"]
