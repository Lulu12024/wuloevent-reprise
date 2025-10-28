# -*- coding: utf-8 -*-
"""
Created on 12/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.contrib import admin

# Register your models here.
from apps.marketing.models import ContactsArea
from commons.admin import BaseModelAdmin


@admin.register(ContactsArea)
class ContactsAreaAdmin(BaseModelAdmin):
    pass


__all__ = ["ContactsAreaAdmin", ]
