# -*- coding: utf-8 -*-
"""
Created on April 26 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from rest_framework.routers import DefaultRouter

from apps.users.views import (
    PointOfInterestViewSet,
    TransactionViewSet,
    AppRoleViewSet,
    AppPermissionViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register(r"pois", PointOfInterestViewSet, basename="PointOfInterestViewSet")
# router.register(r"zois", ZoneOfInterestViewSet, basename="ZoneOfInterestViewSet")
router.register(r"transactions", TransactionViewSet, basename="TransactionViewSet")
router.register(
    r"app-permissions", AppPermissionViewSet, basename="AppPermissionViewSet"
)
router.register(r"app-roles", AppRoleViewSet, basename="AppRoleViewSet")
router.register(r"users", UserViewSet, basename="UserViewSet")

urls_patterns = router.urls
