# -*- coding: utf-8 -*-
"""    
Views pour la gestion des wallets des vendeurs.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from apps.super_sellers.models.seller_wallet import SellerWallet, WalletTransaction, WalletTransactionType
from apps.super_sellers.serializers.wallet import (
    WalletSerializer,
    WalletBalanceSerializer,
    WalletTransactionSerializer,
    WalletStatsSerializer,
    WalletAdjustmentSerializer,
)
from apps.super_sellers.services.wallet import SellerWalletService

logger = logging.getLogger(__name__)
class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour la gestion des wallets.
    
    Endpoints:
    - GET /api/wallet/balance          -> Consulter son solde
    - GET /api/wallet/transactions     -> Historique des transactions
    - GET /api/wallet/stats            -> Statistiques complètes
    - POST /api/wallet/adjust (admin)  -> Ajustement manuel
    
    Permissions: Le vendeur ne peut voir que son propre wallet
    """
    
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]
    
    def get_seller(self):
        """
        Récupère le profil vendeur de l'utilisateur connecté.
        Crée le profil s'il n'existe pas.
        """
        from apps.events.models.seller import Seller
        
        seller, created = Seller.objects.get_or_create(
            user=self.request.user,
            defaults={
                'status': 'ACTIVE',
                
            }
        )
        
        if created:
            logger.info(f"Profil vendeur créé automatiquement pour l'utilisateur {self.request.user.pk}")
        
        return seller
    
    def get_queryset(self):
        """Retourne le wallet du vendeur connecté"""
        seller = self.get_seller()
        return SellerWallet.objects.filter(seller=seller).select_related("seller", "seller__user")
    
    @extend_schema(
        summary="Consulter son solde",
        description="Récupère le solde actuel du wallet du vendeur connecté",
        tags=["Wallet"],
        responses={
            200: WalletBalanceSerializer,
            404: OpenApiResponse(description="Wallet non trouvé"),
        }
    )
    @action(detail=False, methods=["get"], url_path="balance")
    def get_balance(self, request):
        """
        Endpoint simple pour consulter uniquement le solde.
        GET /api/wallet/balance
        """
        seller = self.get_seller()  # ✅ Utilisé get_seller()
        
        # Récupérer ou créer le wallet
        wallet, created = SellerWallet.objects.get_or_create(seller=seller)
        
        if created:
            logger.info(f"Wallet créé automatiquement pour le vendeur {seller.pk}")
        
        serializer = WalletBalanceSerializer(wallet)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(
        summary="Historique des transactions",
        description="Récupère l'historique complet des transactions du wallet",
        tags=["Wallet"],
        parameters=[
            OpenApiParameter(
                name="transaction_type",
                type=str,
                description="Filtrer par type de transaction",
                enum=[choice[0] for choice in WalletTransactionType.choices],
            ),
            OpenApiParameter(
                name="limit",
                type=int,
                description="Nombre de transactions à retourner (défaut: 50)",
            ),
        ],
        responses={
            200: WalletTransactionSerializer(many=True),
        }
    )
    @action(detail=False, methods=["get"], url_path="transactions")
    def get_transactions(self, request):
        """
        Endpoint pour l'historique des transactions.
        GET /api/wallet/transactions?transaction_type=SALE&limit=100
        """
        seller = self.get_seller()  # ✅ Utilisé get_seller()
        
        # Récupérer ou créer le wallet
        wallet, _ = SellerWallet.objects.get_or_create(seller=seller)
        
        # Filtres
        queryset = WalletTransaction.objects.filter(wallet=wallet)
        
        # Filtre par type
        transaction_type = request.query_params.get("transaction_type")
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        
        # Limite
        limit = request.query_params.get("limit", 50)
        try:
            limit = int(limit)
            if limit > 500:
                limit = 500  # Maximum 500 transactions
        except ValueError:
            limit = 50
        
        transactions = queryset[:limit]
        
        serializer = WalletTransactionSerializer(transactions, many=True)
        
        return Response({
            "count": queryset.count(),
            "results": serializer.data
        }, status=status.HTTP_200_OK)
    
    @extend_schema(
        summary="Statistiques complètes du wallet",
        description="Récupère toutes les statistiques du wallet (soldes, transactions, etc.)",
        tags=["Wallet"],
        responses={
            200: WalletStatsSerializer,
        }
    )
    @action(detail=False, methods=["get"], url_path="stats")
    def get_stats(self, request):
        """
        Endpoint pour les statistiques complètes.
        GET /api/wallet/stats
        """
        seller = self.get_seller()  # ✅ Utilisé get_seller()
        
        # Récupérer les stats via le service
        stats = SellerWalletService.get_wallet_stats(seller)
        
        # Ajouter des stats supplémentaires
        wallet = SellerWallet.objects.get(seller=seller)
        
        # Stats par type de transaction
        type_stats = wallet.transactions.values("transaction_type").annotate(
            count=Count("pk"),
            total=Sum("amount")
        )
        
        for stat in type_stats:
            tx_type = stat["transaction_type"]
            stats[f"{tx_type.lower()}_count"] = stat["count"]
            stats[f"total_{tx_type.lower()}_amount"] = stat["total"]
        
        serializer = WalletStatsSerializer(stats)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(
        summary="Ajustement manuel du wallet (admin)",
        description="Permet à un administrateur d'ajuster manuellement le solde d'un wallet",
        request=WalletAdjustmentSerializer,
        tags=["Wallet"],
        responses={
            200: OpenApiResponse(description="Ajustement effectué avec succès"),
            400: OpenApiResponse(description="Données invalides"),
            403: OpenApiResponse(description="Permission refusée"),
        }
    )
    @action(detail=True, methods=["post"], url_path="adjust")
    def adjust_wallet(self, request, pk=None):
        """
        Endpoint pour ajustement manuel par un admin.
        POST /api/wallet/{wallet_id}/adjust
        
        Requiert des permissions admin.
        """
        if not request.user.is_staff:
            return Response(
                {"detail": "Vous n'avez pas les permissions pour effectuer cette action"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        wallet = self.get_object()
        
        serializer = WalletAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data["amount"]
        reason = serializer.validated_data["reason"]
        
        # Effectuer l'ajustement via le service
        try:
            transaction = SellerWalletService.adjust_wallet(
                seller=wallet.seller,
                amount=amount,
                reason=reason,
                admin_user=request.user
            )
            
            return Response({
                "message": "Ajustement effectué avec succès",
                "transaction_id": str(transaction.pk),
                "new_balance": str(wallet.balance),
                "amount_adjusted": str(amount),
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception(f"Erreur lors de l'ajustement du wallet {wallet.pk}: {e}")
            return Response(
                {"detail": "Erreur lors de l'ajustement"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )