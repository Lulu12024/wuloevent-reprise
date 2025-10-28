# -*- coding: utf-8 -*-
"""
Created on July 13, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.db import models
from apps.xlib.enums import OrganizationRolesEnum
from simple_history.models import HistoricalRecords

from commons.models import AbstractCommonBaseModel

# Create your models here.

logger = logging.getLogger(__name__)


class Role(AbstractCommonBaseModel):
    ROLE_WEIGHT_NAME_MATCHER = {'Member': 1, 'Coordinator': 2}

    ROLE_WEIGHT = (
        (1, 'Member'),
        (2, 'Coordinator')
    )
    name = models.CharField(verbose_name="Nom du role",
                            max_length=150, unique=True, choices=OrganizationRolesEnum.items())
    weight = models.PositiveBigIntegerField(
        verbose_name="Poids du rôle", choices=ROLE_WEIGHT)
    description = models.CharField(verbose_name="Description", max_length=512)

    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.name
