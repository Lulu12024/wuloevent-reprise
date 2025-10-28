# -*- coding: utf-8 -*-
"""
Created on August, 26 2024.

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
from django.db import models
from simple_history.models import HistoricalRecords

from commons.models import AbstractCommonBaseModel


class AppPermission(AbstractCommonBaseModel):
    name = models.CharField(verbose_name="Nom de la permission", max_length=255)
    codename = models.CharField(verbose_name="Nom de code", max_length=100, unique=True, db_index=True)
    entity = models.CharField(verbose_name="Entité associée à la permission", max_length=100, blank=True, null=True)
    method = models.CharField(verbose_name="Methode associée à la permission", max_length=100, blank=True, null=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Permission de l' application"
        verbose_name_plural = "Permissions de l' application"
        ordering = ("entity", )

    def __str__(self):
        return f"{self.entity} | { self.name}"
