# -*- coding: utf-8 -*-
"""
Created on October 29, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

from rest_framework import serializers
from apps.events.models import Event
from apps.events.models.seller import Seller

class LightEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ("pk", "name", "date", "default_price", "is_ephemeral")

class LightSellerSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    class Meta:
        model = Seller
        fields = ("pk", "user_full_name", "status", "kyc_status", "phone_number", "whatsapp_number")
