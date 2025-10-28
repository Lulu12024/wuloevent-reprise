# -*- coding: utf-8 -*-
"""
Created on July 14, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging
from datetime import datetime, timedelta

from django.db import models

from apps.organizations.models import Organization
from commons.models import AbstractCommonBaseModel

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


class TicketCategoryFeature(AbstractCommonBaseModel):
    description = models.TextField(
        verbose_name='Description', max_length=150, blank=True)
    organization = models.ForeignKey(verbose_name='Organisateur', related_name='created_ticket_category_features',
                                     to=Organization,
                                     on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.description

    class Meta:
        verbose_name = "Attribut d' un Ticket"
        verbose_name_plural = "Attributs d' un Ticket"


class TicketCategory(AbstractCommonBaseModel):
    event = models.ForeignKey(to="events.Event", verbose_name='Évènement connexe', null=True,
                              related_name='ticket_categories',
                              on_delete=models.CASCADE)
    name = models.CharField(verbose_name='Nom', max_length=150, blank=False)
    description = models.TextField(
        verbose_name='Description', max_length=500, blank=False)
    features = models.ManyToManyField(verbose_name="Avantages",
                                      to=TicketCategoryFeature, related_name='ticket_categories', blank=True)
    organization = models.ForeignKey(verbose_name='Organisation', related_name='created_ticket_categories',
                                     to=Organization,
                                     on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.name

    @property
    def get_entity_info(self):
        return {"name": self.name}

    class Meta:
        verbose_name = "Catégorie de Ticket"
        verbose_name_plural = "Catégories de Ticket"


class Ticket(AbstractCommonBaseModel):
    event = models.ForeignKey(to="events.Event", verbose_name='Évènement connexe', related_name='tickets',
                              on_delete=models.CASCADE)
    name = models.CharField(verbose_name='Nom', max_length=150, blank=False)
    description = models.TextField(
        verbose_name='Description', max_length=500, blank=True, null=True)
    category = models.ForeignKey(to=TicketCategory, verbose_name='Catégorie du ticket',
                                 blank=True, null=True, related_name='tickets', on_delete=models.DO_NOTHING)
    price = models.DecimalField(max_digits=9, decimal_places=2)
    expiry_date = models.DateTimeField(verbose_name='Date de fin de validité',
                                       default=datetime.now() + timedelta(hours=6))
    available_quantity = models.IntegerField(
        verbose_name='Nombre de ticket restant', null=False, blank=False, default=-1)
    initial_quantity = models.IntegerField(
        verbose_name='Nombre de ticket valide disponible initialement', null=False, blank=False, default=100)
    organization = models.ForeignKey(verbose_name='Organisateur', related_name='created_tickets', to=Organization,
                                     on_delete=models.CASCADE)

    def __str__(self) -> str:
        if self.category is None:
            return f'Ticket {self.name} de l\'évènement  {self.event.name}'
        else:
            return f'Ticket {self.name} de la catégorie {self.category.name} pour l\'évènement  {self.event.name}'

    @property
    def _name(self) -> str:
        if self.category is None:
            return f'{self.name}'
        else:
            return f'{self.name} de la catégorie {self.category.name}'

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if is_new:
            self.initial_quantity = self.available_quantity
        super().save(*args, **kwargs)

    def get_purchase_cost(self, quantity: int):
        return self.price * quantity

    @property
    def get_entity_info(self):
        return {"name": self.name}

    class Meta:
        verbose_name = "Ticket"
        verbose_name_plural = "Tickets"
        unique_together = ('name', 'category')
