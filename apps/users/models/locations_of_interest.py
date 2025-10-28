# -*- coding: utf-8 -*-
"""
Created on July 11, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.contrib.gis.db import models as gis_model
from django.db import models

from apps.utils.managers import GeoModelManager
from commons.models import AbstractCommonBaseModel

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


class PointOfInterest(AbstractCommonBaseModel):
    user = models.ForeignKey(to="users.User", on_delete=models.CASCADE, null=True,
                             blank=True, related_name='points_of_interest')

    location_lat = models.FloatField(
        verbose_name="Latitude du lieu", default=0)
    location_long = models.FloatField(
        verbose_name="Longitude du lieu", default=0)
    location = gis_model.PointField(
        verbose_name='Coordonnées', blank=False, null=True, srid=4326)
    approximate_distance = models.FloatField(
        verbose_name='Distance de verification en mètre', default=100000)
    allow_notifications = models.BooleanField(
        verbose_name='Notifications', default=False)
    objects = GeoModelManager()

    def __str__(self) -> str:
        return f'Point d\'intérêt de {self.user}'

    class Meta:
        verbose_name = "Point Géographique d'intérêt"
        verbose_name_plural = "Point Géographique d'intérêt"


class ZoneOfInterest(AbstractCommonBaseModel):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, null=True,
                             blank=True, related_name='area')
    geofence = gis_model.PolygonField(
        verbose_name='Zone', blank=False, null=True, srid=4326)
    allow_notifications = models.BooleanField(
        verbose_name='Notifications', default=True)

    def __str__(self) -> str:
        return f''

    class Meta:
        verbose_name = "Zone Géographique d'interet"
        verbose_name_plural = "Zones Géographiques d'interet"
