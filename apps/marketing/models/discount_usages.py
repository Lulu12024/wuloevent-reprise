# -*- coding: utf-8 -*-
"""
Created on 16/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.db import models

from apps.xlib.enums import DISCOUNT_USE_ENTITY_TYPES_ENUM
from commons.models import AbstractCommonBaseModel


class DiscountUsage(AbstractCommonBaseModel):
    entity_id = models.CharField(verbose_name="Id de l' entité", max_length=128)
    entity_type = models.CharField(verbose_name="Type de l' entité", max_length=220,
                                   choices=DISCOUNT_USE_ENTITY_TYPES_ENUM.items())
    discount = models.ForeignKey(
        "Discount", on_delete=models.CASCADE, verbose_name="Réductions", related_name="usages"
    )
    usages = models.IntegerField(
        default=0, editable=False, verbose_name="Utilisation"
    )

    def __str__(self):
        return str(self.entity_type)

    class Meta:
        verbose_name = "Utilisation de réduction"
        verbose_name_plural = "Utilisations de réduction"


__all__ = ["DiscountUsage"]
