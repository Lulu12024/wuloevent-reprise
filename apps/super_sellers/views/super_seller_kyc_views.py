
"""
Created on November 5, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""


from rest_framework import status, permissions, views
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter, OpenApiTypes

from apps.organizations.models import Organization
from apps.super_sellers.serializers.super_seller_kyc import (
    SuperSellerKYCSubmitSerializer, AdminSuperSellerKYCReviewSerializer
)
from apps.super_sellers.models.kyc_submission import SuperSellerKYCSubmission
from apps.events.models.super_seller_profile import SuperSellerProfile, KYCStatus
from apps.super_sellers.permissions import IsSuperSellerMember

from apps.super_sellers.notifications import (
    notify_admin_super_seller_kyc_submitted,
    notify_super_seller_kyc_verified,
    notify_super_seller_kyc_rejected,
)

class SuperSellerKYCSubmitView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsSuperSellerMember]
    parser_classes = []

    @extend_schema(
        operation_id="super_seller_kyc_submit",
        summary="Soumettre KYC (super-vendeur)",
        description="Upload des documents KYC du super-vendeur. Requiert `organization_id`.",
        tags=["Super-Vendeurs - KYC"],
        request=SuperSellerKYCSubmitSerializer,
        responses={201: OpenApiTypes.OBJECT},
        examples=[OpenApiExample(
            "Form-Data", 
            value={"organization_id": "uuid-orga", "identity_type": "ID_CARD"},
            request_only=True
        )]
    )
    def post(self, request, *args, **kwargs):
        org_id = request.data.get("organization_id")
        org = get_object_or_404(Organization, pk=org_id)
        if not org.is_super_seller():
            return Response({"detail": "Organisation non Super-Vendeur."}, status=400)

        ser = SuperSellerKYCSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        sub = SuperSellerKYCSubmission.objects.create(
            super_seller=org,
            submitted_by=request.user,
            **ser.validated_data
        )
        # On met le profil en PENDING (si existant)
        profile = getattr(org, "super_seller_profile", None)
        if profile:
            profile.kyc_status = KYCStatus.PENDING
            profile.save(update_fields=["kyc_status"])

        notify_admin_super_seller_kyc_submitted(sub)
        return Response({"id": str(sub.pk), "status": sub.status}, status=201)


class AdminSuperSellerKYCVerifyView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    @extend_schema(
        operation_id="admin_super_seller_kyc_verify",
        summary="(Admin) Vérifier / Rejeter KYC d'un super-vendeur",
        description="Admin : `action=verify|reject` avec raison optionnelle.",
        tags=["Admin - KYC"],
        request=AdminSuperSellerKYCReviewSerializer,
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
    def patch(self, request, org_id, *args, **kwargs):
        org = get_object_or_404(Organization, pk=org_id)
        sub = org.kyc_submissions.order_by("-timestamp").first()  # dernière soumission
        if not sub:
            return Response({"detail": "Aucune soumission KYC."}, status=404)

        ser = AdminSuperSellerKYCReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        action = ser.validated_data["action"]

        profile, _ = SuperSellerProfile.objects.get_or_create(organization=org)

        if action == "verify":
            sub.status = KYCStatus.VERIFIED
            sub.reviewed_by = request.user
            sub.reviewed_at = timezone.now()
            sub.rejection_reason = ""
            sub.save()

            # Propagation sur le profil
            profile.kyc_status = KYCStatus.VERIFIED
            profile.kyc_verified_by = request.user
            profile.kyc_verified_at = timezone.now()

            # Transfert des fichiers clés (si tu veux les stocker aussi dans le profil)
            if sub.identity_type == "PASSPORT" and sub.passport_image:
                profile.identity_document = sub.passport_image
            elif sub.id_front and sub.id_back:
                profile.identity_document = sub.id_front  # ou stocker les deux dans additional_documents
            if sub.business_registration:
                profile.business_registration = sub.business_registration
            if sub.proof_of_address:
                profile.proof_of_address = sub.proof_of_address
            profile.save()

            notify_super_seller_kyc_verified(org, sub)
            return Response({"detail": "KYC vérifié."}, status=200)
        else:
            sub.status = KYCStatus.REJECTED
            sub.reviewed_by = request.user
            sub.reviewed_at = timezone.now()
            sub.rejection_reason = ser.validated_data.get("reason", "")
            sub.save()

            profile.kyc_status = KYCStatus.REJECTED
            profile.kyc_rejection_reason = sub.rejection_reason
            profile.save(update_fields=["kyc_status", "kyc_rejection_reason"])

            notify_super_seller_kyc_rejected(org, sub)
            return Response({"detail": "KYC rejeté."}, status=200)
