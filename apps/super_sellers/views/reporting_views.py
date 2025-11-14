
"""
Created on November 05, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

from rest_framework import views, permissions, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiResponse, OpenApiExample

from apps.organizations.models import Organization
from apps.super_sellers.models.reporting import SalesReportPreference, SalesReport
from apps.super_sellers.serializers.reporting import (
    SalesReportPreferenceSerializer, SalesReportArchiveSerializer
)
from apps.super_sellers.serializers.reporting import (
    SalesReportPreferenceSerializer, SalesReportArchiveSerializer
)
from apps.super_sellers.services.reporting import compute_period, fetch_sales_data, build_and_archive_report
from apps.super_sellers.permissions import IsVerifiedSuperSellerAndMember

class ReportPreferenceView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsVerifiedSuperSellerAndMember]

    @extend_schema(
        operation_id="super_seller_report_pref_get",
        summary="Préférences de rapport (super-vendeur)",
        responses={200: SalesReportPreferenceSerializer},
        tags=["Super-Vendeurs - Rapports"],
        parameters=[OpenApiParameter("organization_id", OpenApiTypes.STR, OpenApiParameter.QUERY, required=True)]
    )
    def get(self, request):
        org_id = request.query_params.get("organization_id")
        org = Organization.objects.get(pk=org_id)
        pref, _ = SalesReportPreference.objects.get_or_create(super_seller=org)
        return Response(SalesReportPreferenceSerializer(pref).data)

    @extend_schema(
        operation_id="super_seller_report_pref_update",
        summary="Mettre à jour les préférences",
        request=SalesReportPreferenceSerializer,
        responses={200: SalesReportPreferenceSerializer},
        tags=["Super-Vendeurs - Rapports"],
    )
    def put(self, request):
        org_id = request.data.get("organization_id")
        org = Organization.objects.get(pk=org_id)
        pref, _ = SalesReportPreference.objects.get_or_create(super_seller=org)
        ser = SalesReportPreferenceSerializer(instance=pref, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

class ReportPreviewView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsVerifiedSuperSellerAndMember]

    @extend_schema(
        operation_id="super_seller_report_preview",
        summary="Prévisualiser les données de rapport pour une période",
        parameters=[
            OpenApiParameter("organization_id", OpenApiTypes.STR, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("frequency", OpenApiTypes.STR, OpenApiParameter.QUERY, description="DAILY|WEEKLY|MONTHLY"),
        ],
        responses={200: OpenApiResponse(description="Données agrégées JSON")},
        examples=[OpenApiExample("Réponse", value={"totals":{"tickets":12,"revenue":"60000.00"}})]
    )
    def get(self, request):
        org_id = request.query_params.get("organization_id")
        frequency = request.query_params.get("frequency", "WEEKLY")
        org = Organization.objects.get(pk=org_id)
        start, end = compute_period(frequency)
        data = fetch_sales_data(org, start, end)
        return Response(data)

class ReportGenerateNowView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsVerifiedSuperSellerAndMember]

    @extend_schema(
        operation_id="super_seller_report_generate_now",
        summary="Générer et envoyer le rapport maintenant",
        request=None,
        responses={200: SalesReportArchiveSerializer},
        tags=["Super-Vendeurs - Rapports"],
        examples=[OpenApiExample("Réponse", value={"file_path":"reports/2025/11/....pdf"})],
    )
    def post(self, request):
        org_id = request.data.get("organization_id")
        org = Organization.objects.get(pk=org_id)

        pref, _ = SalesReportPreference.objects.get_or_create(super_seller=org)
        report, _data = build_and_archive_report(org, pref.frequency, pref.fmt)

        # Optionnel : envoi immédiat
        # (réutiliser les helpers d’envoi email/whatsapp si tu veux envoyer ici)
        return Response(SalesReportArchiveSerializer(report).data, status=status.HTTP_200_OK)

class ReportHistoryListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsVerifiedSuperSellerAndMember]

    @extend_schema(
        operation_id="super_seller_report_history",
        summary="Lister les rapports archivés",
        parameters=[
            OpenApiParameter("organization_id", OpenApiTypes.STR, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("date_from", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("date_to", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("page", OpenApiTypes.INT, OpenApiParameter.QUERY),
            OpenApiParameter("page_size", OpenApiTypes.INT, OpenApiParameter.QUERY),
        ],
        responses={200: SalesReportArchiveSerializer(many=True)},
        tags=["Super-Vendeurs - Rapports"],
    )
    def get(self, request):
        from rest_framework.pagination import PageNumberPagination
        org_id = request.query_params.get("organization_id")
        org = Organization.objects.get(pk=org_id)

        qs = SalesReport.objects.filter(super_seller=org).order_by("-generated_at")
        if request.query_params.get("date_from"):
            qs = qs.filter(period_start__gte=request.query_params.get("date_from"))
        if request.query_params.get("date_to"):
            qs = qs.filter(period_end__lte=request.query_params.get("date_to"))

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        ser = SalesReportArchiveSerializer(page, many=True)
        return paginator.get_paginated_response(ser.data)
