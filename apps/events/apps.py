# -*- coding: utf-8 -*-
"""
Created on April 26, 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.apps import AppConfig


class EventsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.events'

    def ready(self):
        import apps.events.signals.handlers

