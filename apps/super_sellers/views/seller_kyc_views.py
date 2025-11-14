
"""
Created on November 5, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

from rest_framework import status, permissions, views
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema

from apps.super_sellers.models.kyc_submission import SellerKYCSubmission
from apps.events.models.seller import Seller, SellerKYCStatus
from apps.super_sellers.serializers.seller_kyc import SellerKYCSubmitSerializer, SellerKYCReviewSerializer
from apps.super_sellers.permissions import IsSellerSelf, IsSuperSellerOwnerOfSellerOrAdmin
from apps.super_sellers.notifications import (
    notify_seller_kyc_submitted, 
    notify_seller_kyc_verified, 
    notify_seller_kyc_rejected
)

class SellerKYCSubmitView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsSellerSelf]

    @extend_schema(
        operation_id="seller_kyc_submit",
        summary="Soumettre KYC (vendeur)",
        tags=["Vendeurs - KYC"],
        request=SellerKYCSubmitSerializer,
        responses={201: None}
    )
    def post(self, request, *args, **kwargs):
        seller = getattr(request, "seller_profile", None)
        ser = SellerKYCSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        sub = SellerKYCSubmission.objects.create(
            seller=seller,
            submitted_by=request.user,
            **ser.validated_data
        )

        seller.kyc_status = SellerKYCStatus.PENDING
        seller.save(update_fields=["kyc_status"])

        notify_seller_kyc_submitted(seller, sub)
        return Response({"id": str(sub.pk), "status": sub.status}, status=201)


class SuperSellerReviewSellerKYCView(views.APIView):
    """
    Super-vendeur (propriétaire du vendeur) OU Admin peut valider/rejeter.
    """
    permission_classes = [permissions.IsAuthenticated, IsSuperSellerOwnerOfSellerOrAdmin]

    def get_seller_object(self, seller_id):
        return get_object_or_404(Seller, pk=seller_id)

    @extend_schema(
        operation_id="super_seller_review_seller_kyc",
        summary="(Super-Vendeur/Admin) Vérifier KYC d'un vendeur",
        tags=["Super-Vendeurs - KYC"],
        request=SellerKYCReviewSerializer,
        responses={200: None, 404: None}
    )
    def patch(self, request, seller_id, *args, **kwargs):
        seller = self.get_seller_object(seller_id)
        sub = seller.kyc_submissions.order_by("-timestamp").first()
        if not sub:
            return Response({"detail": "Aucune soumission KYC."}, status=404)

        ser = SellerKYCReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        action = ser.validated_data["action"]

        if action == "verify":
            sub.status = SellerKYCStatus.VERIFIED
            sub.reviewed_by = request.user
            sub.reviewed_at = timezone.now()
            sub.rejection_reason = ""
            sub.save()

            seller.kyc_status = SellerKYCStatus.VERIFIED
            seller.save(update_fields=["kyc_status"])

            notify_seller_kyc_verified(seller, sub)
            return Response({"detail": "KYC vendeur vérifié."}, status=200)
        else:
            reason = ser.validated_data.get("reason") or ""
            sub.status = SellerKYCStatus.REJECTED
            sub.reviewed_by = request.user
            sub.reviewed_at = timezone.now()
            sub.rejection_reason = reason
            sub.save()

            seller.kyc_status = SellerKYCStatus.REJECTED
            seller.save(update_fields=["kyc_status"])

            notify_seller_kyc_rejected(seller, sub)
            return Response({"detail": "KYC vendeur rejeté."}, status=200)
