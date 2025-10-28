# -*- coding: utf-8 -*-
"""
Created on 12/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.contrib import admin

# Register your models here.
from apps.marketing.models import RegistrationsForNewsletter
from commons.admin import BaseModelAdmin


@admin.register(RegistrationsForNewsletter)
class RegistrationsForNewsletterAdmin(BaseModelAdmin):
    pass


__all__ = ["RegistrationsForNewsletterAdmin", ]
