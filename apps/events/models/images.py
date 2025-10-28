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


class EventImage(AbstractCommonBaseModel):
    event = models.ForeignKey(to="events.Event", verbose_name='Évènement relatif',
                              blank=False, related_name='images', on_delete=models.CASCADE)
    title = models.CharField(max_length=220, null=True, blank=True)
    image = models.ImageField(upload_to=_upload_to)
    thumbnails = models.BooleanField(default=False)
    organization = models.ForeignKey(verbose_name='Organisateur', related_name='created_event_images',
                                     to="organizations.Organization",
                                     on_delete=models.CASCADE)

    def __str__(self) -> str:
        return str(self.title)

    class Meta:
        verbose_name = "Image d'évènement "
        verbose_name_plural = "Images d'évènement s"
