# -*- coding: utf-8 -*-
"""
Created on June 16 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import typing

from django.http import HttpRequest
from rest_framework import permissions

from apps.users.models import AppPermission


class IsCreator(permissions.BasePermission):
    message = 'You must be the creator of this object.'

    def has_object_permission(self, request: HttpRequest, view: typing.Any, obj: typing.Any) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user == obj.user)


class HasAppAdminPermissionFor(permissions.BasePermission):
    def __init__(self, codename=None):
        self.codename = codename

    def has_permission(self, request, view):
        if not request.user or not request.user.has_app_admin_access:
            return False
        queryset = AppPermission.objects.get(codename=self.codename).app_roles.filter(pk=request.user.role_id)

        if _has_access := queryset.exists():
            request.from_admin = True
        return _has_access


class CanCreateETicketForOrganization(permissions.BasePermission):
    message = 'You must be the creator of this object.'

    def has_object_permission(self, request: HttpRequest, view: typing.Any, obj: typing.Any) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user == obj.user)


class CanCreateEventForOrganization(permissions.BasePermission):
    message = 'You must be the creator of this object.'

    def has_object_permission(self, request: HttpRequest, view: typing.Any, obj: typing.Any) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user == obj.user)


"""

Object permission drf,
Use ModelPermission
Create Model Permission in django

"""
