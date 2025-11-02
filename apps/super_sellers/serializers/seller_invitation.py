# -*- coding: utf-8 -*-
"""
Created on 31/10/2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""


from rest_framework import serializers
from django.utils import timezone
from apps.super_sellers.models import SellerInvitation, InvitationChannel, InvitationStatus
from apps.users.models import User
from apps.organizations.models import Organization
from apps.events.models.seller import Seller, SellerStatus
from apps.organizations.models import OrganizationMembership
from apps.users.models import AppRole

class SellerInvitationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerInvitation
        fields = ['email', 'phone', 'channel', 'message']

    def validate(self, attrs):
        if not attrs.get('email') and not attrs.get('phone'):
            raise serializers.ValidationError('Email ou téléphone requis')
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        super_seller: Organization = self.context['organization']
        return SellerInvitation.objects.create(
            super_seller=super_seller,
            invited_by=request.user,
            **validated_data
        )

class SellerInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerInvitation
        fields = [
            'token', 
            'status', 
            'email', 
            'phone', 
            'channel', 
            'message',
            'expires_at', 
            'sent_at', 
            'delivered_at', 
            'accepted_at', 
            'declined_at'
        ]

class SellerInvitationRespondSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['accept', 'decline'])
    user_email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)

    def validate(self, attrs):
        return attrs

    def save(self, **kwargs):
        invitation: SellerInvitation = self.context['invitation']
        action = self.validated_data['action']
        now = timezone.now()

        if invitation.is_expired:
            invitation.mark_expired()
            raise serializers.ValidationError("Invitation expirée.")
        if invitation.status != InvitationStatus.PENDING:
            raise serializers.ValidationError("Invitation déjà traitée.")

        if action == 'decline':
            invitation.status = InvitationStatus.DECLINED
            invitation.declined_at = now
            invitation.save(update_fields=['status', 'declined_at'])
            return invitation

        # accept
        email = invitation.email or self.validated_data.get('user_email')
        phone = invitation.phone or self.validated_data.get('phone')

        user = None
        if email:
            user = User.objects.filter(email=email).first()
        if not user and phone:
            user = User.objects.filter(phone=phone).first()
        if not user:
            user = User.objects.create(
                first_name="", last_name="", email=email, phone=phone,
                admin_id=f"seller_{invitation.token[:10]}",
                conf_num="", password="!", have_validate_account=False,
            )

        # membership
        super_seller = invitation.super_seller
        membership, _ = OrganizationMembership.objects.get_or_create(
            organization=super_seller, user=user
        )
        # rôle SELLER si tu le gères via AppRole
        seller_role = AppRole.objects.filter(name__iexact="SELLER").first()
        if seller_role:
            membership.roles.add(seller_role)

        # profil seller
        seller, created = Seller.objects.get_or_create(
            user=user, super_seller=super_seller,
            defaults={"status": SellerStatus.ACTIVE}
        )
        if not created and seller.status != SellerStatus.ACTIVE:
            seller.activate()

        invitation.invited_user = user
        invitation.seller = seller
        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = now
        invitation.save(update_fields=['invited_user', 'seller', 'status', 'accepted_at'])
        return invitation

