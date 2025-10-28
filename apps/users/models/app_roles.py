# -*- coding: utf-8 -*-
"""
Created on August, 26 2024.

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
from django.db import models
from simple_history.models import HistoricalRecords

from apps.xlib.enums import AppRolesEnum
from commons.models import AbstractCommonBaseModel


class AppRole(AbstractCommonBaseModel):
    name = models.CharField(verbose_name="Nom du role", max_length=128)
    label = models.CharField(verbose_name="Label du role", max_length=64, choices=AppRolesEnum.items())

    permissions = models.ManyToManyField(
        to="users.AppPermission",
        related_name="app_roles",
        verbose_name="Permissions relatives",
        blank=True,
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Role de l' application"
        verbose_name_plural = "Roles de l' application"

    def __str__(self):
        return self.name
