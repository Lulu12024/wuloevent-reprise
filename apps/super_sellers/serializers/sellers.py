# -*- coding: utf-8 -*-
"""
Created on October 29, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

from rest_framework import serializers
from apps.events.models.seller import Seller, SellerStatus, SellerKYCStatus

class SellerListSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    organization_id = serializers.UUIDField(source="super_seller.pk", read_only=True)

    class Meta:
        model = Seller
        fields = [
            "pk",
            "user_full_name",
            "status",
            "kyc_status",
            "phone_number",
            "whatsapp_number",
            "commission_rate",
            "sales_target",
            "assigned_zone",
            "activated_at",
            "suspended_at",
            "organization_id",
            "timestamp",
            "active",
        ]


class SellerDetailSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    organization = serializers.SerializerMethodField()
    payment_info = serializers.SerializerMethodField()

    class Meta:
        model = Seller
        fields = [
            "pk",
            "user_full_name",
            "user_email",
            "user_phone",
            "status",
            "kyc_status",
            "invited_at",
            "activated_at",
            "suspended_at",
            "suspension_reason",
            "phone_number",
            "whatsapp_number",
            "commission_rate",
            "sales_target",
            "assigned_zone",
            "notes",
            "metadata",
            "payment_info",
            "organization",
            "active",
            "timestamp",
        ]

    def get_organization(self, obj):
        return {"pk": str(obj.super_seller.pk), "name": obj.super_seller.name}

    def get_payment_info(self, obj):
        return obj.get_payment_info()


class SellerStatusUpdateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["activate", "suspend"])
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        action = attrs["action"]
        seller: Seller = self.context["seller"]
        if action == "activate" and seller.status == SellerStatus.ACTIVE:
            raise serializers.ValidationError("Ce vendeur est déjà actif.")
        if action == "suspend" and seller.status == SellerStatus.SUSPENDED:
            raise serializers.ValidationError("Ce vendeur est déjà suspendu.")
        return attrs
