# -*- coding: utf-8 -*-
"""
Created on August 21, 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.apps import AppConfig


class OrganizationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.organizations'

    def ready(self):
        import apps.organizations.signals.handlers
