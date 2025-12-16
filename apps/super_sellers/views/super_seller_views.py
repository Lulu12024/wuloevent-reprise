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
import logging

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
from apps.super_sellers.services.invitations import (
    send_invitation_email, 
    send_invitation_sms, 
    send_invitation_whatsapp
)

logger = logging.getLogger(__name__)


class InviteSellerAPIView(APIView):
    """
    POST /api/super-sellers/sellers/invite
    
    Invite un vendeur par Email (avec boutons) ou WhatsApp.
    """
    permission_classes = [permissions.IsAuthenticated, IsVerifiedSuperSellerAndMember]

    @extend_schema(
        summary="Inviter un vendeur",
        description=(
            "Invite un vendeur (email/WhatsApp) pour rejoindre l'organisation Super-Vendeur.\n\n"
            "**Email :** Contient des boutons cliquables 'Accepter' et 'Décliner'\n"
            "**WhatsApp :** Message formaté avec lien d'invitation\n\n"
            "- Requiert: Auth + membre de l'orga + orga KYC VERIFIED\n"
        ),
        request=SellerInvitationCreateSerializer,
        responses={
            201: SellerInvitationSerializer, 
            400: OpenApiTypes.OBJECT, 
            403: OpenApiTypes.OBJECT
        },
        examples=[
            OpenApiExample(
                'Invitation par Email',
                value={
                    "organization_id": "uuid-org", 
                    "email": "vendeur@example.com", 
                    "channel": "EMAIL",
                    "message": "Rejoignez notre équipe !"
                },
                request_only=True
            ),
            OpenApiExample(
                'Invitation par WhatsApp',
                value={
                    "organization_id": "uuid-org", 
                    "phone": "22997123456", 
                    "channel": "WHATSAPP",
                    "message": "Bienvenue dans notre équipe de vendeurs !"
                },
                request_only=True
            ),
            OpenApiExample(
                'Réponse succès',
                value={
                    "token": "abcd1234...",
                    "status": "PENDING",
                    "channel": "EMAIL",
                    "email": "vendeur@example.com",
                    "expires_at": "2025-12-09T12:00:00Z",
                    "sent_at": "2025-12-02T10:30:00Z",
                    "invitation_sent": True
                },
                response_only=True
            ),
        ],
        tags=['Super-Vendeurs - Invitations']
    )
    def post(self, request, *args, **kwargs):
        """
        Crée et envoie une invitation vendeur.
        """
        org_id = request.data.get("organization_id")
        self.organization = get_object_or_404(Organization, pk=org_id)

        # Vérifier les permissions
        self.check_permissions(request)

        # Valider et créer l'invitation
        serializer = SellerInvitationCreateSerializer(
            data=request.data, 
            context={"request": request, "organization": self.organization}
        )
        serializer.is_valid(raise_exception=True)
        invitation = serializer.save()
        
        logger.info(
            f"Invitation créée: {invitation.id} | "
            f"Canal: {invitation.channel} | "
            f"Destinataire: {invitation.email or invitation.phone}"
        )

        # ============================================================
        # ENVOYER L'INVITATION via le canal choisi
        # ============================================================
        invitation_sent = False
        send_result = None
        
        try:
            if invitation.channel == InvitationChannel.WHATSAPP and invitation.phone:
                logger.info(f"📱 Envoi WhatsApp à {invitation.phone}...")
                send_result = send_invitation_whatsapp(invitation)
                invitation_sent = send_result.get('success', False)
                
                if invitation_sent:
                    logger.info(
                        f"✅ WhatsApp envoyé avec succès | "
                        f"MessageID: {send_result.get('message_id')}"
                    )
                else:
                    logger.error(
                        f"❌ Échec envoi WhatsApp | "
                        f"Erreur: {send_result.get('error')}"
                    )
                    
            elif invitation.channel == InvitationChannel.EMAIL and invitation.email:
                logger.info(f"📧 Envoi Email à {invitation.email}...")
                invitation_sent = send_invitation_email(invitation)
                
                if invitation_sent:
                    logger.info(f"✅ Email envoyé avec succès avec boutons Accepter/Décliner")
                else:
                    logger.error(f"❌ Échec envoi Email")
                    
            elif invitation.channel == InvitationChannel.SMS and invitation.phone:
                logger.info(f"📲 Envoi SMS à {invitation.phone}...")
                send_result = send_invitation_sms(invitation)
                invitation_sent = send_result.get('success', False)
                
                if not invitation_sent:
                    logger.warning(f"⚠️ SMS pas encore implémenté")
                    
            else:
                logger.warning(
                    f"⚠️ Canal ou destinataire invalide | "
                    f"Canal: {invitation.channel} | "
                    f"Email: {invitation.email} | "
                    f"Phone: {invitation.phone}"
                )
                
        except Exception as e:
            logger.exception(f"❌ Erreur inattendue lors de l'envoi: {e}")
            invitation_sent = False
        
        # ============================================================
        # PRÉPARER LA RÉPONSE
        # ============================================================
        
        # Sérialiser l'invitation
        out = SellerInvitationSerializer(invitation)
        response_data = out.data
        
        # Ajouter info sur l'envoi
        response_data['invitation_sent'] = invitation_sent
        
        if send_result:
            response_data['send_details'] = {
                'success': send_result.get('success'),
                'message_id': send_result.get('message_id'),
                'error': send_result.get('error')
            }
        
        # Message informatif
        if invitation_sent:
            response_data['message'] = (
                f"Invitation créée et envoyée par {invitation.channel} avec succès ! ✅"
            )
        else:
            response_data['message'] = (
                f"Invitation créée mais l'envoi par {invitation.channel} a échoué. "
                f"Vous pouvez la renvoyer manuellement."
            )
        
        return Response(response_data, status=status.HTTP_201_CREATED)


