# -*- coding: utf-8 -*-
"""
Created on 12/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.marketing.models import Coupon, Discount
from apps.organizations.models import Organization
from apps.xlib.enums import ErrorEnum


class CouponSerializer(serializers.ModelSerializer):
    discount = serializers.PrimaryKeyRelatedField(queryset=Discount.objects.filter(active=True))

    class Meta:
        model = Coupon
        fields = ("pk", "code", "discount", "usages", "timestamp", "updated", "active")

        extra_kwargs = {
            "updated": {"read_only": True},
            "timestamp": {"read_only": True},
            "usages": {"read_only": True},
        }

    def validate(self, attrs):
        data = super(CouponSerializer, self).validate(attrs)

        discount: Discount = data.get('discount')
        if discount.is_dynamic and discount.coupons.count() > 1:
            raise ValidationError(
                f"Un seul coupon peut être relié à cette réduction",
                code=ErrorEnum.DISCOUNT_MAX_NUMBER_OF_COUPON_REACHED.value,
            )
        return data


class CheckCouponRequestSerializer(serializers.Serializer):
    coupon = serializers.SlugRelatedField(queryset=Coupon.objects.filter(active=True), required=True, allow_null=False,
                                          slug_field='code')
    entity_id = serializers.UUIDField()
    entity_quantity = serializers.IntegerField(default=1)
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.filter(active=True), required=False,
                                                      allow_null=True, allow_empty=True)


class CalculationMethodSerializer(serializers.Serializer):
    method = serializers.CharField(max_length=32)
    value = serializers.FloatField()


class CheckCouponResponseSerializer(serializers.Serializer):
    calculation_method = CalculationMethodSerializer()
    initial_amount = serializers.DecimalField(max_digits=9, decimal_places=2)
    reduced_amount = serializers.DecimalField(max_digits=9, decimal_places=2)


__all__ = ["CouponSerializer", "CheckCouponRequestSerializer", "CheckCouponResponseSerializer"]
