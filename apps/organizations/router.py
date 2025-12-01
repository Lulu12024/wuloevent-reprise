# -*- coding: utf-8 -*-
"""
Created on April 26 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
# urls.py
from rest_framework_nested.routers import SimpleRouter, NestedSimpleRouter

from apps.chat_rooms.viewsets.access_criteria import ChatRoomAccessCriteriaViewSet
from apps.events.views import (
    WriteOnlyEventViewSet,
    WriteOnlyEventImageViewSet,
    WriteOnlyTicketViewSet,
    WriteOnlyTicketCategoryFeatureViewSet,
    WriteOnlyTicketCategoryViewSet,
    EventHighlightingViewSet,
)
from apps.chat_rooms.viewsets.chat_room_write_only import WriteChatRoomViewSet
from apps.organizations.views import (
    OrganizationViewSet,
    OrganizationStatsViewSet,
    OrganizationSubscriptionViewSet,
    OrganizationMembershipViewSet,
    WithdrawViewSet,
    SubscriptionViewSet,
)
from apps.organizations.views.coupons import OrganizationCouponViewSet
from apps.organizations.views.discount_conditions import (
    OrganizationDiscountConditionViewSet,
)
from apps.organizations.views.discounts import OrganizationDiscountViewSet
from apps.organizations.views.subscription_types import SubscriptionTypeViewSet

router = SimpleRouter()

router.register(r"organizations", OrganizationViewSet, basename="OrganizationViewSet")
router.register(r"subscriptions", SubscriptionViewSet, basename="SubscriptionViewSet")
router.register(
    r"subscription-types", SubscriptionTypeViewSet, basename="SubscriptionTypeViewSet"
)

organization_routers = NestedSimpleRouter(
    router, r"organizations", lookup="organization"
)
organization_routers.register(
    r"events", WriteOnlyEventViewSet, basename="WriteOnlyEventViewSet"
)
organization_routers.register(
    r"subscriptions",
    OrganizationSubscriptionViewSet,
    basename="OrganizationSubscriptionViewSet",
)
organization_routers.register(
    r"chat-rooms",
    WriteChatRoomViewSet,
    basename="WriteChatRoomViewSet"
)

# Router imbriqué pour les critères d'accès
chat_room_router = NestedSimpleRouter(
    organization_routers, r"chat-rooms", lookup='chat_room'
)
chat_room_router.register(r'access-criteria', ChatRoomAccessCriteriaViewSet, basename='chat-room-access-criteria')



organization_routers.register(
    r"event-images", WriteOnlyEventImageViewSet, basename="WriteOnlyEventImageViewSet"
)
# Todo: add s to event on route
organization_routers.register(
    r"event-highlighting",
    EventHighlightingViewSet,
    basename="tHighlightingViewSet",
)
organization_routers.register(
    r"tickets", WriteOnlyTicketViewSet, basename="WriteOnlyTicketViewSet"
)
organization_routers.register(
    r"ticket-categories",
    WriteOnlyTicketCategoryViewSet,
    basename="WriteOnlyTicketCategoryViewSet",
)
organization_routers.register(
    r"ticket-category-features",
    WriteOnlyTicketCategoryFeatureViewSet,
    basename="WriteOnlyTicketCategoryFeatureViewSet",
)

organization_routers.register(
    r"stats", OrganizationStatsViewSet, basename="OrganizationStatsViewSet"
)
organization_routers.register(
    r"memberships",
    OrganizationMembershipViewSet,
    basename="OrganizationMembershipViewSet",
)
organization_routers.register(r"withdraws", WithdrawViewSet, basename="WithdrawViewSet")
organization_routers.register(
    r"coupons", OrganizationCouponViewSet, basename="OrganizationCouponViewSet"
)
organization_routers.register(
    r"discounts", OrganizationDiscountViewSet, basename="OrganizationDiscountViewSet"
)
organization_routers.register(
    r"discount-conditions",
    OrganizationDiscountConditionViewSet,
    basename="OrganizationDiscountConditionViewSet",
)

urls_patterns = router.urls + organization_routers.urls
