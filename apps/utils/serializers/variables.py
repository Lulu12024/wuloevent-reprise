# -*- coding: utf-8 -*-
"""
Created on July 27 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from rest_framework import serializers

from apps.utils.models import Variable
from apps.utils.serializers.variable_values import LightVariableValueSerializer


class VariableSerializer(serializers.ModelSerializer):
    values = LightVariableValueSerializer(many=True, source="possible_values")

    class Meta:
        model = Variable
        fields = ('pk', 'label', 'name', 'type', 'unit', 'values', 'is_unique', 'editable')
