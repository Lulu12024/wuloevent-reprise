# -*- coding: utf-8 -*-
"""
Created on 10/11/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from rest_framework import serializers

from apps.users.models import AppRole, AppPermission
from apps.users.serializers.app_permissions import AppPermissionSerializer


class AppRoleSerializer(serializers.ModelSerializer):
    permissions = AppPermissionSerializer(many=True, read_only=True)
    permissions_ids = serializers.ListField(required=False, allow_null=True, allow_empty=True,
                                            child=serializers.UUIDField(), write_only=True)

    class Meta:
        model = AppRole
        fields = ("pk", "name", "label", "permissions", "permissions_ids", "timestamp", "updated", "active")

        extra_kwargs = {
            "permissions": {"read_only": True},
            "timestamp": {"read_only": True},
            "updated": {"read_only": True},
        }

    def create(self, validated_data):
        permissions_ids = validated_data.pop('permissions_ids', [])
        role: AppRole = super(AppRoleSerializer, self).create(validated_data=validated_data)

        self.set_permissions(role, permissions_ids)
        return role

    def update(self, instance, validated_data):
        permissions_ids = validated_data.pop('permissions_ids', None)
        role = super(AppRoleSerializer, self).update(instance, validated_data)

        if permissions_ids is not None:
            self.set_permissions(role, permissions_ids)
        return role

    @staticmethod
    def set_permissions(role, permissions_ids):
        permissions = AppPermission.objects.filter(pk__in=permissions_ids)
        role.permissions.set(permissions)


__all__ = ["AppRoleSerializer"]
