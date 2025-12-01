# -*- coding: utf-8 -*-
"""
Created on April 26, 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.contrib import admin

# Register your models here.
from apps.events.models import EventType, Event, EventImage, FavouriteEvent, TicketCategoryFeature, TicketCategory, \
    Ticket, Order, OrderItem, ETicket, EventHighlightingType, EventHighlighting
from apps.notifications.tasks import notifications_tasks
from apps.xlib.enums import OrderStatusEnum
from commons.admin import BaseModelAdmin


@admin.register(EventType)
class EventTypeAdmin(BaseModelAdmin):
    pass


@admin.register(Event)
# class EventAdmin(BaseModelAdmin):
#     search_fields = ['name', 'ephemeral_access_code', 'name', 'pk', 'description', 'location_name']
#     list_filter = ('is_ephemeral', 'valid', 'have_passed_validation','organization', 'organization__owner')
#     ordering = ('-timestamp', 'name')
class EventAdmin(BaseModelAdmin):
    """
    Admin pour les événements avec support des événements éphémères.
    """
    
    # ========== LIST DISPLAY ==========
    list_display = [
        'name',
        'event_type_badge',           
        'organization',
        'date',
        'hour',
        'is_ephemeral_badge',         
        'ephemeral_access_code_display', 
        'valid',
        'have_passed_validation',
        'views',
        'participant_count',
    ]
    
    # ========== LIST FILTER ==========
    list_filter = [
        'is_ephemeral',              
        'organization',
        'organization__owner',
        'organization__organization_type',  
        'valid',
        'have_passed_validation',
        'type',
        'date',
    ]
    
    # ========== SEARCH FIELDS ==========
    search_fields = [
        'name',
        'pk',
        'description',
        'location_name',
        'ephemeral_access_code',     
    ]
    
    # ========== ORDERING ==========
    ordering = ('-timestamp', 'name')
    
    # ========== READONLY FIELDS ==========
    readonly_fields = [
        'ephemeral_access_code',     
        'views',
        'participant_count',
        'timestamp',
        'updated',
    ]
    
    # ========== FIELDSETS ==========
    fieldsets = (
        ('Informations de base', {
            'fields': (
                'name',
                'description',
                'type',
                'organization',
                'publisher',
            )
        }),
        ('Détails de l\'événement', {
            'fields': (
                'date',
                'hour',
                'expiry_date',
                'default_price',
                'cover_image',
                'participant_limit',
                'participant_count',
                'views',
            )
        }),
        ('Localisation', {
            'fields': (
                'location_name',
                'location_lat',
                'location_long',
                'country',
            )
        }),
        # ========== FIELDSET : Événement Éphémère ==========
        ('Événement Éphémère', {
            'fields': (
                'is_ephemeral',
                'created_by_super_seller',
                'ephemeral_access_code',
            ),
            'classes': ('collapse',),  # Replié par défaut
            'description': (
                '<strong>⚠️ ÉVÉNEMENTS ÉPHÉMÈRES</strong><br>'
                'Les événements éphémères ne sont pas listés publiquement. '
                'Ils sont accessibles uniquement via leur code d\'accès unique. '
                'Seuls les super-vendeurs vérifiés peuvent créer des événements éphémères.'
            ),
        }),
        # ========== FIN FIELDSET ==========
        ('Statut et visibilité', {
            'fields': (
                'valid',
                'have_passed_validation',
                'active',
                'private',
            )
        }),
        ('Métadonnées', {
            'fields': (
                'timestamp',
                'updated',
            ),
            'classes': ('collapse',),
        }),
    )

    actions = ['validate_events', 'generate_ephemeral_codes']
    
    @admin.action(description="✅ Valider les événements sélectionnés")
    def validate_events(self, request, queryset):
        """Action pour valider plusieurs événements"""
        updated = queryset.update(valid=True, have_passed_validation=True)
        self.message_user(request, f"{updated} événement(s) validé(s) avec succès.")
    
    @admin.action(description="🔑 Générer les codes d'accès pour événements éphémères")
    def generate_ephemeral_codes(self, request, queryset):
        """
        Action pour générer les codes d'accès pour les événements éphémères
        qui n'en ont pas encore.
        """
        ephemeral_events = queryset.filter(is_ephemeral=True, ephemeral_access_code='')
        count = 0
        for event in ephemeral_events:
            event.generate_ephemeral_access_code()
            count += 1
        
        self.message_user(
            request,
            f"{count} code(s) d'accès généré(s) pour les événements éphémères."
        )
    
    # ========== MÉTHODES PERSONNALISÉES POUR L'AFFICHAGE ==========
    
    def event_type_badge(self, obj):
        """
        Affiche un badge coloré selon que l'événement est public ou privé.
        """
        if obj.private:
            color = '#6c757d'  # Gris
            icon = '🔒'
            label = 'Privé'
        else:
            color = '#28a745'  # Vert
            icon = '🌐'
            label = 'Public'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{} {}</span>',
            color, icon, label
        )
    event_type_badge.short_description = 'Type'
    event_type_badge.admin_order_field = 'private'
    
    def is_ephemeral_badge(self, obj):
        """
        Affiche un badge si l'événement est éphémère.
        """
        if obj.is_ephemeral:
            return format_html(
                '<span style="background-color: #9c27b0; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">👻 ÉPHÉMÈRE</span>'
            )
        return format_html(
            '<span style="color: #999; font-size: 11px;">—</span>'
        )
    is_ephemeral_badge.short_description = 'Éphémère'
    is_ephemeral_badge.admin_order_field = 'is_ephemeral'
    
    def ephemeral_access_code_display(self, obj):
        """
        Affiche le code d'accès pour les événements éphémères avec un bouton copier.
        """
        if obj.is_ephemeral and obj.ephemeral_access_code:
            return format_html(
                '<code style="background-color: #f5f5f5; padding: 4px 8px; '
                'border-radius: 3px; font-family: monospace; font-size: 12px;">{}</code> '
                '<button type="button" onclick="navigator.clipboard.writeText(\'{}\'); '
                'alert(\'Code copié !\');" style="cursor: pointer; padding: 2px 6px; '
                'font-size: 11px; border-radius: 3px;">📋 Copier</button>',
                obj.ephemeral_access_code,
                obj.ephemeral_access_code
            )
        elif obj.is_ephemeral:
            return format_html(
                '<span style="color: #dc3545;">⚠️ Pas de code</span>'
            )
        return format_html(
            '<span style="color: #999;">—</span>'
        )
    ephemeral_access_code_display.short_description = 'Code d\'accès'
    ephemeral_access_code_display.admin_order_field = 'ephemeral_access_code'
    
    # ========== OVERRIDE : get_queryset ==========
    def get_queryset(self, request):
        """
        Override pour utiliser admin_objects qui affiche TOUS les événements
        (y compris les éphémères).
        """
        # Utiliser le manager admin qui n'exclut pas les événements éphémères
        qs = self.model.admin_objects.get_queryset()
        
        # Le reste du code par défaut de l'admin
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs
    
    # ========== OVERRIDE : save_model ==========
    def save_model(self, request, obj, form, change):
        """
        Override pour générer automatiquement le code d'accès
        lors de la création d'un événement éphémère.
        """
        is_new = obj.pk is None
        
        super().save_model(request, obj, form, change)
        
        # Si c'est un nouvel événement éphémère sans code, en générer un
        if obj.is_ephemeral and not obj.ephemeral_access_code:
            obj.generate_ephemeral_access_code()
            self.message_user(
                request,
                f"Code d'accès généré automatiquement : {obj.ephemeral_access_code}",
                level='SUCCESS'
            )

@admin.register(EventImage)
class EventImageAdmin(BaseModelAdmin):
    pass


@admin.register(FavouriteEvent)
class FavouriteEventAdmin(BaseModelAdmin):
    pass


@admin.register(TicketCategoryFeature)
class TicketCategoryFeatureAdmin(BaseModelAdmin):
    pass


@admin.register(TicketCategory)
class TicketCategoryAdmin(BaseModelAdmin):
    pass


@admin.register(Ticket)
class TicketAdmin(BaseModelAdmin):
    search_fields = ("name", "description", "category__name", "event__name",)
    list_filter = ('organization',)
    ordering = ['-timestamp']


@admin.register(Order)
class OrderAdmin(BaseModelAdmin):
    search_fields = ("name", "email", "phone", "order_id", "user__first_name", "user__last_name")
    list_filter = ('user', 'status')
    ordering = ['-timestamp']

    actions = ['send_e_tickets_by_emails']

    @admin.action(description="Envoyer les tickets par e-mail")
    def send_e_tickets_by_emails(self, request, queryset):
        for order in queryset.filter(status=OrderStatusEnum.FINISHED.value):
            notifications_tasks.notify_users_about_end_of_pseudo_anonymous_order_processing.delay(str(order.pk))
        self.message_user(request, f"{queryset.count()} envois de tickets lancés avec succès.")


@admin.register(OrderItem)
class OrderItemAdmin(BaseModelAdmin):
    pass


@admin.register(ETicket)
class ETicketAdmin(BaseModelAdmin):
    pass


@admin.register(EventHighlightingType)
class EventHighlightingTypeAdmin(BaseModelAdmin):
    pass


@admin.register(EventHighlighting)
class EventHighlightingAdmin(BaseModelAdmin):
    search_fields = ("uuid", "event__name")
    list_filter = ('type', 'active_status')
