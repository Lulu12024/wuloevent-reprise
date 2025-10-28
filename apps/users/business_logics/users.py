# -*- coding: utf-8 -*-
"""
Created on December 5 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.db.models import Q

from apps.users.models import User


def get_app_admins():
    admins = User.objects.select_related("role").filter(
        Q(is_staff=True) | Q(role__isnull=False, is_app_admin=True)
    )
    return admins
