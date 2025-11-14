# -*- coding: utf-8 -*-
"""
Created on November 03, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

from rest_framework import serializers

class StatsBaseFilterSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField(required=True)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

class StatsOverviewResponseSerializer(serializers.Serializer):
    total_tickets_sold = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_commission = serializers.DecimalField(max_digits=12, decimal_places=2)
    sellers_active = serializers.IntegerField()
    events_count = serializers.IntegerField()

class StatsByEventItemSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    event_name = serializers.CharField()
    tickets_sold = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    commission = serializers.DecimalField(max_digits=12, decimal_places=2)

class StatsBySellerItemSerializer(serializers.Serializer):
    seller_id = serializers.UUIDField()
    seller_name = serializers.CharField()
    tickets_sold = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    commission = serializers.DecimalField(max_digits=12, decimal_places=2)

class StatsByPeriodItemSerializer(serializers.Serializer):
    period = serializers.CharField()
    tickets_sold = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    commission = serializers.DecimalField(max_digits=12, decimal_places=2)

class StatsByEventResponseSerializer(serializers.Serializer):
    results = StatsByEventItemSerializer(many=True)

class StatsBySellerResponseSerializer(serializers.Serializer):
    results = StatsBySellerItemSerializer(many=True)

class StatsByPeriodQuerySerializer(StatsBaseFilterSerializer):
    granularity = serializers.ChoiceField(choices=("day", "week", "month"), default="day")

class StatsByPeriodResponseSerializer(serializers.Serializer):
    results = StatsByPeriodItemSerializer(many=True)
