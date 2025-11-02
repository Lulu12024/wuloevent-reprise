# -*- coding: utf-8 -*-
"""
Created on October 29, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""


import logging
from django.db import models
from django.core.exceptions import ValidationError
from commons.models import AbstractCommonBaseModel
from django.utils import timezone
from django.conf import settings
import secrets

logger = logging.getLogger(__name__)

class InvitationStatus(models.TextChoices):
    PENDING = "PENDING", "En attente"
    ACCEPTED = "ACCEPTED", "Acceptée"
    DECLINED = "DECLINED", "Refusée"
    EXPIRED = "EXPIRED", "Expirée"
    CANCELED = "CANCELED", "Annulée"

class InvitationChannel(models.TextChoices):
    EMAIL = "EMAIL", "Email"
    SMS = "SMS", "SMS"
    WHATSAPP = "WHATSAPP", "WhatsApp"


class SellerInvitation(models.Model):
    super_seller = models.ForeignKey(
        to='organizations.Organization', on_delete=models.CASCADE, related_name='seller_invitations'
    )
    invited_by = models.ForeignKey(
        to='users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_seller_invitations'
    )
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    channel = models.CharField(max_length=10, choices=InvitationChannel.choices, default=InvitationChannel.EMAIL)
    token = models.CharField(max_length=64, unique=True, db_index=True)

    status = models.CharField(max_length=12, choices=InvitationStatus.choices, default=InvitationStatus.PENDING, db_index=True)
    message = models.TextField(blank=True)

    expires_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)

    invited_user = models.ForeignKey('users.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='seller_invites_received')
    seller = models.ForeignKey('events.Seller', null=True, blank=True, on_delete=models.SET_NULL, related_name='origin_invitations')

    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['super_seller', 'status']),
            models.Index(fields=['email', 'phone']),
            models.Index(fields=['expires_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=(models.Q(email__gt='') | models.Q(phone__gt='')),
                name='seller_invitation_contact_required',
            ),
        ]

    def __str__(self):
        target = self.email or self.phone
        return f"Invitation {self.token} → {target} ({self.status})"

    def clean(self):
        if not (self.email or self.phone):
            raise ValidationError("Email ou téléphone requis")
        if self.super_seller and not self.super_seller.is_super_seller():
            raise ValidationError({'super_seller': "L'organisation doit être de type Super‑Vendeur"})

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(48)[:64]
        if not self.expires_at:
            days = getattr(settings, 'SELLER_INVITATION_EXPIRY_DAYS', 7)
            self.expires_at = timezone.now() + timezone.timedelta(days=days)
            return super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at or self.status == InvitationStatus.EXPIRED

    def mark_expired(self, persist=True):
        if self.status == InvitationStatus.PENDING:
            self.status = InvitationStatus.EXPIRED
        if persist:
            self.save(update_fields=['status'])