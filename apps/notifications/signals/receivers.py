import json

from django.dispatch import receiver

from apps.notifications.signals.initializers import send_email_signal
from apps.notifications.tasks import send_in_app_email_task


@receiver(send_email_signal)
def process_email(sender, instance, email_data: dict, *args, **kwargs):
    send_in_app_email_task.delay(json.dumps(email_data))

#
# @receiver(post_save, sender=MobileDevice)
# def handle_one_signal_devices(sender, instance, created, **kwargs):
#     if created:
#         notifications_tasks.one_signal_register_device.delay(
#             instance.pk)
#     elif instance.tracker.has_changed('registration_id') or instance.tracker.has_changed(
#             'current_location_lat') or instance.tracker.has_changed(
#         'current_location_long') or instance.tracker.has_changed('type'):
#         notifications_tasks.one_signal_update_device.delay(
#             instance.pk)
#
#
# @receiver(pre_delete, sender=MobileDevice)
# def handle_one_signal_devices_delete(sender, instance, **kwargs):
#     notifications_tasks.one_signal_delete_device.delay(
#         instance.onesignal_id)
