from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notifications import tasks as notification_tasks
from apps.organizations.models import Withdraw, OrganizationMembership
from apps.xlib.enums import WithdrawStatusEnum


@receiver(post_save, sender=Withdraw)
def handle_withdraws_transaction(sender, instance, created, **kwargs):
    if not isinstance(instance, Withdraw):
        return

    if created:
        return

    if instance.tracker.has_changed('status') and instance.status == WithdrawStatusEnum.FINISHED.value:
        notification_tasks.notify_users_about_end_of_withdraw_processing.delay(str(instance.pk))


@receiver(post_save, sender=OrganizationMembership)
def handle_membership_creation(sender, instance, created, **kwargs):
    if not isinstance(instance, OrganizationMembership):
        return

    if created:
        notification_tasks.notify_users_about_new_membership_creation.delay(str(instance.pk))
