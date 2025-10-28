# -*- coding: utf-8 -*-
"""
Created on April 29 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from rest_framework.routers import DefaultRouter

from apps.events.views import (
    ReadOnlyEventViewSet,
    ReadOnlyEventImageViewSet,
    ReadOnlyTicketCategoryViewSet,
    ReadOnlyTicketCategoryFeatureViewSet,
    ReadOnlyTicketViewSet,
    OrderViewSet,
    ETicketViewSet,
    EventHighlightingTypeViewSet,
    EventTypeViewSet,
    SponsorsViewSet,
)

router = DefaultRouter()
router.register(r"events", ReadOnlyEventViewSet,
                basename="ReadOnlyEventViewSet")
router.register(r"event-images", ReadOnlyEventImageViewSet,
                basename="ReadOnlyEventImageViewSet")
router.register(r"e-tickets", ETicketViewSet, basename="ETicketViewSet")
router.register(r"tickets", ReadOnlyTicketViewSet,
                basename="ReadOnlyTicketViewSet")
router.register(r"ticket-categories", ReadOnlyTicketCategoryViewSet,
                basename="ReadOnlyTicketCategoryViewSet")
router.register(r"ticket-category-features", ReadOnlyTicketCategoryFeatureViewSet,
                basename="ReadOnlyTicketCategoryFeatureViewSet")
router.register(r"orders", OrderViewSet, basename="OrderViewSet")
router.register(r"event-types", EventTypeViewSet, basename="EventTypeViewSet")
router.register(r"event-highlighting-types", EventHighlightingTypeViewSet, basename="EventHighlightingTypeViewSet")
router.register(r'sponsors', SponsorsViewSet, basename='SponsorViewSet')

urls_patterns = router.urls
