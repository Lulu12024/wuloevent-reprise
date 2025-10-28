# -*- coding: utf-8 -*-
"""
Created on 12/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.contrib import admin

# Register your models here.
from apps.marketing.models import Coupon
from commons.admin import BaseModelAdmin


@admin.register(Coupon)
class CouponAdmin(BaseModelAdmin):
    pass


__all__ = ["CouponAdmin"]
