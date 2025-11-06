# -*- coding: utf-8 -*-
"""
Created on 22/07/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
# -*- coding: utf-8 -*-

import json
import os
from pathlib import Path

from django.contrib.gis.db import models

from commons.models import AbstractCommonBaseModel

COUNTRY_CHOICES = (
    ("229", "Bénin"),
    ("000", 'Autres'),
)


class Country(AbstractCommonBaseModel):
    name = models.CharField(max_length=220, blank=True, verbose_name="Nom")
    code = models.CharField(max_length=2, blank=True, verbose_name="Code")
    prefix = models.CharField(max_length=5, blank=True, verbose_name="Préfixe")
    is_covered = models.BooleanField(default=False, verbose_name="Désigne si les services couvrent ce pays.")

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = "Pays"
        verbose_name_plural = "Pays"

    def save(self, *args, **kwargs):
        if self.prefix == "" or self.prefix is None:
            # countries_list_path = os.path.join(Path(__file__).resolve().parent, 'utils', 'files', 'countries.json')
            countries_list_path = "C:\\Users\\AGL\\Documents\\SOURCE\\wuloevents-api\\apps\\utils\\utils\\files\\countries.json"
            countries_list = json.load(open(countries_list_path))
            for item in countries_list:
                if item['code'] == self.code:
                    self.prefix = item['prefix']
                    self.name = item['name']['en']
                    break
        super(Country, self).save(*args, **kwargs)
