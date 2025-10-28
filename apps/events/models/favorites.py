# -*- coding: utf-8 -*-
"""
Created on July 14, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.db import models

from commons.models import AbstractCommonBaseModel

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


class FavouriteEventType(AbstractCommonBaseModel):
    event_type = models.ForeignKey(to="events.EventType", verbose_name='Type d\'évènement  connexe',
                                   related_name='adds_like_favourite',
                                   on_delete=models.CASCADE)
    user = models.ForeignKey(verbose_name='Utilisateur lié', related_name='favourite_event_types', to="users.User",
                             on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f'{self.user.get_full_name()} a choisi l\'évènement {self.event_type.name}  comme favoris'

    class Meta:
        verbose_name = "Favoris"
        verbose_name_plural = "Favoris"
        unique_together = ('user', 'event_type',)


class FavouriteEvent(AbstractCommonBaseModel):
    event = models.ForeignKey(to="events.Event", verbose_name='Évènement connexe', related_name='adds_like_favourite',
                              on_delete=models.CASCADE)
    user = models.ForeignKey(verbose_name='Utilisateur lié', related_name='favourite_events', to="users.User",
                             on_delete=models.CASCADE)
    receive_news_by_email = models.BooleanField(
        verbose_name='Être informé par email', default=True)

    def __str__(self) -> str:
        return f'{self.user.get_full_name()} a choisi l\'évènement  {self.event.name}  comme favoris'

    class Meta:
        verbose_name = "Favoris"
        verbose_name_plural = "Favoris"
        unique_together = ('user', 'event',)
