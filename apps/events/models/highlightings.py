# -*- coding: utf-8 -*-
"""
Created on July 14, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging
from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.events.managers import EventHighlightingManager
from commons.models import AbstractCommonBaseModel

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


class EventHighlightingType(AbstractCommonBaseModel):
    name = models.CharField(verbose_name='Nom', max_length=150, blank=False)
    description = models.TextField(
        verbose_name='Description', max_length=500, blank=False)
    price = models.DecimalField(
        verbose_name="Prix", max_digits=15, default=1000.00, decimal_places=2)
    order = models.IntegerField(
        verbose_name='Ordre hiérarchique', default=1, blank=False)
    number_of_days_covered = models.PositiveIntegerField("Nombre de jours couverts", default=7)

    def __str__(self) -> str:
        return f'{self.name}'

    def get_purchase_cost(self, quantity: int):
        return self.price * quantity

    @property
    def get_entity_info(self):
        return {"name": self.name}

    class Meta:
        verbose_name = "Type de Mise en Avant d' évènement"
        verbose_name_plural = "Types de Mise en Avant d' évènements"


class EventHighlighting(AbstractCommonBaseModel):
    event = models.OneToOneField(to="events.Event", verbose_name='Évènement connexe', related_name='highlight',
                                 on_delete=models.CASCADE)
    type = models.ForeignKey(to=EventHighlightingType, verbose_name='Type De Mise en Avant lié',
                             related_name='related_highlight', on_delete=models.CASCADE)
    start_date = models.DateField(
        verbose_name='Date de début de validité', blank=True, auto_now_add=True, auto_now=False)
    end_date = models.DateField(
        verbose_name="Date de fin de validité", blank=True, default=(timezone.now() + timedelta(days=7)).date())
    active_status = models.BooleanField(default=False)
    objects = EventHighlightingManager()

    def __str__(self) -> str:
        return f'L\'évènement {self.event.name} a été mise en avant | Pack {self.type.name}.'

    class Meta:
        verbose_name = "Mise en Avant d' évènement"
        verbose_name_plural = "Mise en Avant d' évènement"

    @property
    def active(self):
        return True
