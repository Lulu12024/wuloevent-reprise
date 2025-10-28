# -*- coding: utf-8 -*-
"""
Created on October 15 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from rest_framework.routers import DefaultRouter

from apps.marketing.views import CouponViewSet, DiscountViewSet
from apps.marketing.views.discount_conditions import DiscountConditionViewSet

router = DefaultRouter()
router.register(r"coupons", CouponViewSet, basename="CouponViewSet")
router.register(r"discounts", DiscountViewSet, basename="DiscountViewSet")
router.register(
    r"discount-conditions",
    DiscountConditionViewSet,
    basename="DiscountConditionViewSet",
)

urls_patterns = router.urls
