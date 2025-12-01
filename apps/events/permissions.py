# -*- coding: utf-8 -*-
"""
Created on April 29 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import typing

from django.http import HttpRequest
from rest_framework import permissions

from .models import Order


class IsPasswordConfirmed(permissions.BasePermission):
    message = "VALID_PASSWORD_NOT_PROVIDED"

    def has_permission(self, request, view):
        password = request.data.get('password', '')
        self.bool = bool(request.user and request.user.is_authenticated and request.user.check_password(password))
        return self.bool


class IsOrderCreator(permissions.BasePermission):
    message = 'You must be the creator of this object.'

    def has_object_permission(self, request: HttpRequest, view: typing.Any, obj: typing.Any) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user == obj.user)


class OrganizationIsObjectCreator(permissions.BasePermission):
    message = 'YOUR_ORGANIZATION_IS_NOT_CREATOR_OF_THIS_OBJECT'

    def has_object_permission(self, request: HttpRequest, view: typing.Any, obj: typing.Any) -> bool:
        return bool(request.user and request.user.is_authenticated and request.organization == obj.organization)


class IsETicketCreator(permissions.BasePermission):
    message = 'You must be the creator of this object.'

    def has_object_permission(self, request: HttpRequest, view: typing.Any, obj: typing.Any) -> bool:
        try:
            order = Order.objects.get(pk=obj.related_order_id)
        except:
            return False

        return bool(request.user and request.user.is_authenticated and request.user == order.user)


class CanScanETicket(permissions.BasePermission):
    message = 'Vous n\'êtes pas le publicateur de l\'évênement dont vous voulez scanner le ticket'

    def has_object_permission(self, request: HttpRequest, view: typing.Any, obj: typing.Any) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user == obj.event.publisher)


class EndpointNotAuthorized(permissions.BasePermission):
    message = 'You must be the creator of this object.'

    def has_permission(self, request, view):
        return False

    def has_object_permission(self, request: HttpRequest, view: typing.Any, obj: typing.Any) -> bool:
        return False


class CanCreateEphemeralEvent(permissions.BasePermission):
    """
    Permission pour créer des événements éphémères.
    Seulement les super-vendeurs vérifiés peuvent créer des événements éphémères.
    """
    
    def has_permission(self, request, view):
        # Vérifier que l'utilisateur est membre d'une organisation super-vendeur
        user = request.user
        
        # Vérifier si l'utilisateur appartient à une organisation super-vendeur
        from apps.organizations.models import Organization
        
        try:
            # Trouver l'organisation de l'utilisateur
            member = user.organization_members.first()
            if not member:
                return False
            
            organization = member.organization
            
            # Vérifier que c'est un super-vendeur vérifié
            if hasattr(organization, 'super_seller_profile'):
                return organization.super_seller_profile.can_operate()
            
            return False
        except:
            return False
"""

Object permission drf,
Use ModelPermission
Create Model Permission in django

"""
