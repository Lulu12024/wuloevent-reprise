# -*- coding: utf-8 -*-
"""
Created on July 27 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
from rest_framework import serializers

from apps.utils.models import VariableValue, Variable


class VariableValueSerializer(serializers.ModelSerializer):
    variable = serializers.PrimaryKeyRelatedField(queryset=Variable.objects.filter(active=True))

    class Meta:
        model = VariableValue
        fields = ('pk', 'variable', 'value')


class LightVariableValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = VariableValue
        fields = ('pk', 'value')
