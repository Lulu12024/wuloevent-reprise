# -*- coding: utf-8 -*-
"""
Created on 12/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.contrib import admin

# Register your models here.
from apps.marketing.models import DiscountUsageRule, DiscountValidationRule
from commons.admin import BaseModelAdmin


@admin.register(DiscountUsageRule)
class DiscountUsageRuleAdmin(BaseModelAdmin):
    pass


@admin.register(DiscountValidationRule)
class DiscountValidationRuleAdmin(BaseModelAdmin):
    pass


__all__ = ["DiscountUsageRuleAdmin", "DiscountValidationRuleAdmin", ]
