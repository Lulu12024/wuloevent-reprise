# -*- coding: utf-8 -*-
"""
Created on October 29, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

from rest_framework import serializers
from apps.super_sellers.serializers.light import LightEventSerializer, LightSellerSerializer
from apps.events.serializers import LightTicketSerializer

class StockAllocationResultSerializer(serializers.Serializer):
    seller = LightSellerSerializer()
    ticket = LightTicketSerializer()
    event = LightEventSerializer()
    stock = serializers.DictField()
