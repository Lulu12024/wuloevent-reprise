# -*- coding: utf-8 -*-
"""
Created on November 03, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

import logging
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import permissions, views, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiResponse, OpenApiExample

from apps.organizations.models import Organization
from apps.super_sellers.permissions import IsVerifiedSuperSellerAndMember
from apps.super_sellers.serializers.stats import (
    StatsBaseFilterSerializer,
    StatsOverviewResponseSerializer,
    StatsByEventResponseSerializer,
    StatsBySellerResponseSerializer,
    StatsByPeriodQuerySerializer,
    StatsByPeriodResponseSerializer,
)
from apps.super_sellers.services.stats import (
    stats_overview, stats_by_event, stats_by_seller, stats_by_period
)
from apps.organizations.utils import resolve_organization_from_request

logger = logging.getLogger(__name__)

CACHE_TTL = 60 * 5


class BaseStatsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsVerifiedSuperSellerAndMember, IsAdminUser]

    def _check_org(self, request):
        org = resolve_organization_from_request(request)
        return org

@method_decorator(cache_page(CACHE_TTL), name="get")
class StatsOverviewView(BaseStatsView):

    @extend_schema(
        operation_id="super_seller_stats_overview",
        summary="Vue globale des statistiques",
        description="Retourne le total vendu, revenus, commissions, #vendeurs actifs, #événements impliqués.",
        parameters=[
            OpenApiParameter("organization_id", OpenApiTypes.STR, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("date_from", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("date_to", OpenApiTypes.DATE, OpenApiParameter.QUERY),
        ],
        responses={200: StatsOverviewResponseSerializer},
        tags=["Super-Vendeurs - Statistiques"],
        examples=[
            OpenApiExample(
                "Exemple simple",
                value={"total_tickets_sold": 120, "total_revenue": "950000.00", "total_commission": "95000.00",
                       "sellers_active": 8, "events_count": 3},
                response_only=True,
            )
        ]
    )
    def get(self, request):
        ser = StatsBaseFilterSerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        org = self._check_org(request)
        data = stats_overview(
            super_seller=org,
            date_from=ser.validated_data.get("date_from"),
            date_to=ser.validated_data.get("date_to"),
        )
        return Response(data)

@method_decorator(cache_page(CACHE_TTL), name="get")
class StatsByEventView(BaseStatsView):

    @extend_schema(
        operation_id="super_seller_stats_by_event",
        summary="Statistiques par événement",
        description="Regroupe les ventes par événement pour l’organisation super-vendeur.",
        parameters=[
            OpenApiParameter("organization_id", OpenApiTypes.STR, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("date_from", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("date_to", OpenApiTypes.DATE, OpenApiParameter.QUERY),
        ],
        responses={200: StatsByEventResponseSerializer},
        tags=["Super-Vendeurs - Statistiques"],
    )
    def get(self, request):
        ser = StatsBaseFilterSerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        org = self._check_org(request)
        results = stats_by_event(
            super_seller=org,
            date_from=ser.validated_data.get("date_from"),
            date_to=ser.validated_data.get("date_to"),
        )
        return Response({"results": results})

@method_decorator(cache_page(CACHE_TTL), name="get")
class StatsBySellerView(BaseStatsView):

    @extend_schema(
        operation_id="super_seller_stats_by_seller",
        summary="Statistiques par vendeur",
        description="Regroupe les ventes par vendeur affilié du super-vendeur.",
        parameters=[
            OpenApiParameter("organization_id", OpenApiTypes.STR, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("date_from", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("date_to", OpenApiTypes.DATE, OpenApiParameter.QUERY),
        ],
        responses={200: StatsBySellerResponseSerializer},
        tags=["Super-Vendeurs - Statistiques"],
    )
    def get(self, request):
        ser = StatsBaseFilterSerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        org = self._check_org(request)
        results = stats_by_seller(
            super_seller=org,
            date_from=ser.validated_data.get("date_from"),
            date_to=ser.validated_data.get("date_to"),
        )
        return Response({"results": results})

@method_decorator(cache_page(CACHE_TTL), name="get")
class StatsByPeriodView(BaseStatsView):

    @extend_schema(
        operation_id="super_seller_stats_by_period",
        summary="Statistiques par période",
        description="Regroupe les ventes par jour / semaine / mois (granularity=day|week|month).",
        parameters=[
            OpenApiParameter("organization_id", OpenApiTypes.STR, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("date_from", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("date_to", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("granularity", OpenApiTypes.STR, OpenApiParameter.QUERY, description="day|week|month"),
        ],
        responses={200: StatsByPeriodResponseSerializer},
        tags=["Super-Vendeurs - Statistiques"],
        examples=[
            OpenApiExample("Granularité jour", value={"results":[{"period":"2025-11-01","tickets_sold":10,"revenue":"50000.00","commission":"5000.00"}]}, response_only=True)
        ]
    )
    def get(self, request):
        ser = StatsByPeriodQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        org = self._check_org(request)
        results = stats_by_period(
            super_seller=org,
            granularity=ser.validated_data.get("granularity", "day"),
            date_from=ser.validated_data.get("date_from"),
            date_to=ser.validated_data.get("date_to"),
        )
        return Response({"results": results})
