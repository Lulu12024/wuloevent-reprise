# -*- coding: utf-8 -*-
"""
Created on October 29, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

from django.urls import path

from apps.organizations.router import urls_patterns
from apps.organizations.views import (
    OrganizationFollowersView, 
    OrganizationFollowedView,
    OrganizationFollowView, 
    OrganizationUnFollowView,
    ScanETicketView
)
from apps.organizations.views.ephemeral_event_views import (
    EphemeralEventCreateAPIView,
    EphemeralEventViewSet,
)

from apps.super_sellers.views.super_seller_views import (
     InviteSellerAPIView,
     SellerInvitationRespondAPIView
)

from .views.seller_views import SellerManagementViewSet
from .views.sales_views import SellerTicketSellView

urlpatterns = [
    
    path(
        'api/sellers/invite/',
        InviteSellerAPIView.as_view(),
        name="invite-seller",),
    path(
        'api/sellers/invitations/<str:token>/respond/',
        SellerInvitationRespondAPIView.as_view(),
        name="respond-seller-invitation",
    ),

    # Liste
    path(
        "sellers/",
        SellerManagementViewSet.as_view({"get": "list"}),
        name="super-sellers-sellers-list",
    ),
    # Détails + suppression
    path(
        "sellers/<uuid:pk>/",
        SellerManagementViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name="super-sellers-sellers-detail",
    ),
    # Statut (PATCH)
    path(
        "sellers/<uuid:pk>/status/",
        SellerManagementViewSet.as_view({"patch": "update_status"}),
        name="super-sellers-sellers-status",
    ),

    path(
        "super-sellers/sellers/<uuid:pk>/stock/allocate/",
        SellerManagementViewSet.as_view({"post": "allocate_stock"}),
        name="super-sellers-sellers-stock-allocate",
    ),

    path(
        "sellers/tickets/sell", 
        SellerTicketSellView.as_view(), 
        name="seller-ticket-sell"
    ),
]

urlpatterns += urls_patterns