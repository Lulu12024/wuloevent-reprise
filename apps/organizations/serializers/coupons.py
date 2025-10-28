# -*- coding: utf-8 -*-
"""
Created on October 22 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
import logging

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.marketing.models import Coupon, Discount
from apps.xlib.enums import ErrorEnum
from apps.xlib.error_util import ErrorUtil

logger = logging.getLogger(__name__)


class OrganizationCouponSerializer(serializers.ModelSerializer):
    discount = serializers.PrimaryKeyRelatedField(queryset=Discount.objects.filter(active=True))
    code = serializers.CharField(required=True, allow_null=False, allow_blank=False)

    class Meta:
        model = Coupon
        fields = ("pk", "code", "discount", "usages", "timestamp", "updated", "active")

        extra_kwargs = {
            "updated": {"read_only": True},
            "timestamp": {"read_only": True},
            "usages": {"read_only": True},
        }

    def validate(self, attrs):
        code = attrs.get("code", None)
        if code:
            try:
                Coupon.objects.get(code=code)
                raise ValidationError(
                    ErrorUtil.get_error_detail(ErrorEnum.COUPON_WITH_THIS_CODE_ALREADY_EXISTS),
                    code=ErrorEnum.COUPON_WITH_THIS_CODE_ALREADY_EXISTS.value,
                )
            except Coupon.DoesNotExist:
                logger.info("Coupon doesn't exist")
                pass

        validated_data = super(OrganizationCouponSerializer, self).validate(attrs)

        request = self.context.get('request')
        discount: Discount = validated_data.get("discount")

        if discount.organization_id != request.organization.pk:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.YOUR_ORGANIZATION_IS_NOT_CREATOR_OF_THIS_DISCOUNT),
                code=ErrorEnum.YOUR_ORGANIZATION_IS_NOT_CREATOR_OF_THIS_DISCOUNT.value,
            )

        return validated_data


__all__ = ["OrganizationCouponSerializer", ]
