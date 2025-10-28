# -*- coding: utf-8 -*-
"""
Created on July 14, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.db import models

from apps.utils.utils import _upload_to
from commons.models import AbstractCommonBaseModel

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


class EventType(AbstractCommonBaseModel):
    name = models.CharField(
        verbose_name='Nom', unique=True, max_length=150, blank=False)
    description = models.TextField(
        verbose_name='Description', max_length=500, blank=False)
    parent = models.ForeignKey(to='self', verbose_name='Catégorie parente',
                               blank=True, null=True, related_name='children', on_delete=models.CASCADE)
    image = models.ImageField(verbose_name='Image du type d\'évènement',
                              upload_to=_upload_to, blank=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = "Type d' évènement"
        verbose_name_plural = "Types d' évènement"
        unique_together = ('name', 'description',)
