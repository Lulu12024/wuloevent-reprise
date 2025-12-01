
"""
Created on October 29, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

import logging
from rest_framework import permissions, status, views
from rest_framework.response import Response
from drf_spectacular.utils import (
    extend_schema, OpenApiExample, OpenApiResponse
)
from apps.super_sellers.serializers.sales import SellerTicketSellSerializer
from apps.super_sellers.services.sales import sell_tickets_by_seller, SellerSaleError
from apps.events.serializers import LightTicketSerializer, LightEventSerializer
from apps.super_sellers.serializers.light import LightSellerSerializer 
from apps.super_sellers.permissions import IsActiveSeller 

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


class SellerTicketSellView(views.APIView):
    """
    POST /api/sellers/tickets/sell
    Le vendeur connecté vend un ticket de son stock alloué.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_seller(self, user):
        """
        Récupère le profil seller de l'utilisateur.
        """
        from apps.events.models.seller import Seller
        try:
            return Seller.objects.filter(user=user).first()
        except Seller.DoesNotExist:
            return None
        
    @extend_schema(
        operation_id="seller_ticket_sell",
        summary="Vente de tickets par un vendeur",
        description=(
            "Effectue une vente  depuis le stock alloué au vendeur :\n"
        ),
        tags=["Vendeurs - Ventes"],
        request=SellerTicketSellSerializer,
        responses={
            #200: OpenApiResponse(description="Vente réussie", response=SellerTicketSellResponseSerializer),
            400: OpenApiResponse(description="Erreur de validation de la requête"),
            403: OpenApiResponse(description="Accès refusé (vendeur inactif ou non autorisé)"),
            409: OpenApiResponse(description="Stock insuffisant (vendeur ou événement)"),
            500: OpenApiResponse(description="Erreur interne lors du traitement de la vente"),
        },
        examples=[
            OpenApiExample(
                "Requête (vente par Mobile Money)",
                value={
                    "ticket": "0f1a4e1d-5a7c-4f2c-9c2a-6b7e21d1c9aa",
                    "quantity": 2,
                    "buyer_full_name": "Julien DUPONT",
                    "buyer_email": "julien@example.com",
                    "buyer_phone": "+22901020304",
                    "payment_channel": "MOBILE_MONEY",
                    "payment_reference": "MOMO-REF-12345",
                    "paid_amount": "10000.00",
                    "notes": "Vente sur place"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Réponse succès",
                value={
                    "order": {
                        "id": "1c3b7a80-1b2a-4b90-a2f0-99c81234abcd",
                        "order_id": "CMD-AB12CD34",
                        "status": "FINISHED",
                        "total": "10000.00",
                        "buyer": {
                            "name": "Julien DUPONT",
                            "email": "julien@example.com",
                            "phone": "+22901020304"
                        }
                    },
                    "seller": {
                        "id": "7d8a1a52-55f0-4b7e-b2d4-0c1fabc12345",
                        "user_full_name": "Sarah Vendeuse",
                        "status": "ACTIVE"
                    },
                    "ticket": {
                        "pk": "0f1a4e1d-5a7c-4f2c-9c2a-6b7e21d1c9aa",
                        "name": "Standard",
                        "category": "a2b3c4d5-...-...",
                        "description": "Accès général",
                        "price": "5000.00",
                        "expiry_date": "2025-12-31T23:59:59Z"
                    },
                    "event": {
                        "pk": "c7a6e5d4-...-...",
                        "name": "Concert X",
                        "date": "2025-12-31",
                        "hour": "21:00:00"
                    },
                    "quantity": 2,
                    "seller_stock": {
                        "total_allocated": 50,
                        "total_sold": 12,
                        "available_for_seller": 38,
                        "authorized_sale_price": "5000.00",
                        "commission_rate": "10.00"
                    },
                    "etickets": [
                        {
                            "id": "e1a2b3c4-...-...",
                            "name": "E-Ticket N° 120 | Concert X",
                            "qr_code_data": "{\"id64\":\"...\",\"secret_phrase\":\"...\"}",
                            "expiration_date": "2025-12-31T23:59:59Z"
                        },
                        {
                            "id": "f1a2b3c4-...-...",
                            "name": "E-Ticket N° 121 | Concert X",
                            "qr_code_data": "{\"id64\":\"...\",\"secret_phrase\":\"...\"}",
                            "expiration_date": "2025-12-31T23:59:59Z"
                        }
                    ]
                },
                response_only=True,
            ),
            OpenApiExample(
                "Erreur stock insuffisant",
                value={"detail": "Stock insuffisant chez le vendeur."},
                status_codes=["409"],
                response_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        serializer = SellerTicketSellSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # ✅ CORRECTION : Récupérer le seller depuis l'utilisateur
        seller = self.get_seller(request.user)
        
        if not seller:
            return Response(
                {"detail": "Profil vendeur introuvable. Vous devez être enregistré comme vendeur."},
                status=status.HTTP_403_FORBIDDEN
            )
        

        try:
            order, e_tickets, stock = sell_tickets_by_seller(
                seller=seller,
                ticket=data["ticket"],
                quantity=data["quantity"],
                paid_amount=data["paid_amount"],
                payment_channel=data.get("payment_channel", "MOBILE_MONEY"),
                payment_reference=data.get("payment_reference", ""),
                buyer_full_name=data.get("buyer_full_name", ""),
                buyer_email=data.get("buyer_email", ""),
                buyer_phone=data.get("buyer_phone", ""),
                notes=data.get("notes", ""),
            )
        except SellerSaleError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.exception(e)
            return Response(
                {"detail": "Erreur interne lors de la vente."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Réponse
        payload = {
            "order": {
                "id": str(order.pk),
                "order_id": order.order_id,
                "status": order.status,
                "total": str(order.total),
                "buyer": {
                    "name": order.name,
                    "email": order.email,
                    "phone": order.phone,
                },
            },
            "seller": LightSellerSerializer(seller).data if hasattr(seller, "user") else None,
            "ticket": LightTicketSerializer(data["ticket"]).data,
            "event": LightEventSerializer(data["ticket"].event).data,
            "quantity": data["quantity"],
            "seller_stock": {
                "total_allocated": stock.total_allocated,
                "total_sold": stock.total_sold,
                "available_for_seller": stock.available_quantity,
                "authorized_sale_price": str(stock.authorized_sale_price),
                "commission_rate": str(stock.commission_rate),
            },
            "etickets": [
                {
                    "id": str(et.pk),
                    "name": et.name,
                    "qr_code_data": et.qr_code_data,
                    "expiration_date": et.expiration_date,
                }
                for et in e_tickets
            ],
        }
        return Response(payload, status=status.HTTP_200_OK)
