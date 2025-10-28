# -*- coding: utf-8 -*-
"""
Created on 02/07/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
from rest_framework.mixins import DestroyModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.events.permissions import IsPasswordConfirmed
from apps.organizations.mixings import CheckParentPermissionMixin
from apps.organizations.models import OrganizationMembership, Organization
from apps.organizations.permissions import IsOrganizationOwner
from commons.mixings import BaseModelMixin


class OrganizationMembershipViewSet(CheckParentPermissionMixin, DestroyModelMixin, BaseModelMixin, GenericViewSet):
    object_class = OrganizationMembership
    queryset = OrganizationMembership.objects.all()
    permission_classes = [IsAuthenticated, IsPasswordConfirmed, IsOrganizationOwner]
    authentication_classes = [JWTAuthentication]
    # http_method_names = ['DELETE']

    parent_queryset = Organization.objects.all()
    parent_lookup_field = "pk"
    parent_lookup_url_kwarg = "organization_pk"

    def perform_destroy(self, instance):
        instance.hard_delete()

    permission_classes_by_action = {
        'destroy': [IsAuthenticated, IsPasswordConfirmed, IsOrganizationOwner],
    }
