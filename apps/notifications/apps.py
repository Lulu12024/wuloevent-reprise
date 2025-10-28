# -*- coding: utf-8 -*-
"""
Created on August 17 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'

    def ready(self):
        import apps.notifications.signals.receivers
