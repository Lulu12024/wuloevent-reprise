# -*- coding: utf-8 -*-
"""
Created on 22/07/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.db import models

from commons.models import AbstractCommonBaseModel


class ContactsArea(AbstractCommonBaseModel):
    full_name = models.CharField("Nom complet", max_length=150, blank=True)
    email = models.EmailField('Email', max_length=150, blank=False)
    phone = models.CharField('Numero de téléphone', max_length=150, blank=True)
    subject = models.CharField('Sujet', max_length=150, blank=False)
    message = models.TextField('Message', max_length=150, blank=False)
    date = models.DateTimeField(auto_now_add=True, auto_now=False)

    def __str__(self) -> str:
        return str(self.full_name + ' ' + " à propos de " + ' ' + self.subject)

    class Meta:
        verbose_name = "Message Contact"
        verbose_name_plural = "Messages de Contact"
