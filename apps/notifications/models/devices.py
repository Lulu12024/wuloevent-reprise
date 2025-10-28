# -*- coding: utf-8 -*-
"""
Created on 22/07/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.contrib.gis.db import models as gis_model
from django.contrib.gis.geos import Point
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils import FieldTracker

from apps.notifications.managers import MobileDeviceManager
from apps.notifications.onesignal import Processor
from commons.models import AbstractCommonBaseModel

one_signal_processor = Processor()


class MobileDevice(AbstractCommonBaseModel):
    DEVICE_TYPES = (("ios", "ios"), ("android", "android"), ("web", "web"))

    name = models.CharField(
        max_length=255, verbose_name=_("Name"), blank=True, null=True
    )
    user = models.ForeignKey(
        to="users.User",
        verbose_name="Utilisateur associé",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    registration_id = models.TextField(
        verbose_name="Token d' enregistrement", blank=True, null=True
    )
    token = models.TextField(
        verbose_name="Token d' enregistrement", blank=True, null=True
    )
    type = models.CharField(choices=DEVICE_TYPES, max_length=10, blank=True, null=True)
    current_location_lat = models.FloatField(
        verbose_name="Latitude du lieu", blank=True, null=True
    )
    current_location_long = models.FloatField(
        verbose_name="Longitude du lieu", blank=True, null=True
    )
    current_location = gis_model.PointField(
        verbose_name="Lieu de l' évènement", blank=True, null=True, srid=4326
    )
    tracker = FieldTracker()
    objects = MobileDeviceManager()

    class Meta:
        verbose_name = "Appareil Mobile"
        verbose_name_plural = "Appareils Mobile"
        unique_together = ('registration_id', 'token')

    def initialize_one_signal_registerer(self):
        return one_signal_processor.Registerer(
            device_type=type,
            identifier=self.registration_id,
            first_name=self.user.first_name,
            last_name=self.user.last_name,
            lat=self.current_location_lat,
            long=self.current_location_long,
        )

    def create_device_on_one_signal(self):
        registerer = self.initialize_one_signal_registerer()
        response = registerer.create_device()
        self.onesignal_id = response.get("id")
        self.save()

    def update_device_on_one_signal(self):
        registerer = self.initialize_one_signal_registerer()
        return registerer.edit_device(player_id=self.onesignal_id)

    def save(self, *args, **kwargs) -> None:
        self.current_location = Point(
            self.current_location_lat, self.current_location_long, srid=4326
        )
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} de {self.user} | {self.registration_id[10] if self.registration_id else 'Pas de token'}..."
