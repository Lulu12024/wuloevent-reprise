from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.events.models import Event, Order, Ticket
from apps.events.tasks import eticket_tasks
from apps.notifications.tasks import notifications_tasks
from apps.xlib.enums import OrderStatusEnum


@receiver(post_save, sender=Event)
def initiate_notification_processes(sender, instance: Event, created: bool, **kwargs):
    if created:
        notifications_tasks.create_notification_for_admins_about_event_creation.delay(str(instance.pk))

        # Set default expiry date
        # instance.expiry_date = datetime.combine(instance.date, instance.hour) + timedelta(days=1)
        # instance.save(update_fields=['expiry_date'])

    if instance.tracker.has_changed('have_passed_validation') and instance.tracker.previous(
            'have_passed_validation') is False and instance.valid:
        notifications_tasks.create_notification_for_event_publisher_about_event_validation.delay(
            str(instance.pk))
        notifications_tasks.create_notification_for_those_that_near_by.delay(
            str(instance.pk))
        notifications_tasks.create_notification_for_those_that_favoured_this_type_of_event.delay(
            str(instance.pk))
        # Pass ZOI for the moment
        '''notifications_tasks.create_notification_for_zoi_containing_event_location.delay(
            instance.id)'''
        notifications_tasks.create_notification_for_poi_near_by_event_location.delay(
            str(instance.pk))
        notifications_tasks.create_notification_for_event_publisher_followers.delay(
            str(instance.pk))


@receiver(post_save, sender=Ticket)
def update_event_expiry_datetime(sender, instance: Ticket, **kwargs):
    event = instance.event
    if instance.expiry_date > event.expiry_date:
        event.expiry_date = instance.expiry_date
        event.save(update_fields=['expiry_date'])


@receiver(post_save, sender=Order)
def finalize_other_process(sender, instance, created, **kwargs):
    if instance.active and instance.tracker.has_changed('status') and instance.tracker.previous(
            'status') == OrderStatusEnum.SUBMITTED.value and instance.status == OrderStatusEnum.STARTED.value:
        # Send notification about other receipt, after receiving transaction paid signal from fedapay
        notifications_tasks.notify_users_about_order_receipt.delay(str(instance.pk))

        # Start e-ticket generation task
        eticket_tasks.generate_etickets_for_order.delay(str(instance.pk))

    # Send notifications after order status set to finished
    if instance.active and instance.tracker.has_changed('status') and instance.tracker.previous(
            'status') == OrderStatusEnum.STARTED.value and instance.status == OrderStatusEnum.FINISHED.value:
        if instance.is_pseudo_anonymous:
            notifications_tasks.notify_users_about_end_of_pseudo_anonymous_order_processing.delay(str(instance.pk))
        else:
            notifications_tasks.notify_users_about_end_of_order_processing.delay(str(instance.pk))
