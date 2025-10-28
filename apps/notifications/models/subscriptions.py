# -*- coding: utf-8 -*-
"""
Created on 22/07/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""


from django.db import models

from commons.models import AbstractCommonBaseModel


class SubscriptionToNotificationType(AbstractCommonBaseModel):
    user = models.ForeignKey(
        to="users.User",
        verbose_name="Utilisateur",
        related_name="subscriptions_to_notification",
        on_delete=models.CASCADE,
    )
    notification_type = models.ForeignKey(
        to="NotificationType",
        verbose_name="Type de Notification",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return "{} : {}".format(self.user, self.notification_type)

    class Meta:
        unique_together = (
            "user",
            "notification_type",
        )
        verbose_name = "Abonnement à un type de Notifications"
        verbose_name_plural = "Abonnements à un type Notifications"
