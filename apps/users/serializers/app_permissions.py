# -*- coding: utf-8 -*-
"""
Created on 10/11/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from rest_framework import serializers

from apps.users.models import AppPermission


class AppPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppPermission
        fields = ("pk", "name", "codename", "entity", "method", "timestamp", "updated", "active")

        extra_kwargs = {
            "codename": {"read_only": True},
            "entity": {"read_only": True},
        }


__all__ = ["AppPermissionSerializer"]
