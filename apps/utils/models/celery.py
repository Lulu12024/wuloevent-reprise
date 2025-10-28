# -*- coding: utf-8 -*-
"""
Created on 22/07/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
# -*- coding: utf-8 -*-

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db import models

from commons.models import AbstractCommonBaseModel


class CeleryTask(AbstractCommonBaseModel):
    PAYMENT_TRANSACTION_CALLBACK = 'PAYMENT_TRANSACTION_CALLBACK'
    WITHDRAW_TRANSACTION_CALLBACK = 'WITHDRAW_TRANSACTION_CALLBACK'
    DATABASE_BACKUP = 'DATABASE_BACKUP'

    TASK_STATUS_INITIALIZED = 'TASK_STATUS_INITIALIZED'
    TASK_STATUS_PENDING = 'TASK_STATUS_PENDING'
    TASK_STATUS_FINISHED = 'TASK_STATUS_FINISHED'

    CELERY_LOG_TYPES = (
        (DATABASE_BACKUP, DATABASE_BACKUP),
        (PAYMENT_TRANSACTION_CALLBACK, PAYMENT_TRANSACTION_CALLBACK),
    )

    CELERY_TASK_STATUS = (
        (TASK_STATUS_INITIALIZED, TASK_STATUS_INITIALIZED),
        (TASK_STATUS_PENDING, TASK_STATUS_PENDING),
        (TASK_STATUS_FINISHED, TASK_STATUS_FINISHED),
    )

    type = models.CharField(max_length=220, choices=CELERY_LOG_TYPES, blank=True, verbose_name="Type de la tache")
    status = models.CharField(max_length=220, choices=CELERY_TASK_STATUS, blank=True, verbose_name="Status de la tache")
    task_id = models.CharField(max_length=220, blank=True, verbose_name="Id de la tâche")
    started_at = models.DateTimeField(verbose_name="Date de début", blank=True, null=True)
    finished_at = models.DateTimeField(verbose_name="Date de fin", blank=True, null=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=225)
    content_object = GenericForeignKey()

    def __str__(self) -> str:
        return f'Celery Task of type {self.type} About Model {str(self.content_type.model).upper()}\'s Object N° {self.object_id}'
