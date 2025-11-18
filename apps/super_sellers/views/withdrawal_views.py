# -*- coding: utf-8 -*-
"""

Views pour la gestion des retraits des vendeurs.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from django.db import transaction as db_transaction
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from apps.super_sellers.models.seller_withdrawal import SellerWithdrawal, WithdrawalStatus
from apps.super_sellers.serializers.withdrawal import (
    WithdrawalCreateSerializer,
    WithdrawalSerializer,
    WithdrawalDetailSerializer,
    WithdrawalApprovalSerializer,
    WithdrawalRejectionSerializer,
    WithdrawalCancelSerializer,
    WithdrawalProcessSerializer,
    WithdrawalStatsSerializer,
)
from apps.super_sellers.services.withdrawal import (
    SellerWithdrawalService,
    WithdrawalProcessingError
)

logger = logging.getLogger(__name__)


class WithdrawalViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des retraits.
    
    Endpoints:
    - POST /api/withdrawals/request                -> Créer une demande
    - GET /api/withdrawals                         -> Liste des demandes
    - GET /api/withdrawals/{id}                    -> Détails d'une demande
    - PATCH /api/withdrawals/{id}/cancel           -> Annuler une demande
    - PATCH /api/withdrawals/{id}/approve (admin)  -> Approuver
    - PATCH /api/withdrawals/{id}/reject (admin)   -> Rejeter
    - PATCH /api/withdrawals/{id}/complete (admin) -> Marquer comme complété
    - GET /api/withdrawals/stats                   -> Statistiques
    
    Permissions: Le vendeur ne peut voir que ses propres retraits
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Sélectionne le serializer selon l'action"""
        if self.action == "create_request":
            return WithdrawalCreateSerializer
        elif self.action == "retrieve":
            return WithdrawalDetailSerializer
        elif self.action == "approve":
            return WithdrawalApprovalSerializer
        elif self.action == "reject":
            return WithdrawalRejectionSerializer
        elif self.action == "cancel":
            return WithdrawalCancelSerializer
        elif self.action == "complete":
            return WithdrawalProcessSerializer
        elif self.action == "get_stats":
            return WithdrawalStatsSerializer
        return WithdrawalSerializer
    
    def get_queryset(self):
        """Retourne les retraits du vendeur connecté (ou tous pour admin)"""
        if self.request.user.is_staff:
            # Admin voit tous les retraits
            return SellerWithdrawal.objects.all().select_related(
                "seller", "seller__user", "approved_by"
            ).order_by("-requested_at")
        else:
            # Vendeur voit uniquement ses retraits
            seller = self.request.seller
            return SellerWithdrawal.objects.filter(seller=seller).select_related(
                "seller", "seller__user", "approved_by"
            ).order_by("-requested_at")
    
    @extend_schema(
        summary="Créer une demande de retrait",
        description="Crée une nouvelle demande de retrait pour le vendeur connecté",
        tags=["Withdrawals"],
        request=WithdrawalCreateSerializer,
        responses={
            201: WithdrawalDetailSerializer,
            400: OpenApiResponse(description="Données invalides ou solde insuffisant"),
        }
    )
    @action(detail=False, methods=["post"], url_path="request")
    def create_request(self, request):
        """
        Créer une demande de retrait.
        POST /api/withdrawals/request
        """
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        
        try:
            withdrawal = serializer.save()
            
            # Retourner les détails complets
            response_serializer = WithdrawalDetailSerializer(withdrawal)
            
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except WithdrawalProcessingError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception(f"Erreur lors de la création de la demande de retrait: {e}")
            return Response(
                {"detail": "Erreur lors de la création de la demande"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Liste des demandes de retrait",
        description="Récupère la liste de toutes les demandes de retrait du vendeur",
        tags=["Withdrawals"],
        parameters=[
            OpenApiParameter(
                name="status",
                type=str,
                description="Filtrer par statut",
                enum=[choice[0] for choice in WithdrawalStatus.choices],
            ),
        ],
        responses={
            200: WithdrawalSerializer(many=True),
        }
    )
    def list(self, request, *args, **kwargs):
        """
        Liste des demandes de retrait.
        GET /api/withdrawals?status=PENDING
        """
        queryset = self.get_queryset()
        
        # Filtre par statut
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            "count": queryset.count(),
            "results": serializer.data
        }, status=status.HTTP_200_OK)
    
    @extend_schema(
        summary="Détails d'une demande de retrait",
        description="Récupère les détails complets d'une demande de retrait",
        tags=["Withdrawals"],
        responses={
            200: WithdrawalDetailSerializer,
            404: OpenApiResponse(description="Demande non trouvée"),
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        Détails d'une demande.
        GET /api/withdrawals/{id}
        """
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        summary="Annuler une demande de retrait",
        description="Permet au vendeur d'annuler sa propre demande (si elle n'est pas déjà traitée)",
        tags=["Withdrawals"],
        request=WithdrawalCancelSerializer,
        responses={
            200: OpenApiResponse(description="Demande annulée avec succès"),
            400: OpenApiResponse(description="Impossible d'annuler cette demande"),
        }
    )
    @action(detail=True, methods=["patch"], url_path="cancel")
    def cancel(self, request, pk=None):
        """
        Annuler une demande de retrait.
        PATCH /api/withdrawals/{id}/cancel
        """
        withdrawal = self.get_object()
        
        # Vérifier que c'est bien le vendeur qui annule sa propre demande
        if withdrawal.seller != request.seller and not request.user.is_staff:
            return Response(
                {"detail": "Vous ne pouvez annuler que vos propres demandes"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        reason = serializer.validated_data.get("reason", "Annulé par le vendeur")
        
        try:
            withdrawal.cancel(reason=reason)
            
            return Response({
                "message": "Demande de retrait annulée avec succès",
                "withdrawal_id": str(withdrawal.pk),
                "status": withdrawal.status,
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Approuver une demande de retrait (admin)",
        description="Permet à un administrateur d'approuver une demande de retrait en attente",
        tags=["Withdrawals"],
        request=WithdrawalApprovalSerializer,
        responses={
            200: OpenApiResponse(description="Demande approuvée avec succès"),
            403: OpenApiResponse(description="Permission refusée"),
        }
    )
    @action(detail=True, methods=["patch"], url_path="approve")
    def approve(self, request, pk=None):
        """
        Approuver une demande (admin uniquement).
        PATCH /api/withdrawals/{id}/approve
        """
        # Ajouter permission IsAdmin
        if not request.user.is_staff:
            return Response(
                {"detail": "Seuls les administrateurs peuvent approuver des retraits"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        withdrawal = self.get_object()
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notes = serializer.validated_data.get("notes")
        if notes:
            withdrawal.notes = notes
        
        try:
            withdrawal.approve(approved_by=request.user)
            
            return Response({
                "message": "Demande de retrait approuvée avec succès",
                "withdrawal_id": str(withdrawal.pk),
                "status": withdrawal.status,
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Rejeter une demande de retrait (admin)",
        description="Permet à un administrateur de rejeter une demande de retrait",
        tags=["Withdrawals"],
        request=WithdrawalRejectionSerializer,
        responses={
            200: OpenApiResponse(description="Demande rejetée avec succès"),
            403: OpenApiResponse(description="Permission refusée"),
        }
    )
    @action(detail=True, methods=["patch"], url_path="reject")
    def reject(self, request, pk=None):
        """
        Rejeter une demande (admin uniquement).
        PATCH /api/withdrawals/{id}/reject
        """
        if not request.user.is_staff:
            return Response(
                {"detail": "Seuls les administrateurs peuvent rejeter des retraits"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        withdrawal = self.get_object()
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        reason = serializer.validated_data["reason"]
        
        try:
            withdrawal.reject(reason=reason, rejected_by=request.user)
            
            return Response({
                "message": "Demande de retrait rejetée",
                "withdrawal_id": str(withdrawal.pk),
                "status": withdrawal.status,
                "reason": reason,
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Marquer un retrait comme complété (admin)",
        description="Permet à un admin de marquer manuellement un retrait comme complété (pour virements bancaires)",
        tags=["Withdrawals"],
        request=WithdrawalProcessSerializer,
        responses={
            200: OpenApiResponse(description="Retrait marqué comme complété"),
            403: OpenApiResponse(description="Permission refusée"),
        }
    )
    @action(detail=True, methods=["patch"], url_path="complete")
    def complete(self, request, pk=None):
        """
        Marquer comme complété manuellement (admin, pour virements bancaires).
        PATCH /api/withdrawals/{id}/complete
        """
        if not request.user.is_staff:
            return Response(
                {"detail": "Seuls les administrateurs peuvent compléter des retraits"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        withdrawal = self.get_object()
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        provider_reference = serializer.validated_data["provider_reference"]
        notes = serializer.validated_data.get("notes")
        
        if notes:
            withdrawal.notes = notes
            withdrawal.save(update_fields=["notes"])
        
        try:
            withdrawal.mark_as_completed(
                provider_reference=provider_reference,
                provider_response={
                    "manual_completion": True,
                    "completed_by": request.user.email,
                    "notes": notes,
                }
            )
            
            return Response({
                "message": "Retrait marqué comme complété avec succès",
                "withdrawal_id": str(withdrawal.pk),
                "status": withdrawal.status,
                "provider_reference": provider_reference,
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"Erreur lors de la complétion du retrait {withdrawal.pk}: {e}")
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Statistiques des retraits",
        description="Récupère les statistiques de retraits du vendeur (ou tous pour admin)",
        tags=["Withdrawals"],
        responses={
            200: WithdrawalStatsSerializer,
        }
    )
    @action(detail=False, methods=["get"], url_path="stats")
    def get_stats(self, request):
        """
        Statistiques des retraits.
        GET /api/withdrawals/stats
        """
        queryset = self.get_queryset()
        
        # Montants par statut
        stats = {
            "total_requested": queryset.aggregate(Sum("amount"))["amount__sum"] or 0,
            "total_completed": queryset.filter(
                status=WithdrawalStatus.COMPLETED
            ).aggregate(Sum("amount"))["amount__sum"] or 0,
            "total_pending": queryset.filter(
                status__in=[WithdrawalStatus.PENDING, WithdrawalStatus.APPROVED, WithdrawalStatus.PROCESSING]
            ).aggregate(Sum("amount"))["amount__sum"] or 0,
            "total_failed": queryset.filter(
                status=WithdrawalStatus.FAILED
            ).aggregate(Sum("amount"))["amount__sum"] or 0,
        }
        
        # Comptage par statut
        status_counts = queryset.values("status").annotate(count=Count("pk"))
        stats["count_total"] = queryset.count()
        
        for item in status_counts:
            stats[f"count_{item['status'].lower()}"] = item["count"]
        
        # Valeurs par défaut
        for status_choice in WithdrawalStatus.choices:
            key = f"count_{status_choice[0].lower()}"
            if key not in stats:
                stats[key] = 0
        
        # Stats par méthode
        method_counts = queryset.values("method").annotate(count=Count("pk"))
        for item in method_counts:
            method = item["method"].lower().replace("_", "_")
            stats[f"{method}_count"] = item["count"]
        
        serializer = self.get_serializer(stats)
        return Response(serializer.data, status=status.HTTP_200_OK)