# -*- coding: utf-8 -*-
"""
Created on April 26 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.contrib import admin

# Register your models here.
from apps.users.models import User, AppRole, AppPermission, Transaction, AccountValidationRequest, ResetPasswordRequest, \
    ZoneOfInterest, PointOfInterest
from commons.admin import BaseModelAdmin


@admin.register(User)
class UserAdmin(BaseModelAdmin):
    list_filter = ('sex', 'is_active', 'is_staff')
    ordering = ('birthday', 'date_joined')
    search_fields = ("first_name", "last_name", "email", "phone")


@admin.register(AppRole)
class AppRoleAdmin(BaseModelAdmin):
    ordering = ('name', 'timestamp')
    search_fields = ("name", "label")


@admin.register(AppPermission)
class AppPermissionAdmin(BaseModelAdmin):
    ordering = ("entity", 'name', 'timestamp')
    search_fields = ("name", "codename")
    list_filter = ('entity', 'method')


@admin.register(Transaction)
class TransactionAdmin(BaseModelAdmin):
    list_filter = ('type', 'status', 'gateway', 'user')
    search_fields = ("description", "gateway_id", "local_id", "entity_id")

    ordering = ['-timestamp']


@admin.register(AccountValidationRequest)
class AccountValidationRequestAdmin(BaseModelAdmin):
    pass


@admin.register(ResetPasswordRequest)
class ResetPasswordRequestAdmin(BaseModelAdmin):
    pass


@admin.register(ZoneOfInterest)
class ZoneOfInterestAdmin(BaseModelAdmin):
    pass


@admin.register(PointOfInterest)
class PointOfInterestAdmin(BaseModelAdmin):
    pass
