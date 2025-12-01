# -*- coding: utf-8 -*-
"""
Gestion des vendeurs affiliés aux super-vendeurs

@author: 

    Beaudelaire LAHOUME, alias root-lr
"""

import logging
from django.db import models
from django.core.exceptions import ValidationError
from commons.models import AbstractCommonBaseModel

logger = logging.getLogger(__name__)


class SellerStatus(models.TextChoices):
    """Statuts du vendeur"""
    INVITED = 'INVITED', 'Invité'
    ACTIVE = 'ACTIVE', 'Actif'
    SUSPENDED = 'SUSPENDED', 'Suspendu'
    INACTIVE = 'INACTIVE', 'Inactif'


class SellerKYCStatus(models.TextChoices):
    """Statuts KYC du vendeur (simplifié par rapport au super-vendeur)"""
    PENDING = 'PENDING', 'En attente'
    VERIFIED = 'VERIFIED', 'Vérifié'
    REJECTED = 'REJECTED', 'Rejeté'
    NOT_REQUIRED = 'NOT_REQUIRED', 'Non requis'


class Seller(AbstractCommonBaseModel):
    """
    Modèle représentant un vendeur affilié à un super-vendeur.
    Un vendeur est un membre d'organisation avec le rôle SELLER.
    
    Relations:
    - user: ForeignKey -> User (l'utilisateur vendeur)
    - organization_member: OneToOne -> OrganizationMember (membre avec rôle SELLER)
    - super_seller: ForeignKey -> Organization (organisation super-vendeur)
    """
    
    # Relations
    user = models.ForeignKey(
        to='users.User',
        on_delete=models.SET_NULL,
        related_name='seller_profiles',
        verbose_name="Utilisateur",
        help_text="L'utilisateur associé à ce vendeur",
        null=True
    )
    
    organization_member = models.OneToOneField(
        to='organizations.OrganizationMembership',
        on_delete=models.SET_NULL,
        related_name='seller_profile',
        verbose_name="Membre d'organisation",
        null=True,
        blank=True,
        help_text="Référence au membre d'organisation (rôle SELLER)"
    )
    
    super_seller = models.ForeignKey(
        to='organizations.Organization',
        on_delete=models.SET_NULL,
        related_name='sellers',
        verbose_name="Super-Vendeur",
        help_text="Organisation super-vendeur qui gère ce vendeur",
        null=True
    )
    
    # Statut du vendeur
    status = models.CharField(
        max_length=20,
        choices=SellerStatus.choices,
        default=SellerStatus.INVITED,
        verbose_name="Statut",
        db_index=True
    )
    
    # Statut KYC
    kyc_status = models.CharField(
        max_length=20,
        choices=SellerKYCStatus.choices,
        default=SellerKYCStatus.NOT_REQUIRED,
        verbose_name="Statut KYC",
        db_index=True
    )
    
    # Dates importantes
    invited_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date d'invitation"
    )
    
    activated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'activation"
    )
    
    suspended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de suspension"
    )
    
    suspension_reason = models.TextField(
        blank=True,
        verbose_name="Raison de la suspension"
    )
    
    # Informations de contact
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Numéro de téléphone"
    )
    
    whatsapp_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Numéro WhatsApp",
        help_text="Pour les notifications et communications"
    )
    
    # Informations de paiement (Mobile Money uniquement pour les vendeurs)
    mobile_money_provider = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Opérateur Mobile Money",
        help_text="Ex: MTN, Moov, Orange, Celtiis, etc."
    )
    
    mobile_money_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Numéro Mobile Money pour les paiements"
    )
    
    mobile_money_account_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Nom du compte Mobile Money"
    )
    
    # Informations commerciales
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name="Taux de commission (%)",
        help_text="Pourcentage de commission sur les ventes"
    )
    
    sales_target = models.IntegerField(
        default=0,
        verbose_name="Objectif de ventes",
        help_text="Nombre de tickets à vendre (objectif mensuel)"
    )
    
    # Zone géographique
    assigned_zone = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Zone assignée",
        help_text="Zone géographique ou secteur d'activité"
    )
    
    # Métadonnées
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
        help_text="Notes internes sur le vendeur"
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Métadonnées",
        help_text="Informations supplémentaires flexibles"
    )
    
    class Meta:
        verbose_name = "Vendeur"
        verbose_name_plural = "Vendeurs"
        ordering = ['-timestamp']
        unique_together = [['user', 'super_seller']]  
        indexes = [
            models.Index(fields=['super_seller', 'status']),
            models.Index(fields=['status', '-timestamp']),
            models.Index(fields=['user', 'super_seller']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} - Vendeur de {self.super_seller.name}"
    
    def clean(self):
        """Validation personnalisée"""
        super().clean()
        
        # Vérifier que le super_seller est bien une organisation SUPER_SELLER
        if self.super_seller and not hasattr(self.super_seller, 'super_seller_profile'):
            raise ValidationError({
                'super_seller': 'L\'organisation doit être de type Super-Vendeur'
            })
        
        # Vérifier que les informations de paiement sont complètes si fournies
        if self.mobile_money_number and not self.mobile_money_provider:
            raise ValidationError({
                'mobile_money_provider': 'Le fournisseur Mobile Money est requis'
            })
    
    def save(self, *args, **kwargs):
        """Override save pour gérer les dates de statut"""
        from django.utils import timezone
        
        # Si le statut passe à ACTIVE et activated_at n'est pas défini
        if self.status == SellerStatus.ACTIVE and not self.activated_at:
            self.activated_at = timezone.now()
        
        # Si le statut passe à SUSPENDED
        if self.status == SellerStatus.SUSPENDED and not self.suspended_at:
            self.suspended_at = timezone.now()
        
        # Réinitialiser suspended_at si le statut n'est plus SUSPENDED
        if self.status != SellerStatus.SUSPENDED:
            self.suspended_at = None
        
        super().save(*args, **kwargs)
    
    # Méthodes utilitaires
    def is_active(self):
        """Vérifie si le vendeur est actif"""
        return self.status == SellerStatus.ACTIVE and self.active

    
    def has_payment_method_configured(self):
        """Vérifie si la méthode de paiement est configurée"""
        return bool(self.mobile_money_number and self.mobile_money_provider)
    
    def activate(self):
        """Active le vendeur"""
        self.status = SellerStatus.ACTIVE
        self.save()
    
    def suspend(self, reason=""):
        """Suspend le vendeur"""
        self.status = SellerStatus.SUSPENDED
        self.suspension_reason = reason
        self.save()
    
    def get_payment_info(self):
        """Retourne les informations de paiement du vendeur"""
        return {
            'provider': self.mobile_money_provider,
            'number': self.mobile_money_number,
            'account_name': self.mobile_money_account_name
        }
    
    def get_statistics(self):
        """
        Retourne les statistiques de vente du vendeur.
        À implémenter avec les ventes réelles plus tard.
        """
        from apps.events.models import ETicket
        
        # Compter les tickets vendus par ce vendeur
        sold_tickets = ETicket.objects.filter(
            seller=self,
            related_order__status='paid'  
        ).count()
        
        return {
            'total_sales': sold_tickets,
            'total_amount': 0,  
            'commission_earned': 0, 
        }