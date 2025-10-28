# -*- coding: utf-8 -*-
"""
Created on August 17, 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.contrib import admin, messages

# Register your models here.
from apps.notifications.models import MobileDevice, SubscriptionToNotificationType, \
    NotificationType, Notification
from commons.admin import BaseModelAdmin


@admin.register(MobileDevice)
class MobileDeviceAdmin(BaseModelAdmin):
    search_fields = ["user__first_name", "user__last_name", "user__email", "name"]


@admin.register(SubscriptionToNotificationType)
class SubscriptionToNotificationTypeAdmin(BaseModelAdmin):
    pass


@admin.register(NotificationType)
class NotificationTypeAdmin(BaseModelAdmin):
    pass


@admin.register(Notification)
class NotificationAdmin(BaseModelAdmin):
    search_fields = ["user__first_name", "user__last_name", "email", "phone", "target_phone_id", "title", "message",
                     "channels", ]
    list_filter = ["type", "status", "unread"]
    actions = ["send_notifications"]

    @admin.action(description="Envoyer les notifications sélectionnées")
    def send_notifications(self, request, queryset):
        queryset.bulk_send()

        self.message_user(
            request,
            f"Start the sending of {queryset.count()} notifications",
            messages.SUCCESS
        )
