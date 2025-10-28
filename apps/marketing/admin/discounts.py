# -*- coding: utf-8 -*-
"""
Created on 12/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.contrib import admin

# Register your models here.
from apps.marketing.models import Discount, DiscountUsage
from commons.admin import BaseModelAdmin


@admin.register(Discount)
class DiscountAdmin(BaseModelAdmin):
    pass


@admin.register(DiscountUsage)
class DiscountUsageAdmin(BaseModelAdmin):
    pass


__all__ = ["DiscountAdmin", "DiscountUsageAdmin", ]
