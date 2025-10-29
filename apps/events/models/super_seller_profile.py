# -*- coding: utf-8 -*-
"""
Gestion des organisations de type super-vendeur avec KYC

@author: 
    Beaudelaire LAHOUME, alias root-lr
"""

import logging
from django.db import models
from django.core.validators import FileExtensionValidator
from commons.models import AbstractCommonBaseModel

logger = logging.getLogger(__name__)


class OrganizationType(models.TextChoices):
    """Types d'organisations"""
    STANDARD = 'STANDARD', 'Organisation Standard'
    SUPER_SELLER = 'SUPER_SELLER', 'Super-Vendeur'


class KYCStatus(models.TextChoices):
    """Statuts de vérification KYC"""
    PENDING = 'PENDING', 'En attente'
    VERIFIED = 'VERIFIED', 'Vérifié'
    REJECTED = 'REJECTED', 'Rejeté'


class PaymentMethod(models.TextChoices):
    """Méthodes de paiement disponibles"""
    MOBILE_MONEY = 'MOBILE_MONEY', 'Mobile Money'
    BANK_TRANSFER = 'BANK_TRANSFER', 'Virement Bancaire'


class SuperSellerProfile(AbstractCommonBaseModel):
    """
    Profil étendu pour les organisations de type Super-Vendeur.
    Contient les informations KYC et de paiement.
    
    Relations:
    - organization: OneToOne -> Organization (super-vendeur)
    - kyc_verified_by: ForeignKey -> User (administrateur qui a vérifié)
    """
    
    # Relation avec l'organisation
    organization = models.OneToOneField(
        to='organizations.Organization',
        on_delete=models.CASCADE,
        related_name='super_seller_profile',
        verbose_name="Organisation Super-Vendeur"
    )
    
    # Statut KYC
    kyc_status = models.CharField(
        max_length=20,
        choices=KYCStatus.choices,
        default=KYCStatus.PENDING,
        verbose_name="Statut KYC",
        db_index=True
    )
    
    kyc_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de vérification KYC"
    )
    
    kyc_verified_by = models.ForeignKey(
        to='users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_super_sellers',
        verbose_name="Vérifié par"
    )
    
    kyc_rejection_reason = models.TextField(
        blank=True,
        verbose_name="Raison du rejet KYC"
    )
    
    # Documents de vérification KYC
    identity_document = models.FileField(
        upload_to='kyc/super_sellers/identity/%Y/%m/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        verbose_name="Document d'identité"
    )
    
    business_registration = models.FileField(
        upload_to='kyc/super_sellers/business/%Y/%m/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        verbose_name="Enregistrement commercial"
    )
    
    proof_of_address = models.FileField(
        upload_to='kyc/super_sellers/address/%Y/%m/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        verbose_name="Justificatif de domicile"
    )
    
    additional_documents = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Documents additionnels",
        help_text="Liste d'URLs ou chemins vers documents supplémentaires"
    )
    
    # Informations de paiement - Mobile Money
    mobile_money_provider = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Opérateur Mobile Money",
        help_text="Ex: MTN, Moov, Orange, Celtiis, etc."
    )
    
    mobile_money_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Numéro Mobile Money"
    )
    
    mobile_money_account_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Nom du compte Mobile Money"
    )
    
    # Informations de paiement - Compte Bancaire
    bank_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Nom de la banque"
    )
    
    bank_account_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Numéro de compte bancaire"
    )
    
    bank_account_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Nom du titulaire du compte"
    )
    
    bank_swift_code = models.CharField(
        max_length=11,
        blank=True,
        verbose_name="Code SWIFT/BIC",
        help_text="Pour les virements internationaux"
    )
    
    bank_iban = models.CharField(
        max_length=34,
        blank=True,
        verbose_name="IBAN",
        help_text="Si applicable"
    )
    
    # Méthode de paiement préférée
    preferred_payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.MOBILE_MONEY,
        verbose_name="Méthode de paiement préférée"
    )
    
    # Métadonnées
    notes = models.TextField(
        blank=True,
        verbose_name="Notes internes",
        help_text="Notes pour l'équipe administrative"
    )
    
    class Meta:
        verbose_name = "Profil Super-Vendeur"
        verbose_name_plural = "Profils Super-Vendeurs"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['kyc_status', '-timestamp']),
            models.Index(fields=['organization', 'kyc_status']),
        ]
    
    def __str__(self):
        return f"Super-Vendeur: {self.organization.name} ({self.get_kyc_status_display()})"
    
    def is_kyc_verified(self):
        """Vérifie si le KYC est validé"""
        return self.kyc_status == KYCStatus.VERIFIED
    
    def can_operate(self):
        """Vérifie si le super-vendeur peut opérer (créer événements, gérer vendeurs)"""
        return self.active and self.is_kyc_verified()
    
    def has_payment_method_configured(self):
        """Vérifie si au moins une méthode de paiement est configurée"""
        has_mobile_money = bool(self.mobile_money_number and self.mobile_money_provider)
        has_bank = bool(self.bank_account_number and self.bank_name)
        return has_mobile_money or has_bank
    
    def get_payment_info(self):
        """Retourne les informations de paiement selon la méthode préférée"""
        if self.preferred_payment_method == PaymentMethod.MOBILE_MONEY:
            return {
                'method': 'mobile_money',
                'provider': self.mobile_money_provider,
                'number': self.mobile_money_number,
                'account_name': self.mobile_money_account_name
            }
        else:
            return {
                'method': 'bank_transfer',
                'bank_name': self.bank_name,
                'account_number': self.bank_account_number,
                'account_name': self.bank_account_name,
                'swift': self.bank_swift_code,
                'iban': self.bank_iban
            }
    
    def save(self, *args, **kwargs):
        """Override save pour mettre à jour la date de vérification"""
        if self.kyc_status == KYCStatus.VERIFIED and not self.kyc_verified_at:
            from django.utils import timezone
            self.kyc_verified_at = timezone.now()
        super().save(*args, **kwargs)