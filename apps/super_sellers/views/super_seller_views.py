# -*- coding: utf-8 -*-
"""
Created on October 29, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiTypes
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404

from apps.organizations.models import Organization
from apps.super_sellers.permissions import IsVerifiedSuperSellerAndMember
from apps.super_sellers.serializers.seller_invitation import (
    SellerInvitationCreateSerializer, 
    SellerInvitationSerializer, 
    SellerInvitationRespondSerializer
)
from apps.super_sellers.models import (
    SellerInvitation, InvitationChannel
)
# from apps.super_sellers.services.invitations import (
#     send_invitation_email, 
#     send_invitation_sms, 
#     send_invitation_whatsapp
# )

class InviteSellerAPIView(APIView):
    """
    POST /api/super-sellers/sellers/invite
    """
    permission_classes = [permissions.IsAuthenticated, IsVerifiedSuperSellerAndMember]

    @extend_schema(
        summary="Inviter un vendeur",
        description=(
            "Invite un vendeur (email/sms/whatsapp) pour rejoindre l'organisation Super-Vendeur.\n"
            "- Requiert: Auth + membre de l’orga + orga KYC VERIFIED\n"
        ),
        request=SellerInvitationCreateSerializer,
        responses={201: SellerInvitationSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                'Payload email',
                value={"organization_id": "uuid-org", "email": "sarah@example.com", "channel": "EMAIL"},
                request_only=True
            ),
            OpenApiExample(
                'Réponse succès',
                value={"token": "abcd...","status":"PENDING","expires_at":"2025-11-06T12:00:00Z"},
                response_only=True
            ),
        ],
        tags=['Super-Vendeurs - Invitations']
    )
    def post(self, request, *args, **kwargs):
        org_id = request.data.get("organization_id")
        self.organization = get_object_or_404(Organization, pk=org_id)

        # Permissions (lit self.organization)
        self.check_permissions(request)

        serializer = SellerInvitationCreateSerializer(
            data=request.data, context={"request": request, "organization": self.organization}
        )
        serializer.is_valid(raise_exception=True)
        invitation = serializer.save()

        # Envoi
        if invitation.channel == InvitationChannel.EMAIL and invitation.email:
            return
            #send_invitation_email(invitation)
        elif invitation.channel == InvitationChannel.SMS and invitation.phone:
            return
            #send_invitation_sms(invitation)
        elif invitation.channel == InvitationChannel.WHATSAPP and invitation.phone:
            return
            #send_invitation_whatsapp(invitation)

        out = SellerInvitationSerializer(invitation)
        return Response(out.data, status=status.HTTP_201_CREATED)


class SellerInvitationRespondAPIView(APIView):
    """
    POST /api/super-sellers/sellers/invitations/{token}/respond
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Répondre à une invitation vendeur",
        description="Accepter ou refuser l’invitation via le token reçu par email/SMS/WhatsApp.",
        request=SellerInvitationRespondSerializer,
        responses={200: SellerInvitationSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample('Accepter', value={"action": "accept"}, request_only=True),
            OpenApiExample('Refuser', value={"action": "decline"}, request_only=True),
        ],
        tags=['Super-Vendeurs - Invitations']
    )
    def post(self, request, token, *args, **kwargs):
        invitation = get_object_or_404(SellerInvitation, token=token)
        serializer = SellerInvitationRespondSerializer(data=request.data, context={"invitation": invitation})
        serializer.is_valid(raise_exception=True)
        invitation = serializer.save()
        out = SellerInvitationSerializer(invitation)
        return Response(out.data, status=200)
