# -*- coding: utf-8 -*-
"""
Created on April 26 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.contrib.gis import admin

# Register your models here.
from apps.utils.models import Country, Variable, VariableValue, CeleryTask
from commons.admin import BaseModelAdmin


@admin.register(CeleryTask)
class CeleryTaskAdmin(BaseModelAdmin):
    pass


@admin.register(Country)
class CountryAdmin(BaseModelAdmin):
    pass


@admin.register(Variable)
class VariableAdmin(BaseModelAdmin):
    pass


@admin.register(VariableValue)
class VariableValueAdmin(BaseModelAdmin):
    list_filter = ('variable__name', 'variable__label', 'variable__type')
    ordering = ('variable__name', 'timestamp')
    search_fields = ("variable__name",)
