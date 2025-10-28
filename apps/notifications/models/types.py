# -*- coding: utf-8 -*-
"""
Created on 22/07/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.db import models

from apps.xlib.enums import NOTIFICATION_TYPES_ENUM
from commons.models import AbstractCommonBaseModel


class NotificationType(AbstractCommonBaseModel):
    name = models.CharField(
        max_length=128, choices=NOTIFICATION_TYPES_ENUM.items(), verbose_name="Nom", unique=False
    )
    description = models.CharField(
        verbose_name="Description", max_length=128, blank=True, editable=False
    )

    def __str__(self):
        return "{}".format(self.name)

    @staticmethod
    def get_by_name(name):
        notification_type, _ = NotificationType.objects.get_or_create(
            name=name,
            defaults={
                "description": name,
            }
        )

        return notification_type

    class Meta:
        verbose_name = "Type de Notification"
        verbose_name_plural = "Types de Notification"
        unique_together = ("name", "description")
