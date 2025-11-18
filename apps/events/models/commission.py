"""
Modèles pour la gestion des commissions sur les événements
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from commons.models import AbstractCommonBaseModel
from apps.organizations.models import Organization


class EventCommissionOffer(AbstractCommonBaseModel):
    """
    Offre de commission créée par un organisateur standard pour son événement.
    Les super-vendeurs peuvent accepter cette offre pour vendre des tickets.
    """
    
    class OfferStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        PAUSED = 'PAUSED', 'En pause'
        EXPIRED = 'EXPIRED', 'Expirée'
        CANCELLED = 'CANCELLED', 'Annulée'
    
    event = models.OneToOneField(
        to='events.Event',
        on_delete=models.CASCADE,
        related_name='commission_offer',
        verbose_name='Événement',
        help_text="L'événement concerné par cette offre"
    )
    
    organization = models.ForeignKey(
        to='organizations.Organization',
        on_delete=models.CASCADE,
        related_name='commission_offers',
        verbose_name='Organisation',
        help_text="Organisation qui propose cette commission"
    )
    
    commission_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(10.00), MaxValueValidator(100.00)],
        verbose_name='Pourcentage de commission (%)',
        help_text='Commission offerte aux super-vendeurs (minimum 10%)'
    )
    
    status = models.CharField(
        max_length=20,
        choices=OfferStatus.choices,
        default=OfferStatus.ACTIVE,
        verbose_name='Statut de l\'offre'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Détails supplémentaires sur cette offre'
    )
    
    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Valide jusqu\'au',
        help_text='Date limite de validité de l\'offre'
    )
    
    total_accepted = models.IntegerField(
        default=0,
        verbose_name='Nombre d\'acceptations',
        help_text='Nombre de super-vendeurs ayant accepté'
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Métadonnées',
        help_text='Informations supplémentaires'
    )
    
    class Meta:
        verbose_name = 'Offre de Commission'
        verbose_name_plural = 'Offres de Commission'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event', 'status']),
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['status', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.event.name} - {self.commission_percentage}%"
    
    def clean(self):
        """Validation personnalisée"""
        super().clean()
        
        # Vérifier que l'organisation n'est pas un super-vendeur
        if self.organization.organization_type == 'SUPER_SELLER':
            raise ValidationError({
                'organization': 'Seules les organisations standard peuvent créer des offres de commission'
            })
        
        # Vérifier que le pourcentage est au minimum 10%
        if self.commission_percentage < 10:
            raise ValidationError({
                'commission_percentage': 'La commission minimale est de 10%'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class SuperSellerOfferAcceptance(AbstractCommonBaseModel):
    """
    Acceptation d'une offre de commission par un super-vendeur.
    Permet au super-vendeur de définir la sous-commission pour ses vendeurs.
    """
    
    class AcceptanceStatus(models.TextChoices):
        PENDING = 'PENDING', 'En attente'
        ACCEPTED = 'ACCEPTED', 'Acceptée'
        REJECTED = 'REJECTED', 'Rejetée'
        CANCELLED = 'CANCELLED', 'Annulée'
    
    offer = models.ForeignKey(
        to='EventCommissionOffer',
        on_delete=models.CASCADE,
        related_name='acceptances',
        verbose_name='Offre de commission'
    )
    
    super_seller = models.ForeignKey(
        to='organizations.Organization',
        on_delete=models.CASCADE,
        related_name='offer_acceptances',
        verbose_name='Super-Vendeur',
        help_text='Organisation super-vendeur acceptant l\'offre'
    )
    
    status = models.CharField(
        max_length=20,
        choices=AcceptanceStatus.choices,
        default=AcceptanceStatus.PENDING,
        verbose_name='Statut'
    )
    
    seller_commission_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0.00), MaxValueValidator(100.00)],
        verbose_name='Commission vendeur (%)',
        help_text='Pourcentage de commission offert aux vendeurs par le super-vendeur',
        null=True,
        blank=True
    )
    
    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Acceptée le'
    )
    
    rejected_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Rejetée le'
    )
    
    rejection_reason = models.TextField(
        blank=True,
        verbose_name='Raison du rejet'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='Notes'
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Métadonnées'
    )
    
    class Meta:
        verbose_name = 'Acceptation d\'Offre'
        verbose_name_plural = 'Acceptations d\'Offres'
        ordering = ['-timestamp']
        unique_together = [('offer', 'super_seller')]
        indexes = [
            models.Index(fields=['super_seller', 'status']),
            models.Index(fields=['offer', 'status']),
            models.Index(fields=['status', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.super_seller.name} - {self.offer.event.name}"
    
    def clean(self):
        """Validation personnalisée"""
        super().clean()
        
        # Vérifier que c'est bien un super-vendeur
        if self.super_seller.organization_type != 'SUPER_SELLER':
            raise ValidationError({
                'super_seller': 'Seules les organisations super-vendeur peuvent accepter des offres'
            })
        
        # Si accepté, la commission vendeur doit être définie
        if self.status == self.AcceptanceStatus.ACCEPTED and self.seller_commission_percentage is None:
            raise ValidationError({
                'seller_commission_percentage': 'Vous devez définir la commission pour vos vendeurs'
            })
        
        # La commission vendeur ne peut pas dépasser la commission de l'offre
        if self.seller_commission_percentage and self.seller_commission_percentage > self.offer.commission_percentage:
            raise ValidationError({
                'seller_commission_percentage': f'La commission vendeur ne peut pas dépasser {self.offer.commission_percentage}%'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        
        # Mettre à jour les timestamps
        if self.status == self.AcceptanceStatus.ACCEPTED and not self.accepted_at:
            from django.utils import timezone
            self.accepted_at = timezone.now()
            
            # Incrémenter le compteur d'acceptations
            self.offer.total_accepted += 1
            self.offer.save(update_fields=['total_accepted'])
        
        elif self.status == self.AcceptanceStatus.REJECTED and not self.rejected_at:
            from django.utils import timezone
            self.rejected_at = timezone.now()
        
        super().save(*args, **kwargs)