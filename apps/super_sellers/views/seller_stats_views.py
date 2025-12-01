
"""
Created on November 03, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes, OpenApiResponse, OpenApiExample
)
from rest_framework import viewsets, permissions, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from apps.super_sellers.permissions import IsAdminOrSellerSelfOrSellerOfSuperSeller
from apps.super_sellers.paginator import SellerStatSetPagination
from apps.events.models.seller import Seller
from apps.super_sellers.services.seller_stats import (
    seller_stats_overview,
    seller_stats_by_event,
    seller_stocks_current,
)
from apps.super_sellers.serializers import (
    SellerStatsFilterSerializer,
    SellerStatsOverviewSerializer,
    SellerStatsByEventItemSerializer,
    SellerStockItemSerializer,
)




class _PaginationMixin:
    pagination_class = SellerStatSetPagination

    def _paginate(self, request, rows):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(rows, request)
        return paginator, page


class SellerStatsOverviewAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSellerSelfOrSellerOfSuperSeller]
    """
    GET /api/sellers/<uuid:pk>/
    """
    def _get_seller_and_check_obj_perm(self, request, pk):
        """
        Récupère le vendeur et vérifie les permissions.
        """
        from django.shortcuts import get_object_or_404
        from apps.events.models.seller import Seller
        
        seller = get_object_or_404(
            Seller.objects.select_related("user", "super_seller"),
            pk=pk
        )
        # self.check_object_permissions(request, seller)
        return seller
    
    @extend_schema(
        operation_id="seller_stats_overview",
        summary="Stats vendeur - Vue globale",
        description=(
            "Retourne les totaux (tickets vendus, revenu, commissions) pour **le vendeur ciblé**.\n\n"
            "**Accès** :\n"
            "- Admin : tous vendeurs\n"
            "- Super-vendeur : uniquement vendeurs de sa propre organisation\n"
            "- Vendeur : uniquement lui-même\n\n"
            "Filtres facultatifs : `date_from`, `date_to` (YYYY-MM-DD)."
        ),
        tags=["Vendeurs - Statistiques"],
        parameters=[
            OpenApiParameter("date_from", OpenApiTypes.DATE, OpenApiParameter.QUERY, description="Date min (inclus)"),
            OpenApiParameter("date_to", OpenApiTypes.DATE, OpenApiParameter.QUERY, description="Date max (inclus)"),
        ],
        responses={200: SellerStatsOverviewSerializer, 403: OpenApiResponse(description="Accès refusé")},
        examples=[
            OpenApiExample(
                "Réponse",
                value={"total_tickets_sold": 42, "total_revenue": "210000.00", "total_commission": "21000.00"},
                response_only=True,
            )
        ],
    )
    def get(self, request, pk):
        seller = self._get_seller_and_check_obj_perm(request, pk)
        fser = SellerStatsFilterSerializer(data=request.query_params)
        fser.is_valid(raise_exception=True)

        data = seller_stats_overview(
            seller,
            date_from=fser.validated_data.get("date_from"),
            date_to=fser.validated_data.get("date_to"),
        )
        return Response(data, status=status.HTTP_200_OK)


class SellerStatsByEventAPIView(_PaginationMixin, APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSellerSelfOrSellerOfSuperSeller]
    """
    GET /api/sellers/<uuid:pk>/by-event
    """
    def _get_seller_and_check_obj_perm(self, request, pk):
        """
        Récupère le vendeur et vérifie les permissions.
        """
        from django.shortcuts import get_object_or_404
        from apps.events.models.seller import Seller
        
        seller = get_object_or_404(
            Seller.objects.select_related("user", "super_seller"),
            pk=pk
        )
        # self.check_object_permissions(request, seller)
        return seller
    
    @extend_schema(
        operation_id="seller_stats_by_event",
        summary="Stats vendeur - Par événement",
        description=(
            "Agrège xxxxx les ventes **par événement** pour le vendeur.\n\n"
            "Tri : `order_by` parmi `tickets_sold`, `revenue`, `last_sale_at`, `event_date`, `event_name`. "
            "Utiliser `order=asc|desc` (défaut: `desc`).\n"
            "Pagination : `page`, `page_size`."
        ),
        tags=["Vendeurs - Statistiques"],
        parameters=[
            OpenApiParameter("date_from", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("date_to", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("order_by", OpenApiTypes.STR, OpenApiParameter.QUERY,
                             description="tickets_sold|revenue|last_sale_at|event_date|event_name"),
            OpenApiParameter("order", OpenApiTypes.STR, OpenApiParameter.QUERY,
                             description="asc|desc (default: desc)"),
            OpenApiParameter("page", OpenApiTypes.INT, OpenApiParameter.QUERY),
            OpenApiParameter("page_size", OpenApiTypes.INT, OpenApiParameter.QUERY),
        ],
        responses={200: SellerStatsByEventItemSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Réponse",
                value=[{
                    "event_id": "8fa2...c1", "event_name": "Concert X", "event_date": "2025-12-30",
                    "tickets_sold": 12, "revenue": "60000.00", "last_sale_at": "2025-11-02T19:10:00Z"
                }],
                response_only=True,
            )
        ]
    )
    def get(self, request, pk):
        seller = self._get_seller_and_check_obj_perm(request, pk)

        fser = SellerStatsFilterSerializer(data=request.query_params)
        fser.is_valid(raise_exception=True)

        rows = seller_stats_by_event(
            seller,
            date_from=fser.validated_data.get("date_from"),
            date_to=fser.validated_data.get("date_to"),
        )

        order_by = request.query_params.get("order_by", "last_sale_at")
        order = request.query_params.get("order", "desc")
        valid_keys = {"tickets_sold", "revenue", "last_sale_at", "event_date", "event_name"}
        if order_by not in valid_keys:
            order_by = "last_sale_at"

        rows_sorted = sorted(
            rows,
            key=lambda r: (
                r.get(order_by) if order_by not in {"event_name"} else (r.get(order_by) or "").lower()
            ) or 0,
            reverse=(order != "asc"),
        )

        paginator, page = self._paginate(request, rows_sorted)
        ser = SellerStatsByEventItemSerializer(page, many=True)
        return paginator.get_paginated_response(ser.data)
    
class SellerStockListAPIView(_PaginationMixin, APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSellerSelfOrSellerOfSuperSeller]
    
    def _get_seller_and_check_obj_perm(self, request, pk):
        """
        Récupère le vendeur et vérifie les permissions.
        """
        from django.shortcuts import get_object_or_404
        from apps.events.models.seller import Seller
        
        seller = get_object_or_404(
            Seller.objects.select_related("user", "super_seller"),
            pk=pk
        )
        # self.check_object_permissions(request, seller)
        return seller
    
    @extend_schema(
        operation_id="seller_stock_list",
        summary="Stocks alloués du vendeur",
        description=(
            "Liste les stocks alloués du vendeur (quantités, dispos, prix, commission).\n\n"
            "Tri : `order_by` parmi `available_quantity`, `total_allocated`, `total_sold`, "
            "`authorized_sale_price`, `commission_rate`, `event_name`, `ticket_name`.\n"
            "Utiliser `order=asc|desc` (défaut: `desc`).\n"
            "Pagination : `page`, `page_size`."
        ),
        tags=["Vendeurs - Statistiques"],
        parameters=[
            OpenApiParameter("order_by", OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter("order", OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter("page", OpenApiTypes.INT, OpenApiParameter.QUERY),
            OpenApiParameter("page_size", OpenApiTypes.INT, OpenApiParameter.QUERY),
        ],
        responses={200: SellerStockItemSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Réponse",
                value=[{
                    "event_id": "c7a6...e5", "event_name": "Festival Y",
                    "ticket_id": "0f1a...9aa", "ticket_name": "VIP",
                    "authorized_sale_price": "10000.00", "commission_rate": "10.00",
                    "total_allocated": 50, "total_sold": 12, "available_quantity": 38
                }],
                response_only=True,
            )
        ]
    )
    def get(self, request, pk):
        seller = self._get_seller_and_check_obj_perm(request, pk)
        rows = seller_stocks_current(seller)

        order_by = request.query_params.get("order_by", "available_quantity")
        order = request.query_params.get("order", "desc")
        valid_keys = {
            "available_quantity", "total_allocated", "total_sold",
            "authorized_sale_price", "commission_rate", "event_name", "ticket_name"
        }
        if order_by not in valid_keys:
            order_by = "available_quantity"

        rows_sorted = sorted(
            rows,
            key=lambda r: (
                r.get(order_by) if order_by not in {"event_name", "ticket_name"} else (r.get(order_by) or "").lower()
            ) or 0,
            reverse=(order != "asc"),
        )

        paginator, page = self._paginate(request, rows_sorted)
        ser = SellerStockItemSerializer(page, many=True)
        return paginator.get_paginated_response(ser.data)
