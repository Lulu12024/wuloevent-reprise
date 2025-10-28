# -*- coding: utf-8 -*-
"""
Created on March 17, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.contrib import admin

# Register your models here.
from apps.organizations.models import Role, Organization, OrganizationFinancialAccount, OrganizationMembership, \
    OrganizationFollow, Subscription, SubscriptionType, Withdraw
from commons.admin import BaseModelAdmin


@admin.register(Role)
class RoleAdmin(BaseModelAdmin):
    pass


@admin.register(OrganizationFollow)
class OrganizationFollowAdmin(BaseModelAdmin):
    pass


@admin.register(Withdraw)
class WithdrawAdmin(BaseModelAdmin):
    pass


@admin.register(Organization)
class OrganizationAdmin(BaseModelAdmin):
    search_fields = ['name', 'email', 'phone', 'description', 'address']


@admin.register(OrganizationFinancialAccount)
class OrganizationFinancialAccountAdmin(BaseModelAdmin):
    pass


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(BaseModelAdmin):
    list_filter = ('organization', 'organization__owner')


@admin.register(SubscriptionType)
class SubscriptionTypeAdmin(BaseModelAdmin):
    pass


@admin.register(Subscription)
class SubscriptionAdmin(BaseModelAdmin):
    search_fields = ("uuid", "organization__name")
    list_filter = ('organization', 'organization__owner')
