# -*- coding: utf-8 -*-
"""
Created on 08/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.db import models

from apps.marketing.helpers.discounts.helpers import get_random_code, get_coupon_code_length
from commons.models import AbstractCommonBaseModel


class Coupon(AbstractCommonBaseModel):
    code_length = get_coupon_code_length()

    code = models.CharField(
        max_length=code_length,
        default=get_random_code,
        verbose_name="Code coupon",
        unique=True,
        db_index=True
    )
    discount = models.ForeignKey("marketing.Discount", verbose_name="Réduction associée", related_name="coupons",
                                 on_delete=models.CASCADE)
    usages = models.IntegerField(
        default=0, editable=False, verbose_name="Nombre de fois utilisé"
    )
    is_auto_generated = models.BooleanField(
        default=False, verbose_name="Généré automatiquement", 
        help_text="Indique si ce coupon a été généré automatiquement par le système"
    )

    class Meta:
        verbose_name = "Coupon de Réduction"
        verbose_name_plural = "Coupons de Réduction"

    def __str__(self):
        return f"Coupon de code {self.code} pour la réduction {self.discount.label}"

    def use_coupon(self):
        self.usages += 1
        self.save(update_fields=['usages'])

    def save(self, *args, **kwargs):
        return super(Coupon, self).save(*args, **kwargs)


__all__ = ["Coupon", ]
