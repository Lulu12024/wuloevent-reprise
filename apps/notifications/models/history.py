# -*- coding: utf-8 -*-
"""
Created on 22/07/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

#
#
# # Notifications sent history
# class NotificationSentHistory(AbstractCommonBaseModel):
#     STATUS = (("S", "Succès"), ("E", "Échec"))
#     notification = models.ForeignKey(
#         to="notifications.Notification",
#         verbose_name="Notification",
#         on_delete=models.CASCADE,
#     )
#
#     status = models.CharField(
#         max_length=1,
#         choices=STATUS,
#         default="S",
#         verbose_name="Statut",
#     )
#     is_read = models.BooleanField(default=False)
#
#     def __str__(self):
#         return "{} : {} : {}".format(self.timestamp, self.notification, self.status)
#
#     def get_date(self):
#         time = timezone.now()
#
#         if self.timestamp.day == time.day:
#             if (time.hour - self.timestamp.hour) == 0:
#                 minute = time.minute - self.timestamp.minute
#                 if minute < 1:
#                     return "Just Now"
#                 return str(minute) + " min ago"
#             return str(time.hour - self.timestamp.hour) + " hours ago"
#         else:
#             if self.timestamp.month == time.month:
#                 return str(time.day - self.timestamp.day) + " days ago"
#             else:
#                 if self.timestamp.year == time.year:
#                     return str(time.month - self.timestamp.month) + " months ago"
#         return self.timestamp
#
#     def send(self):
#         raise NotImplementedError()
#
#     class Meta:
#         abstract = True
#
#
# class PushNotificationSentHistory(NotificationSentHistory):
#     sent_to = models.ForeignKey(
#         to="notifications.MobileDevice",
#         verbose_name="Appareil",
#         related_name="notifications_history",
#         on_delete=models.CASCADE,
#     )
#     objects = NotificationSendHistoryManager()
#
#     def __str__(self):
#         return "{} : {} : {} : {}".format(
#             self.timestamp, self.notification, self.sent_to.user, self.status
#         )
#
#     @staticmethod
#     def enroll(devices, notification):
#         for device in devices:
#             notification_history = PushNotificationSentHistory.objects.create(
#                 sent_to=device, notification=notification
#             )
#             notification_history.send()
#
#     def send(self):
#         notifier = one_signal_processor.Notifier(
#             player_ids=[self.sent_to.onesignal_id],
#             title=self.notification.title,
#             message=self.notification.message,
#             image=self.notification.image.url,
#         )
#         try:
#             if "event" in str(self.notification.type.name).lower():
#                 notifier.push_about_event(data=self.notification.data)
#             else:
#                 notifier.push()
#             self.status = "S"
#         except Exception as exc:
#             logger.exception(exc.__str__())
#             self.status = "E"
#         self.save()
#
#     class Meta:
#         verbose_name = "Historique d' envoi de Notification Push"
#         verbose_name_plural = "Historique d' envoi de notifications Push"
