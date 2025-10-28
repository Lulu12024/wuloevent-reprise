# -*- coding: utf-8 -*-
"""
Created on 22/07/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
import json

import courier
from courier.core import ApiError
from django.db import models
from django.utils import timezone

from apps.notifications.managers import NotificationManager
from apps.notifications.models.utils import get_notification_default_data
from apps.notifications.utils import id2slug
from apps.notifications.utils.courier_client import CourierClient
from apps.utils.utils import _upload_to
from apps.utils.validators import PhoneNumberValidator
from apps.xlib.enums import NOTIFICATION_STATUS_ENUM, NOTIFICATION_CHANNELS_ENUM, \
    NOTIFICATION_TYPE_TEMPLATE_BY_CHANNEL_ENUM
from commons.models import AbstractCommonBaseModel


class Notification(AbstractCommonBaseModel):
    type = models.ForeignKey(
        to="notifications.NotificationType",
        verbose_name="Type de Notification",
        related_name="related_notifications",
        on_delete=models.DO_NOTHING,
    )

    status = models.CharField(
        max_length=10,
        choices=NOTIFICATION_STATUS_ENUM.items(),
        default=NOTIFICATION_STATUS_ENUM.SUCCESS.value,
        verbose_name="Statut",
    )

    user = models.ForeignKey(
        to="users.User",
        verbose_name="Utilisateur associé",
        related_name="notifications",
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    email = models.EmailField(verbose_name="Email", max_length=96)
    phone = models.CharField(
        verbose_name="Numéro de téléphone",
        max_length=25,
        blank=True,
        null=True,
        validators=[PhoneNumberValidator()],
    )
    target_phone_id = models.CharField(verbose_name="Id courier du mobile", max_length=1024)

    title = models.CharField(verbose_name="Titre de la notification", max_length=256)
    message = models.TextField(verbose_name="Message")
    data = models.JSONField(verbose_name="Données", blank=False, null=False, default=get_notification_default_data)
    extra_data = models.JSONField(verbose_name="Extra données", blank=False, null=False)

    channels = models.JSONField(verbose_name="Canal", blank=True, null=True)

    icon = models.CharField(verbose_name="Icon", null=True, blank=True, max_length=1024)
    image = models.ImageField(verbose_name="Image", upload_to=_upload_to, null=True, blank=True, max_length=1024)

    unread = models.BooleanField(verbose_name="Désigne si la notification n'a ps été vu", default=True, blank=False,
                                 db_index=True)

    scheduled_to_delivery = models.DateTimeField(null=True, blank=True)

    objects = NotificationManager()

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"{self.title} | {self.target_email or self.target_phone}"

    def timesince(self, now=None):
        """
        Shortcut for the ``django.utils.timesince.timesince`` function of the
        current timestamp.
        """
        from django.utils.timesince import timesince as timesince_
        return timesince_(self.timestamp, now)

    def get_date(self):
        time = timezone.now()

        if self.timestamp.day == time.day:
            if (time.hour - self.timestamp.hour) == 0:
                minute = time.minute - self.timestamp.minute
                if minute < 1:
                    return "Just Now"
                return str(minute) + " min ago"
            return str(time.hour - self.timestamp.hour) + " hours ago"
        else:
            if self.timestamp.month == time.month:
                return str(time.day - self.timestamp.day) + " days ago"
            else:
                if self.timestamp.year == time.year:
                    return str(time.month - self.timestamp.month) + " months ago"
        return self.timestamp

    @property
    def target_email(self):
        return self.email or f'{self.user.email if self.user else "No Email"}'

    @property
    def target_phone(self):
        return self.phone or f'{self.user.phone if self.user else "No Phone"}'

    @property
    def slug(self):
        return id2slug(self.uuid)

    def mark_as_read(self):
        if self.unread:
            self.unread = False
            self.save()

    def mark_as_unread(self):
        if not self.unread:
            self.unread = True
            self.save()

    @staticmethod
    def bulk_insert(objs):
        from itertools import islice

        batch_size = 100
        created_objs: list[Notification] = []

        start_index = 0

        while True:
            end_index = start_index + batch_size

            batch = list(islice(objs, start_index, end_index))
            if not batch:
                break
            created_objs.extend(Notification.objects.bulk_create(batch, batch_size))

            start_index = end_index

        return Notification.objects.filter(uuid__in=[obj.pk for obj in created_objs])

    def send(self):

        if any(element in self.channels for element in
               [NOTIFICATION_CHANNELS_ENUM.EMAIL.value, NOTIFICATION_CHANNELS_ENUM.PUSH.value,
                NOTIFICATION_CHANNELS_ENUM.SMS.value, NOTIFICATION_CHANNELS_ENUM.WHATSAPP.value]):

            client = CourierClient()
            target_template = NOTIFICATION_TYPE_TEMPLATE_BY_CHANNEL_ENUM[self.type.name].value
            _to = {}
            for channel in self.channels:
                match channel:
                    case NOTIFICATION_CHANNELS_ENUM.EMAIL.value:
                        _to["email"] = self.target_email
                    case NOTIFICATION_CHANNELS_ENUM.PUSH.value:
                        _to["user_id"] = self.target_phone_id
                    case NOTIFICATION_CHANNELS_ENUM.SMS.value | NOTIFICATION_CHANNELS_ENUM.WHATSAPP.value:
                        _to["phone_number"] = self.target_phone

            message = courier.TemplateMessage(
                template=target_template,
                to=_to,
                data={**self.extra_data, "data": json.dumps(self.data)},
                routing=courier.Routing(method="all", channels=["email", "push", "sms", "inbox"]),
            )

            try:
                client.send(
                    message=message
                )
            except ApiError as e:
                self.status = NOTIFICATION_STATUS_ENUM.FAILED.value
                self.save(update_fields=['status'])
        return
