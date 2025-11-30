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
class EventAdmin(BaseModelAdmin):
    search_fields = ['name', 'pk', 'description', 'location_name']
    list_filter = ('organization', 'organization__owner')
    ordering = ('-timestamp', 'name')


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
