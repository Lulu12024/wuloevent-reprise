# -*- coding: utf-8 -*-
"""

Gestion des stocks de tickets pour les vendeurs

@author: 
    Beaudelaire LAHOUME, alias root-lr
"""

import logging
from django.db import models
from django.core.exceptions import ValidationError
from commons.models import AbstractCommonBaseModel

logger = logging.getLogger(__name__)


class StockTransactionType(models.TextChoices):
    """Types de transactions de stock"""
    ALLOCATION = 'ALLOCATION', 'Attribution de stock'
    SALE = 'SALE', 'Vente'
    RETURN = 'RETURN', 'Retour de stock'
    ADJUSTMENT = 'ADJUSTMENT', 'Ajustement'


class TicketStock(AbstractCommonBaseModel):
    """
    Gestion des stocks de tickets pour les vendeurs.
   
    """
    
    # Relations
    seller = models.ForeignKey(
        to='events.Seller',
        on_delete=models.CASCADE,
        related_name='ticket_stocks',
        verbose_name="Vendeur",
        help_text="Vendeur possédant ce stock"
    )
    
    event = models.ForeignKey(
        to='events.Event',
        on_delete=models.CASCADE,
        related_name='seller_stocks',
        verbose_name="Événement",
        help_text="Événement concerné"
    )
    
    ticket = models.ForeignKey(
        to='events.Ticket',
        on_delete=models.CASCADE,
        related_name='seller_stocks',
        verbose_name="Type de ticket",
        help_text="Catégorie de ticket"
    )
    
    # Quantités
    total_allocated = models.IntegerField(
        default=0,
        verbose_name="Quantité totale allouée",
        help_text="Nombre total de tickets attribués au vendeur"
    )
    
    total_sold = models.IntegerField(
        default=0,
        verbose_name="Quantité vendue",
        help_text="Nombre de tickets déjà vendus"
    )
    
    # Prix et commissions
    authorized_sale_price = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        verbose_name="Prix de vente autorisé",
        help_text="Prix auquel le vendeur peut vendre le ticket"
    )
    
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name="Taux de commission (%)",
        help_text="Commission du vendeur sur chaque vente"
    )
    
    # Dates
    allocated_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date d'attribution"
    )
    
    last_sale_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Dernière vente",
        help_text="Date et heure de la dernière vente"
    )
    
    # Métadonnées
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
        help_text="Notes sur ce stock"
    )
    
    class Meta:
        verbose_name = "Stock de Tickets"
        verbose_name_plural = "Stocks de Tickets"
        ordering = ['-allocated_at']
        unique_together = [['seller', 'event', 'ticket']]  
        indexes = [
            models.Index(fields=['seller', 'event']),
            models.Index(fields=['event', '-allocated_at']),
            models.Index(fields=['seller', '-allocated_at']),
        ]
    
    def __str__(self):
        return f"Stock: {self.seller.user.get_full_name()} - {self.event.name} ({self.available_quantity} disponibles)"
    
    @property
    def available_quantity(self):
        """Calcule la quantité disponible"""
        return self.total_allocated - self.total_sold
    
    @property
    def is_available(self):
        """Vérifie si du stock est disponible"""
        return self.available_quantity > 0
    
    @property
    def stock_percentage_sold(self):
        """Calcule le pourcentage de stock vendu"""
        if self.total_allocated == 0:
            return 0
        return (self.total_sold / self.total_allocated) * 100
    
    def clean(self):
        """Validations personnalisées"""
        super().clean()
        
        # Vérifier que total_sold ne dépasse pas total_allocated
        if self.total_sold > self.total_allocated:
            raise ValidationError({
                'total_sold': 'La quantité vendue ne peut pas dépasser la quantité allouée'
            })
        
        # Vérifier que le vendeur peut vendre
        if self.seller and not self.seller.can_sell():
            raise ValidationError({
                'seller': 'Ce vendeur ne peut pas recevoir de stock (inactif ou super-vendeur non vérifié)'
            })
        
        # Vérifier que le ticket appartient bien à l'événement
        if self.ticket and self.event and self.ticket.event != self.event:
            raise ValidationError({
                'ticket': 'Ce ticket n\'appartient pas à l\'événement sélectionné'
            })
    
    def can_sell(self, quantity=1):
        """Vérifie si on peut vendre une quantité donnée"""
        return self.is_available and self.available_quantity >= quantity
    
    def record_sale(self, quantity=1):
        """
        Enregistre une vente et met à jour le stock.
        Retourne True si succès, False si stock insuffisant.
        """
        if not self.can_sell(quantity):
            logger.warning(f"Stock insuffisant pour vente: {self} - Demandé: {quantity}, Disponible: {self.available_quantity}")
            return False
        
        from django.utils import timezone
        self.total_sold += quantity
        self.last_sale_at = timezone.now()
        self.save()
        
        logger.info(f"Vente enregistrée: {quantity} tickets - {self}")
        return True
    
    def add_stock(self, quantity):
        """Ajoute du stock"""
        self.total_allocated += quantity
        self.save()
        logger.info(f"Stock ajouté: +{quantity} tickets - {self}")
    
    def remove_stock(self, quantity):
        """Retire du stock (ajustement)"""
        if quantity > self.available_quantity:
            raise ValidationError("Impossible de retirer plus que le stock disponible")
        self.total_allocated -= quantity
        self.save()
        logger.info(f"Stock retiré: -{quantity} tickets - {self}")


