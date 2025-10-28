# -*- coding: utf-8 -*-
"""
Created on 22/07/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
from django.contrib.gis.db import models

from apps.xlib.enums import VARIABLE_NAMES_ENUM
from commons.models import AbstractCommonBaseModel


class Variable(AbstractCommonBaseModel):
    VARIABLE_TYPE_CHOICES = (
        ("float", "Float"),
        ("int", "Int"),
        ("str", "String"),
    )

    label = models.CharField(max_length=520, blank=False, default="The Label")
    name = models.CharField(max_length=120, blank=False, unique=True, choices=VARIABLE_NAMES_ENUM.items())
    type = models.CharField(max_length=120, choices=VARIABLE_TYPE_CHOICES, blank=False)
    unit = models.CharField(max_length=120, blank=True, null=False)
    is_unique = models.BooleanField(verbose_name='Désigne si la variable à une valeur unique', default=False)
    editable = models.BooleanField(verbose_name='Désigne si la variable peut être modifiée', default=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = "Variable"
        verbose_name_plural = "Variables"

    def format_value(self, value):
        return eval(self.type)(value)


class VariableValue(AbstractCommonBaseModel):
    variable = models.ForeignKey(to=Variable, verbose_name='Variable relative', related_name='possible_values',
                                 blank=False, null=False, on_delete=models.CASCADE)
    value = models.CharField(verbose_name="Valeur de la variable", max_length=220)

    def __str__(self) -> str:
        return f'Valeur ( {self.value} ) de la variable {self.variable.name}'

    class Meta:
        verbose_name = "Valeur d' une Variable"
        verbose_name_plural = "Valeurs des Variables"
