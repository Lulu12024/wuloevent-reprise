

# -*- coding: utf-8 -*-
"""
Created on October 29, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

from rest_framework import serializers
from django.core.validators import MinValueValidator
from apps.events.models import Ticket
from apps.utils.validators import PhoneNumberValidator

class SellerTicketSellSerializer(serializers.Serializer):
    ticket = serializers.PrimaryKeyRelatedField(queryset=Ticket.objects.select_related("event").all())
    quantity = serializers.IntegerField(min_value=1, validators=[MinValueValidator(1)])

    buyer_full_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    buyer_email = serializers.EmailField(required=False, allow_blank=True)
    buyer_phone = serializers.CharField(required=False, allow_blank=True, validators=[PhoneNumberValidator()])

    payment_reference = serializers.CharField(required=False, allow_blank=True, max_length=128)
    payment_channel = serializers.ChoiceField(
        choices=[("MOBILE_MONEY", "MOBILE_MONEY"), ("CASH", "CASH")],
        default="MOBILE_MONEY"
    )
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)

    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        ticket = attrs["ticket"]
        event = ticket.event

        if not event.valid or not event.have_passed_validation:
            raise serializers.ValidationError("L'événement n'est pas valide.")
        from django.utils import timezone
        if ticket.expiry_date and ticket.expiry_date <= timezone.now():
            raise serializers.ValidationError("Ce ticket est expiré.")
        return attrs
    

