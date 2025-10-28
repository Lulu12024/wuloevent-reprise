# -*- coding: utf-8 -*-
"""
Created on 22/07/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.db import models

from commons.models import AbstractCommonBaseModel


class RegistrationsForNewsletter(AbstractCommonBaseModel):
    email = models.EmailField(verbose_name='Adresse email', max_length=150, blank=True)
    conf_num = models.CharField(verbose_name='Numero de confirmation', max_length=15)
    confirmed = models.BooleanField(verbose_name="Désigne si l'inscription est confirmé", default=False)

    def __str__(self) -> str:
        return self.email

    class Meta:
        verbose_name = "Souscription pour les newsletters"
        verbose_name_plural = "Souscriptions pour les newsletters"
