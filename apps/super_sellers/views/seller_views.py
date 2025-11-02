# -*- coding: utf-8 -*-
"""
Created on October 29, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiExample,OpenApiResponse
from rest_framework import viewsets, permissions, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.super_sellers.permissions import IsVerifiedSuperSellerAndMember
from apps.organizations.models import Organization
from apps.events.models.seller import Seller, SellerStatus, SellerKYCStatus
from apps.super_sellers.serializers.sellers import (
    SellerListSerializer,
    SellerDetailSerializer,
    SellerStatusUpdateSerializer,
)
from apps.super_sellers.serializers.light import LightSellerSerializer, LightEventSerializer
from apps.events.serializers import LightTicketSerializer
from apps.super_sellers.serializers.stock_allocation import StockAllocationSerializer
from apps.super_sellers.services.stock import allocate_ticket_stock, StockAllocationError
from apps.events.models.seller import Seller
from apps.organizations.utils import resolve_organization_from_request
from apps.super_sellers.services.notification import notify_seller_stock_allocated



class SellerManagementViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Endpoints:
    - GET    /api/super-sellers/sellers/                  -> list
    - GET    /api/super-sellers/sellers/<uuid:pk>/        -> retrieve
    - PATCH  /api/super-sellers/sellers/<uuid:pk>/status/ -> update_status (activer/suspendre)
    - DELETE /api/super-sellers/sellers/<uuid:pk>/        -> destroy (soft remove)
    - POST   /api/super-sellers/sellers/<uuid:pk>/stock/allocate/ -> allocate_stock
    """
    permission_classes = [permissions.IsAuthenticated, IsVerifiedSuperSellerAndMember]
    queryset = Seller.objects.select_related("user", "super_seller").all()
    lookup_field = "pk"

    # ---------- Résolution ----------
    def initial(self, request, *args, **kwargs):
        """

        """
        self.organization = resolve_organization_from_request(self, request)

        super().initial(request, *args, **kwargs)

    # ---------- Queryset filtré ----------
    def get_queryset(self):
        org = getattr(self, "organization", None)
        if not org:
            return Seller.objects.none()

        qs = super().get_queryset().filter(super_seller=org)

        # Filtres
        req = self.request
        status_param = req.query_params.get("status")
        if status_param in dict(SellerStatus.choices):
            qs = qs.filter(status=status_param)

        kyc_param = req.query_params.get("kyc_status")
        if kyc_param in dict(SellerKYCStatus.choices):
            qs = qs.filter(kyc_status=kyc_param)

        active_param = req.query_params.get("active")
        if active_param is not None:
            val = str(active_param).lower()
            if val in ("true", "1", "yes"):
                qs = qs.filter(active=True)
            elif val in ("false", "0", "no"):
                qs = qs.filter(active=False)

        search = req.query_params.get("search")
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search)
                | Q(user__phone__icontains=search)
                | Q(phone_number__icontains=search)
                | Q(whatsapp_number__icontains=search)
            )

        date_min = req.query_params.get("date_min")
        if date_min:
            qs = qs.filter(invited_at__date__gte=date_min)

        date_max = req.query_params.get("date_max")
        if date_max:
            qs = qs.filter(invited_at__date__lte=date_max)

        return qs.order_by("-timestamp")

    # ---------- List ----------
    @extend_schema(
        summary="Liste des vendeurs de l'organisation",
        parameters=[
            OpenApiParameter(name="organization_id", type=OpenApiTypes.STR, required=False,
                             description="UUID de l'organisation du super-vendeur"),
            OpenApiParameter(name="status", type=OpenApiTypes.STR, description="ACTIVE | INVITED | SUSPENDED | INACTIVE"),
            OpenApiParameter(name="kyc_status", type=OpenApiTypes.STR, description="VERIFIED | PENDING | REJECTED | NOT_REQUIRED"),
            OpenApiParameter(name="active", type=OpenApiTypes.BOOL),
            OpenApiParameter(name="search", type=OpenApiTypes.STR, description="Nom, email, téléphone…"),
            OpenApiParameter(name="date_min", type=OpenApiTypes.DATE),
            OpenApiParameter(name="date_max", type=OpenApiTypes.DATE),
            OpenApiParameter(name="page", type=OpenApiTypes.INT),
            OpenApiParameter(name="page_size", type=OpenApiTypes.INT),
        ],
        responses={200: SellerListSerializer(many=True)},
        tags=["Super-Vendeurs - Vendeurs"],
    )
    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(qs)
        if page is not None:
            ser = SellerListSerializer(page, many=True)
            return self.get_paginated_response(ser.data)

        ser = SellerListSerializer(qs, many=True)
        return Response(ser.data)

    # ---------- Retrieve ----------
    @extend_schema(
        summary="Détails d'un vendeur",
        parameters=[OpenApiParameter(name="organization_id", type=OpenApiTypes.STR, required=False)],
        responses={200: SellerDetailSerializer},
        tags=["Super-Vendeurs - Vendeurs"],
    )
    def retrieve(self, request, pk=None, *args, **kwargs):
        seller = get_object_or_404(self.get_queryset(), pk=pk)
        ser = SellerDetailSerializer(seller)
        return Response(ser.data)

    # ---------- Update status ----------
    @extend_schema(
        summary="Modifier le statut d'un vendeur (activer/suspendre)",
        request=SellerStatusUpdateSerializer,
        responses={200: SellerDetailSerializer},
        tags=["Super-Vendeurs - Vendeurs"],
        examples=[
            OpenApiExample("Activer", value={"action": "activate"}),
            OpenApiExample("Suspendre", value={"action": "suspend", "reason": "Non-respect des règles"}),
        ],
    )
    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, pk=None):
        seller = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = SellerStatusUpdateSerializer(data=request.data, context={"seller": seller})
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]
        reason = serializer.validated_data.get("reason", "")

        if action == "activate":
            seller.activate()
        else:
            seller.suspend(reason=reason)

        out = SellerDetailSerializer(seller)
        return Response(out.data, status=200)

    # ---------- Destroy (soft) ----------
    @extend_schema(
        summary="Retirer un vendeur de l'organisation (soft delete)",
        description="Désactive le vendeur et met le statut à INACTIVE.",
        responses={204: None},
        tags=["Super-Vendeurs - Vendeurs"],
    )
    def destroy(self, request, pk=None, *args, **kwargs):
        seller = get_object_or_404(self.get_queryset(), pk=pk)
        seller.status = SellerStatus.INACTIVE
        seller.active = False
        seller.suspension_reason = (seller.suspension_reason or "") + "\nRetiré par super-vendeur."
        seller.save(update_fields=["status", "active", "suspension_reason"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ---------- Allocate stock ----------
    @extend_schema(
        summary="Allouer du stock de tickets à un vendeur",
        request=StockAllocationSerializer,
        responses={
            200: OpenApiResponse(description="Stock alloué"),
            400: OpenApiResponse(description="Erreur de validation"),
            403: OpenApiResponse(description="Accès refusé"),
            409: OpenApiResponse(description="Stock insuffisant"),
        },
        tags=["Super-Vendeurs - Stocks"],
    )
    @action(detail=True, methods=["post"], url_path="stock/allocate")
    def allocate_stock(self, request, pk=None):
        seller = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = StockAllocationSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        ticket = data["ticket"]
        quantity = data["quantity"]
        authorized_sale_price = data["authorized_sale_price"]
        commission_rate = data["commission_rate"]
        notes = data.get("notes", "")

        org = getattr(self, "organization", None)

        try:
            stock = allocate_ticket_stock(
                super_seller_org=org,
                seller=seller,
                ticket=ticket,
                quantity=quantity,
                authorized_sale_price=authorized_sale_price,
                commission_rate=commission_rate,
                notes=notes,
                initiated_by=request.user,
            )
        except StockAllocationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)

        try:
            notify_seller_stock_allocated(seller, stock, quantity)
        except Exception:
            pass

        return Response(
            {
                "seller": LightSellerSerializer(seller).data,
                "ticket": LightTicketSerializer(ticket).data,
                "event": LightEventSerializer(ticket.event).data,
                "stock": {
                    "total_allocated": stock.total_allocated,
                    "total_sold": stock.total_sold,
                    "available_for_seller": stock.available_quantity,
                    "authorized_sale_price": str(stock.authorized_sale_price),
                    "commission_rate": str(stock.commission_rate),
                },
            },
            status=status.HTTP_200_OK,
        )
