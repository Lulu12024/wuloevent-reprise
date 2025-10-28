# -*- coding: utf-8 -*-
"""
Created on April 26, 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.contrib import admin

# Register your models here.
from apps.marketing.models import RegistrationsForNewsletter, ContactsArea
from commons.admin import BaseModelAdmin


@admin.register(RegistrationsForNewsletter)
class RegistrationsForNewsletterAdmin(BaseModelAdmin):
    pass


@admin.register(ContactsArea)
class ContactsAreaAdmin(BaseModelAdmin):
    pass