class StockTransaction(AbstractCommonBaseModel):
    """
    Historique de toutes les transactions de stock.
    Permet de tracer tous les mouvements de tickets.
    
    Relations:
    - ticket_stock: ForeignKey -> TicketStock (stock concerné)
    - initiated_by: ForeignKey -> User (qui a initié la transaction)
    - related_order: ForeignKey -> Order (commande associée si vente)
    """
    
    # Relations
    ticket_stock = models.ForeignKey(
        to=TicketStock,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name="Stock de tickets",
        help_text="Stock concerné par cette transaction"
    )
    
    transaction_type = models.CharField(
        max_length=20,
        choices=StockTransactionType.choices,
        verbose_name="Type de transaction",
        db_index=True
    )
    
    quantity = models.IntegerField(
        verbose_name="Quantité",
        help_text="Nombre de tickets concernés (positif ou négatif)"
    )
    
    # Avant/Après pour traçabilité
    quantity_before = models.IntegerField(
        verbose_name="Quantité avant",
        help_text="Quantité disponible avant la transaction"
    )
    
    quantity_after = models.IntegerField(
        verbose_name="Quantité après",
        help_text="Quantité disponible après la transaction"
    )
    
    # Relations supplémentaires
    initiated_by = models.ForeignKey(
        to='users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='initiated_stock_transactions',
        verbose_name="Initié par",
        help_text="Utilisateur qui a initié cette transaction"
    )
    
    related_order = models.ForeignKey(
        to='events.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_transactions',
        verbose_name="Commande associée",
        help_text="Commande liée (si transaction de vente)"
    )
    
   
    sale_price = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Prix de vente",
        help_text="Prix unitaire de vente (si transaction de vente)"
    )
    
    commission_amount = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Montant de commission",
        help_text="Commission gagnée (si transaction de vente)"
    )
    
    # Métadonnées
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
        help_text="Détails ou raison de la transaction"
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Métadonnées",
        help_text="Informations supplémentaires"
    )
    
    class Meta:
        verbose_name = "Transaction de Stock"
        verbose_name_plural = "Transactions de Stock"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['ticket_stock', '-timestamp']),
            models.Index(fields=['transaction_type', '-timestamp']),
            models.Index(fields=['initiated_by', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.quantity} tickets - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    @classmethod
    def create_allocation_transaction(cls, ticket_stock, quantity, initiated_by, notes=""):
        """Crée une transaction d'allocation de stock"""
        return cls.objects.create(
            ticket_stock=ticket_stock,
            transaction_type=StockTransactionType.ALLOCATION,
            quantity=quantity,
            quantity_before=ticket_stock.available_quantity,
            quantity_after=ticket_stock.available_quantity + quantity,
            initiated_by=initiated_by,
            notes=notes
        )
    
    @classmethod
    def create_sale_transaction(cls, ticket_stock, quantity, initiated_by, order, sale_price, commission_rate, notes=""):
        """Crée une transaction de vente"""
        commission_amount = (sale_price * quantity * commission_rate) / 100
        
        return cls.objects.create(
            ticket_stock=ticket_stock,
            transaction_type=StockTransactionType.SALE,
            quantity=-quantity,     
            quantity_before=ticket_stock.available_quantity,
            quantity_after=ticket_stock.available_quantity - quantity,
            initiated_by=initiated_by,
            related_order=order,
            sale_price=sale_price,
            commission_amount=commission_amount,
            notes=notes
        )
    
    @classmethod
    def create_return_transaction(cls, ticket_stock, quantity, initiated_by, notes=""):
        """Crée une transaction de retour de stock"""
        return cls.objects.create(
            ticket_stock=ticket_stock,
            transaction_type=StockTransactionType.RETURN,
            quantity=quantity,
            quantity_before=ticket_stock.available_quantity,
            quantity_after=ticket_stock.available_quantity + quantity,
            initiated_by=initiated_by,
            notes=notes
        )
    
    @classmethod
    def create_adjustment_transaction(cls, ticket_stock, quantity, initiated_by, notes=""):
        """Crée une transaction d'ajustement"""
        return cls.objects.create(
            ticket_stock=ticket_stock,
            transaction_type=StockTransactionType.ADJUSTMENT,
            quantity=quantity,
            quantity_before=ticket_stock.available_quantity,
            quantity_after=ticket_stock.available_quantity + quantity,
            initiated_by=initiated_by,
            notes=notes
        )