class SellerInvitationRespondAPIView(APIView):
    """
    POST /api/super-sellers/sellers/invitations/{token}/respond
    
    Accepter ou décliner une invitation vendeur.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Répondre à une invitation vendeur",
        description=(
            "Accepter ou refuser l'invitation via le token reçu par email/SMS/WhatsApp.\n\n"
            "**Actions possibles :**\n"
            "- `accept` : Accepter l'invitation et créer le compte vendeur\n"
            "- `decline` : Décliner l'invitation\n"
        ),
        request=SellerInvitationRespondSerializer,
        responses={
            200: SellerInvitationSerializer, 
            400: OpenApiTypes.OBJECT, 
            404: OpenApiTypes.OBJECT
        },
        examples=[
            OpenApiExample(
                'Accepter l\'invitation', 
                value={"action": "accept"}, 
                request_only=True
            ),
            OpenApiExample(
                'Refuser l\'invitation', 
                value={"action": "decline"}, 
                request_only=True
            ),
            OpenApiExample(
                'Réponse succès',
                value={
                    "token": "abcd1234...",
                    "status": "ACCEPTED",
                    "accepted_at": "2025-12-02T11:00:00Z",
                    "message": "Invitation acceptée avec succès !"
                },
                response_only=True
            ),
        ],
        tags=['Super-Vendeurs - Invitations']
    )
    def post(self, request, token, *args, **kwargs):
        """
        Accepte ou décline une invitation.
        """
        invitation = get_object_or_404(SellerInvitation, token=token)
        
        logger.info(
            f"Tentative de réponse à l'invitation {invitation.id} | "
            f"Action: {request.data.get('action')}"
        )
        
        serializer = SellerInvitationRespondSerializer(
            data=request.data, 
            context={"invitation": invitation}
        )
        serializer.is_valid(raise_exception=True)
        invitation = serializer.save()
        
        # Logger le résultat
        action = request.data.get('action')
        if action == 'accept':
            logger.info(f"✅ Invitation {invitation.id} acceptée")
        elif action == 'decline':
            logger.info(f"❌ Invitation {invitation.id} déclinée")
        
        out = SellerInvitationSerializer(invitation)
        response_data = out.data
        
        # Ajouter message informatif
        if invitation.status == 'ACCEPTED':
            response_data['message'] = "Invitation acceptée avec succès ! Bienvenue dans l'équipe. 🎉"
        elif invitation.status == 'DECLINED':
            response_data['message'] = "Invitation déclinée."
        
        return Response(response_data, status=200)