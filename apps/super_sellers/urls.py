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
from apps.super_sellers.views.wallet_views import WalletViewSet
from apps.super_sellers.views.withdrawal_views import WithdrawalViewSet

from .views.seller_views import SellerManagementViewSet
from .views.sales_views import SellerTicketSellView
from rest_framework.routers import DefaultRouter
from apps.super_sellers.views.tickets import PublicTicketViewSet, TicketDeliveryViewSet
from apps.super_sellers.views.stats_views import (
    StatsOverviewView, StatsByEventView, StatsBySellerView, StatsByPeriodView
)
from apps.super_sellers.views.reporting_views import (
    ReportPreferenceView,
    ReportPreviewView,
    ReportGenerateNowView,
    ReportHistoryListView
)

from apps.super_sellers.views.seller_stats_views import (
    SellerStatsOverviewAPIView,
    SellerStatsByEventAPIView,
    SellerStockListAPIView,
)
from apps.super_sellers.views.super_seller_kyc_views import SuperSellerKYCSubmitView, AdminSuperSellerKYCVerifyView
from apps.super_sellers.views.seller_kyc_views import SellerKYCSubmitView, SuperSellerReviewSellerKYCView


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

    # Super-seller stats endpoints
    path(
        'super-sellers/stats/overview', 
        StatsOverviewView.as_view(),
        name="super-sellers-stats-overview"
    ),
    path(
        'super-sellers/stats/by-event', 
        StatsByEventView.as_view(),
        name="super-sellers-stats-by-event"
    ),
    path(
        'super-sellers/stats/by-seller', 
        StatsBySellerView.as_view(),
        name="super-sellers-stats-by-seller"
    ),
    path(
        'super-sellers/stats/by-period', 
        StatsByPeriodView.as_view(),
        name="super-sellers-stats-by-period"
    ),

    # Seller stats endpoints
    path('sellers/<uuid:pk>/stats/overview/', SellerStatsOverviewAPIView.as_view(), name="sellers-stats-overview"),
    path('sellers/<uuid:pk>/stats/by-event/', SellerStatsByEventAPIView.as_view(), name="sellers-stats-by-event"),
    path('sellers/<uuid:pk>/stats/stock/', SellerStockListAPIView.as_view(), name="sellers-stats-stock"),
    
    # Super-seller reporting endpoints
    path("super-sellers/reports/prefs", ReportPreferenceView.as_view(), name="super-sellers-report-prefs"),
    path("super-sellers/reports/preview", ReportPreviewView.as_view(), name="super-sellers-report-preview"),
    path("super-sellers/reports/generate", ReportGenerateNowView.as_view(), name="super-sellers-report-generate"),
    path("super-sellers/reports/history", ReportHistoryListView.as_view(), name="super-sellers-report-history"),

    
    # KYC Endpoints
    # Super-seller KYC submission and admin verification
    path("super-sellers/kyc/submit", SuperSellerKYCSubmitView.as_view(), name="super-seller-kyc-submit"),
    path("admin/super-sellers/<uuid:org_id>/kyc/verify", AdminSuperSellerKYCVerifyView.as_view(),
         name="admin-super-seller-kyc-verify"),

    #
    path(
        'sellers/kyc/submit', 
        SellerKYCSubmitView.as_view(), 
        name='seller-kyc-submit'
    ),
    path(
        'super-sellers/sellers/<uuid:seller_id>/kyc/review', 
        SuperSellerReviewSellerKYCView.as_view(),
        name='super-seller-review-seller-kyc'
    ),

    # Détails d'un ticket (accès public)
    path(
        'tickets/<uuid:pk>/',
        PublicTicketViewSet.as_view({'get': 'retrieve'}),
        name='public-ticket-detail'
    ),
    
    # Télécharger le PDF du ticket
    path(
        'tickets/<uuid:pk>/download/',
        PublicTicketViewSet.as_view({'get': 'download_pdf'}),
        name='public-ticket-download'
    ),
    
    # Vérifier la validité du ticket
    path(
        'tickets/<uuid:pk>/verify/',
        PublicTicketViewSet.as_view({'get': 'verify_ticket'}),
        name='public-ticket-verify'
    ),
    
    # ============================================
    # TICKET DELIVERY ENDPOINTS
    # ============================================
    
    # Liste des envois de tickets
    path(
        'ticket-deliveries/',
        TicketDeliveryViewSet.as_view({'get': 'list'}),
        name='ticket-delivery-list'
    ),
    
    # Détails d'un envoi
    path(
        'ticket-deliveries/<uuid:pk>/',
        TicketDeliveryViewSet.as_view({'get': 'retrieve'}),
        name='ticket-delivery-detail'
    ),
    
    # Forcer un retry manuel
    path(
        'ticket-deliveries/<uuid:pk>/retry/',
        TicketDeliveryViewSet.as_view({'post': 'retry_delivery'}),
        name='ticket-delivery-retry'
    ),

     # Consulter son solde
    path(
        'wallet/balance/',
        WalletViewSet.as_view({'get': 'get_balance'}),
        name='wallet-balance'
    ),
    
    # Historique des transactions
    path(
        'wallet/transactions/',
        WalletViewSet.as_view({'get': 'get_transactions'}),
        name='wallet-transactions'
    ),
    
    # Statistiques complètes
    path(
        'wallet/stats/',
        WalletViewSet.as_view({'get': 'get_stats'}),
        name='wallet-stats'
    ),
    
    # Ajustement manuel (admin uniquement)
    path(
        'wallet/<uuid:pk>/adjust/',
        WalletViewSet.as_view({'post': 'adjust_wallet'}),
        name='wallet-adjust'
    ),
    
    # ============================================
    # WITHDRAWAL ENDPOINTS
    # ============================================
    
    # Créer une demande de retrait
    path(
        'withdrawals/request/',
        WithdrawalViewSet.as_view({'post': 'create_request'}),
        name='withdrawal-create-request'
    ),
    
    # Liste des demandes de retrait
    path(
        'withdrawals/',
        WithdrawalViewSet.as_view({'get': 'list'}),
        name='withdrawal-list'
    ),
    
    # Détails d'une demande de retrait
    path(
        'withdrawals/<uuid:pk>/',
        WithdrawalViewSet.as_view({'get': 'retrieve'}),
        name='withdrawal-detail'
    ),
    
    # Annuler une demande
    path(
        'withdrawals/<uuid:pk>/cancel/',
        WithdrawalViewSet.as_view({'patch': 'cancel'}),
        name='withdrawal-cancel'
    ),
    
    # Approuver une demande (admin)
    path(
        'withdrawals/<uuid:pk>/approve/',
        WithdrawalViewSet.as_view({'patch': 'approve'}),
        name='withdrawal-approve'
    ),
    
    # Rejeter une demande (admin)
    path(
        'withdrawals/<uuid:pk>/reject/',
        WithdrawalViewSet.as_view({'patch': 'reject'}),
        name='withdrawal-reject'
    ),
    
    # Marquer comme complété (admin)
    path(
        'withdrawals/<uuid:pk>/complete/',
        WithdrawalViewSet.as_view({'patch': 'complete'}),
        name='withdrawal-complete'
    ),
    
    # Statistiques des retraits
    path(
        'withdrawals/stats/',
        WithdrawalViewSet.as_view({'get': 'get_stats'}),
        name='withdrawal-stats'
    ),

]

urlpatterns += urls_patterns