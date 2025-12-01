# -*- coding: utf-8 -*-
"""
Created on July 14, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import datetime
import logging

from django.contrib.gis.db import models as gis_model
from django.contrib.gis.geos import Point
from django.db import models
from model_utils import FieldTracker
from simple_history.models import HistoricalRecords

from apps.events.managers import EphemeralEventManager, EventManager, AdminEventManager
from apps.notifications.utils.firebase import FirebaseDynamicLinkGenerator
from apps.utils.utils import _upload_to
from commons.models import AbstractCommonBaseModel

# from io import BytesIO
# from django.core.files import File
# from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class Event(AbstractCommonBaseModel):
    name = models.CharField(verbose_name="Nom", max_length=256, blank=False)
    description = models.TextField(
        verbose_name="Description", max_length=512, blank=False
    )
    type = models.ForeignKey(
        to="events.EventType",
        verbose_name="Type de l' évènement",
        blank=False,
        related_name="events",
        on_delete=models.DO_NOTHING,
    )
    default_price = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    location_name = models.CharField(
        verbose_name="Nom du lieu", max_length=512, blank=True
    )
    location_lat = models.FloatField(verbose_name="Latitude du lieu")
    location_long = models.FloatField(verbose_name="Longitude du lieu")
    location = gis_model.PointField(
        verbose_name="Lieu de l' évènement ", blank=False, null=True, srid=4326
    )
    hour = models.TimeField(
        verbose_name="Heure à laquelle aura lieu l' évènement ",
        default=datetime.time(00, 00, 00),
        blank=False,
    )
    date = models.DateField(
        verbose_name="Date à laquelle aura lieu l' évènement ", blank=False
    )
    expiry_date = models.DateTimeField(
        verbose_name="Date à laquelle l' évènement expire.", blank=False
    )
    cover_image = models.ImageField(
        verbose_name="Cover officiel de l' évènement", upload_to=_upload_to
    )
    publisher = models.ForeignKey(
        to="users.User",
        verbose_name="Utilisateur ayant publié",
        blank=False,
        related_name="published_events",
        on_delete=models.CASCADE,
    )
    organization = models.ForeignKey(
        to="organizations.Organization",
        verbose_name="Organisation du publicateur",
        blank=True,
        null=True,
        related_name="published_events",
        on_delete=models.CASCADE,
    )
    views = models.IntegerField(verbose_name="Nombre de vues", default=0)
    participant_count = models.IntegerField(
        verbose_name="Nombre de participants", default=0
    )
    dynamic_link = models.CharField(
        verbose_name="Lien dynamique", max_length=512, blank=True
    )
    country = models.ForeignKey(
        to="utils.Country",
        blank=True,
        null=True,
        verbose_name="Pays",
        on_delete=models.SET_NULL,
    )
    is_tickets_management_enabled = models.BooleanField(
        default=True, verbose_name="Permission de management de tickets"
    )
    tracker = FieldTracker()
    have_passed_validation = models.BooleanField(
        default=False, verbose_name="A passé la validation"
    )
    valid = models.BooleanField(default=False, verbose_name="Est valide")
    private = models.BooleanField(
        default=False, verbose_name="Est privé"
    )
    participant_limit = models.IntegerField(
        verbose_name="Limite de participants", default=15, blank=True
    )
    objects = EventManager()
    admin_objects = AdminEventManager()

    history = HistoricalRecords()
    
    is_ephemeral = models.BooleanField(
        default=False,
        verbose_name="Événement éphémère",
        help_text="Si coché, l'événement ne sera pas listé publiquement",
        db_index=True
    )
    
    created_by_super_seller = models.ForeignKey(
        to='organizations.Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ephemeral_events',
        verbose_name="Créé par super-vendeur",
        help_text="Super-vendeur qui a créé cet événement éphémère (si applicable)"
    )
    
    ephemeral_access_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Code d'accès éphémère",
        help_text="Code unique pour accéder à l'événement éphémère",
        db_index=True
    )
    

    objects = EventManager()              
    admin_objects = AdminEventManager()  
    ephemeral = EphemeralEventManager() 
    
    def __str__(self) -> str:
        return self.name

    def check_if_user_favourite(self, user):
        return user.favourite_events.filter(event=self).exists()

    def increment_by_one_view(self):
        self.views += 1
        self.save(update_fields=["views"])

    def deactivate(self):
        self.valid = False
        self.save(update_fields=["valid"])

    def activate(self):
        self.valid = True
        self.have_passed_validation = True
        self.save(update_fields=["valid", "have_passed_validation"])

    def save(self, *args, **kwargs):
        self.location_lat = float(self.location_lat)
        self.location_long = float(self.location_long)
        location = Point(self.location_lat, self.location_long, srid=2953)
        location.transform(4326)
        self.location = location
        if not self.expiry_date:
            self.expiry_date = datetime.datetime.combine(
                self.date, self.hour
            ) + datetime.timedelta(days=1)
        return super().save(*args, **kwargs)

    def get_dynamic_link(self):
        event_link = f"https://wuloevents.com/event/{self.pk}"
        if self.dynamic_link:
            return self.dynamic_link
        generator = FirebaseDynamicLinkGenerator()
        link = generator.generate(
            link=event_link,
            meta_tag_info={
                "socialTitle": self.name,
                "socialDescription": self.description,
                "socialImageLink": self.get_cover_image_url,
            },
        )
        self.dynamic_link = link
        self.save(update_fields=["dynamic_link"])
        return link

    @property
    def get_cover_image_url(self):
        if self.cover_image and hasattr(self.cover_image, "url"):
            return self.cover_image.url
        return None

    @property
    def get_entity_info(self):
        return {"name": self.name}

    class Meta:
        verbose_name = "Évènement"
        verbose_name_plural = "Évènements"
        unique_together = ("name", "date")
        constraints = [
            models.CheckConstraint(
                check=models.Q(private=False) | models.Q(participant_count__lte=models.F('participant_limit')),
                name="private_event_participant_limit"
            )
        ]

    def is_accessible_publicly(self):
        """
        Vérifie si l'événement est accessible publiquement.
        Un événement éphémère n'est pas accessible publiquement.
        """
        return not self.is_ephemeral and self.valid and self.have_passed_validation
    
    def can_be_found_by_search(self):
        """
        Vérifie si l'événement peut être trouvé par recherche.
        Les événements éphémères ne peuvent pas être recherchés.
        """
        return not self.is_ephemeral
    
    def generate_ephemeral_access_code(self):
        """
        Génère un code d'accès unique pour un événement éphémère.
        À appeler lors de la création d'un événement éphémère.
        """
        if self.is_ephemeral and not self.ephemeral_access_code:
            import uuid
            self.ephemeral_access_code = f"EPH-{uuid.uuid4().hex[:12].upper()}"
            self.save(update_fields=['ephemeral_access_code'])
        return self.ephemeral_access_code
    
    def get_ephemeral_access_url(self):
        """
        Retourne l'URL d'accès pour un événement éphémère.
        """
        if self.is_ephemeral and self.ephemeral_access_code:
            from django.conf import settings
            base_url = getattr(settings, 'FRONTEND_URL', 'https://app.wuloevents.com')
            return f"{base_url}/events/ephemeral/{self.ephemeral_access_code}"
        return None
