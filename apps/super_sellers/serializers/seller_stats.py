
"""
Created on November 03, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

from rest_framework import serializers


class SellerStatsFilterSerializer(serializers.Serializer):
    """
    Filtres communs pour les stats vendeur (période).
    """
    date_from = serializers.DateField(required=False, allow_null=True)
    date_to = serializers.DateField(required=False, allow_null=True)


class SellerStatsOverviewSerializer(serializers.Serializer):
    total_tickets_sold = serializers.IntegerField()
    total_revenue = serializers.CharField()
    total_commission = serializers.CharField()


class SellerStatsByEventItemSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    event_name = serializers.CharField()
    event_date = serializers.DateField()
    tickets_sold = serializers.IntegerField()
    revenue = serializers.CharField()
    last_sale_at = serializers.DateTimeField(allow_null=True)


class SellerStockItemSerializer(serializers.Serializer):
    event_id = serializers.UUIDField(allow_null=True)
    event_name = serializers.CharField(allow_null=True)
    ticket_id = serializers.UUIDField(allow_null=True)
    ticket_name = serializers.CharField(allow_null=True)

    authorized_sale_price = serializers.CharField()
    commission_rate = serializers.CharField()

    total_allocated = serializers.IntegerField()
    total_sold = serializers.IntegerField()
    available_quantity = serializers.IntegerField()
