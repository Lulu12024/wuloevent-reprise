# -*- coding: utf-8 -*-
"""
Created on April 26 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.db import models

# Create your models here.
from commons.models import AbstractCommonBaseModel


class Search(AbstractCommonBaseModel):
    tracking_id = models.CharField(max_length=200, verbose_name="Identifiant de tracking", default='')
    q = models.CharField(max_length=120, verbose_name="Terme de recherche")
    search_date = models.DateTimeField(auto_now_add=True, verbose_name="Date de la recherche")
    ip_address = models.GenericIPAddressField(verbose_name="Adresse IP")
    user = models.ForeignKey(verbose_name='Utilisateur lié', related_name='searches', to="users.User",
                             on_delete=models.CASCADE, blank=True)

    def __str__(self) -> str:
        return self.q

    class Meta:
        abstract = True
