# -*- coding: utf-8 -*-
"""
Created on April 29 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import typing

from django.http import HttpRequest
from rest_framework import permissions


class IsOrganizationActive(permissions.BasePermission):
    message = 'ORGANIZATION_OWNER_ACCOUNT_MUST_BE_VERIFIED'

    def has_permission(self, request: HttpRequest, view: typing.Any) -> bool:
        if hasattr(view, 'parent_obj'):
            organization = getattr(view, 'parent_obj')
            return organization.is_owner_verified
        return super().has_permission(request, view)

    def has_object_permission(self, request: HttpRequest, view: typing.Any, obj: typing.Any) -> bool:
        if not hasattr(view, 'parent_obj'):
            return bool(request.user and request.user.is_authenticated and obj.is_owner(request.user)) or bool(
                request.user and request.user.is_authenticated and request.user.check_organization_access(obj,
                                                                                                          'MEMBER'))
        return super().has_object_permission(request, view, obj)


class OrganizationHaveActiveSubscription(permissions.BasePermission):
    message = "THE_ORGANIZATION_DOES_NOT_HAVE_ACTIVE_SUBSCRIPTION"

    def has_permission(self, request: HttpRequest, view: typing.Any) -> bool:
        assert hasattr(
            view,
            'parent_obj'), "Parent Object not in nested view attrs. Try to check or create mixing for adding parent object."
        organization = getattr(view, 'parent_obj')
        return organization.have_active_subscription


class IsOrganizationOwner(permissions.BasePermission):
    message = 'YOU_ARE_NOT_ORGANIZATION_OWNER'

    def has_permission(self, request: HttpRequest, view: typing.Any) -> bool:
        # assert hasattr(
        #     view, 'parent_obj'), "Parent Object not in wested view attrs.
        #     Try to check or create mixing for adding parent object."
        if hasattr(view, 'parent_obj'):
            organization = getattr(view, 'parent_obj')
            return bool(
                request.user and request.user.is_authenticated and request.user == organization.owner)
        return super().has_permission(request, view)

    def has_object_permission(self, request: HttpRequest, view: typing.Any, obj: typing.Any) -> bool:
        if not hasattr(view, 'parent_obj'):
            return bool(
                request.user and request.user.is_authenticated and request.user == obj.owner)
        return super().has_object_permission(request, view, obj)


class IsOrganizationCoordinator(permissions.BasePermission):
    message = 'YOU_ARE_NOT_ORGANIZATION_COORDINATOR'

    def has_permission(self, request: HttpRequest, view: typing.Any) -> bool:
        # assert hasattr(
        #     view, 'parent_obj'), "Parent Object not in wested view attrs. Try to check or create mixing for adding parent object."
        if hasattr(view, 'parent_obj'):
            organization = getattr(view, 'parent_obj')
            return bool(
                request.user and request.user.is_authenticated and request.user.check_organization_access(organization,
                                                                                                          'COORDINATOR'))
        return super().has_permission(request, view)

    def has_object_permission(self, request: HttpRequest, view: typing.Any, obj: typing.Any) -> bool:
        if not hasattr(view, 'parent_obj'):
            return bool(
                request.user and request.user.is_authenticated and request.user.check_organization_access(obj,
                                                                                                          'COORDINATOR'))
        return super().has_object_permission(request, view, obj)


class IsOrganizationEventManager(permissions.BasePermission):
    message = 'YOU_MUST_BE_ORGANIZATION_OWNER_OR_MEMBER_WITH_COORDINATOR_ROLES'

    def has_permission(self, request: HttpRequest, view: typing.Any) -> bool:
        # assert hasattr(
        #     view, 'parent_obj'), "Parent Object not in nested view attrs. Try to check or create mixing for adding parent object."
        if hasattr(view, 'parent_obj'):
            organization = getattr(view, 'parent_obj')

            return bool(request.user and request.user.is_authenticated and organization.is_owner(request.user)) or bool(
                request.user and request.user.is_authenticated and request.user.check_organization_access(organization,
                                                                                                          'COORDINATOR'))
        return super().has_permission(request, view)

    def has_object_permission(self, request: HttpRequest, view: typing.Any, obj: typing.Any) -> bool:
        if not hasattr(view, 'parent_obj'):
            return bool(request.user and request.user.is_authenticated and obj.is_owner(request.user)) or bool(
                request.user and request.user.is_authenticated and request.user.check_organization_access(obj,
                                                                                                          'COORDINATOR'))
        return super().has_object_permission(request, view, obj)


class IsOrganizationMember(permissions.BasePermission):
    message = 'YOU_ARE_NOT_ORGANIZATION_MEMBER'

    def has_permission(self, request: HttpRequest, view: typing.Any) -> bool:
        # assert hasattr(
        #     view, 'parent_obj'), "Parent Object not in wested view attrs. Try to check or create mixing for adding parent object."
        if hasattr(view, 'parent_obj'):
            organization = getattr(view, 'parent_obj')
            return bool(request.user and request.user.is_authenticated and organization.is_owner(request.user)) or bool(
                request.user and request.user.is_authenticated and request.user.check_organization_access(
                    organization, 'MEMBER'))
        return super().has_permission(request, view)

    def has_object_permission(self, request: HttpRequest, view: typing.Any, obj: typing.Any) -> bool:
        if not hasattr(view, 'parent_obj'):
            return bool(request.user and request.user.is_authenticated and obj.is_owner(request.user)) or bool(
                request.user and request.user.is_authenticated and request.user.check_organization_access(obj,
                                                                                                          'MEMBER'))
        return super().has_object_permission(request, view, obj)
