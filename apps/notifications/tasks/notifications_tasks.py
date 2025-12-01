# -*- coding: utf-8 -*-
"""
Created on August 17, 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import itertools
import json
import time
from datetime import timedelta

from celery import shared_task
from celery.utils.log import get_task_logger
from django.db import transaction
from django.db.models import F, IntegerField
from django.db.models.functions import Cast

from apps.events.models import FavouriteEvent, FavouriteEventType, Event, Order, EventHighlighting
from apps.events.utils.orders import send_e_tickets_email_for_order
from apps.notifications.models import (
    MobileDevice,
    NotificationType,
    Notification,
    SubscriptionToNotificationType,
)
from apps.notifications.onesignal import Processor
from apps.organizations.models import Withdraw, Subscription, OrganizationMembership
from apps.users.business_logics.users import get_app_admins
from apps.users.models import User, ZoneOfInterest, PointOfInterest, Transaction
from apps.utils.models import Variable
from apps.utils.utils import replace_english_words
from apps.xlib.enums import NOTIFICATION_TYPES_ENUM, NOTIFICATION_CHANNELS_ENUM, VARIABLE_NAMES_ENUM

logger = get_task_logger(__name__)


def get_event_image_uri(ressource_url):
    site_variable = Variable.objects.get(
        name=VARIABLE_NAMES_ENUM.CURRENT_SITE_BASE_ADDRESS.value
    )
    image_url = "https://i.ibb.co/pdzKtq4/Wulo-Events-Logo.png"
    try:
        site_variable_value = site_variable.format_value(
            site_variable.possible_values.first().value
        )
        if ressource_url:
            image_url = f"{site_variable_value}{ressource_url}"
    except Exception as exc:
        logger.info(exc)
        pass
    return image_url


@shared_task()
def send_in_app_email_task(data):
    """
    The data params is a stringed dict.
    The dict is form by key, values that are params took by the mailer to send a mail

    """
    email_data = json.loads(data)
    email_type = email_data.get('email_type', "")

    params = email_data.get('params', {})

    email = params["email"]
    full_name = params["full_name"]

    code = params.get("code", None)
    user_id = params.get("user_id", None)

    match email_type:
        case "welcome":
            context = {
                "fullName": full_name,
            }
            notification_type_name = NOTIFICATION_TYPES_ENUM.WELCOME.value
            title = "Bienvenu {full_name}".format(full_name=full_name)
        case "account_validation_request":
            context = {
                "fullName": full_name,
                "code": code,
                "expiryTime": "10 minutes",
            }
            notification_type_name = NOTIFICATION_TYPES_ENUM.ACCOUNT_VALIDATION_REQUEST.value
            title = "Demande de validation de compte - {full_name}".format(full_name=full_name)
        case "account_validation_successful":
            context = {
                "fullName": full_name,
            }
            notification_type_name = NOTIFICATION_TYPES_ENUM.ACCOUNT_VALIDATION_SUCCESSFUL.value
            title = "Validation de compte réussi - {full_name}".format(full_name=full_name)
        case "password_reset_request":
            context = {
                "fullName": full_name,
                "code": code,
                "expiryTime": "10 minutes",
            }
            notification_type_name = NOTIFICATION_TYPES_ENUM.PASSWORD_RESET_REQUEST.value
            title = "Demande de modification de mot de passe - {full_name}".format(full_name=full_name)
        case "password_reset_successful":
            context = {
                "fullName": full_name,
            }
            notification_type_name = NOTIFICATION_TYPES_ENUM.PASSWORD_RESET_SUCCESSFUL.value
            title = "Modification de mot de passe réussi - {full_name}".format(full_name=full_name)
        case _:
            raise ValueError("Email send type is not valid")

    notification_type = NotificationType.get_by_name(
        name=notification_type_name
    )

    notification = Notification.objects.create(
        title=title,
        type=notification_type,
        user_id=user_id,
        channels=[NOTIFICATION_CHANNELS_ENUM.EMAIL.value],
        email=email,
        extra_data=context,
        data={}
    )
    notification.send()


# Implementation OK
@shared_task()
def create_notification_for_those_that_near_by(event_id):
    with transaction.atomic():
        event = Event.objects.get(pk=event_id)
        devices_near_by = (
            MobileDevice.objects.annotate_spherical_distance(
                ("current_location_lat", "current_location_long"),
                (event.location_lat, event.location_long),
            ).select_related("user").distinct('user')
            # .filter(
            #     ~Q(
            #         notifications_history__notification__data__eventId=event_id,
            #         notifications_history__timestamp__gte=datetime.now() - timedelta(hours=1),
            #     ),
            #     spherical_distance__lte=7,
            # ).distinct()
        )
        if not devices_near_by.exists():
            return False

        notification_type = NotificationType.get_by_name(
            name=NOTIFICATION_TYPES_ENUM.EVENT_NEAR_BY_USER_LAST_LOCATION.value
        )
        subscription_to_this_notification_type_users_ids = (
            SubscriptionToNotificationType.objects.filter(
                notification_type=notification_type
            ).values_list("user_id", flat=True)
        )
        user_not_subscribed_to_notification_type = User.objects.exclude(
            id__in=subscription_to_this_notification_type_users_ids
        ).values_list("pk", flat=True)
        devices_near_by = devices_near_by.exclude(
            user_id__in=user_not_subscribed_to_notification_type
        )
        if len(devices_near_by) > 0:
            # Todo: Create related courier template
            notifications = Notification.bulk_insert([
                Notification(
                    user=device.user,
                    type=notification_type,
                    target_phone_id=device.registration_id,
                    channels=[NOTIFICATION_CHANNELS_ENUM.PUSH.value],
                    message="Cet évènement aura lieu près de vous. Veuillez Vérifier !",
                    title=f"{event.name} nouvellement publié",
                    data={"entityId": event_id, "entityLink": event.get_dynamic_link(), "type": "EVENT",
                          "logLevel": "info"},
                    extra_data={
                        "eventName": event.name,
                        "eventDate": event.date.strftime('%d/%m/%Y'),
                        "eventTime": event.hour.strftime('%H:%M'),
                        "eventLocation": event.location_name,
                        "eventLink": event.get_dynamic_link(),
                    },
                    image=get_event_image_uri(event.get_cover_image_url),

                ) for device in devices_near_by]
            )
            notifications.bulk_send()


# Todo: test
@shared_task()
def create_notification_for_admins_about_event_creation(event_id):
    with transaction.atomic():
        event = Event.objects.select_related("organization").get(pk=event_id)

        notification_type = NotificationType.get_by_name(
            name=NOTIFICATION_TYPES_ENUM.NEW_EVENT_CREATION.value
        )

        admins = get_app_admins().distinct('email')

        if len(admins) > 0:
            # Todo: X
            notifications = Notification.bulk_insert([
                Notification(
                    user=admin,
                    type=notification_type,
                    phone=admin.phone,
                    email=admin.email,
                    channels=[NOTIFICATION_CHANNELS_ENUM.EMAIL.value],
                    message="",
                    title=f"{event.name} nouvellement publié",
                    data={"entityId": event_id, "entityLink": event.get_dynamic_link(), "type": "EVENT",
                          "logLevel": "info"},
                    # Todo: generate validation link
                    extra_data={
                        "adminName": admin.first_name,
                        "organizationName": event.organization.name,
                        "eventName": event.name,
                        "eventDate": event.date.strftime('%d/%m/%Y'),
                        "eventTime": event.hour.strftime('%H:%M'),
                        "eventLocation": event.location_name,
                        "eventValidationLink": "",
                    },
                    image=get_event_image_uri(event.get_cover_image_url),

                ) for admin in admins if
                admin.is_staff or (admin.role and admin.role.label in ["ADMIN", "STAFF", "SUPER_ADMIN", "EVENT_OWNER"])]
            )
            notifications.bulk_send()


# Implementation OK
@shared_task()
def create_notification_for_those_that_favoured_this_type_of_event(event_id):
    with transaction.atomic():
        event = Event.objects.get(pk=event_id)
        users_ids = FavouriteEventType.objects.filter(event_type=event.type).values_list(
            "user_id", flat=True
        )

        if len(users_ids) < 0:
            return False

        related_devices = MobileDevice.objects.select_related("user").filter(
            # ~Q(
            #     notifications_history__notification__data__eventId=event_id,
            #     notifications_history__timestamp__gte=datetime.now() - timedelta(hours=1),
            # ),
            user_id__in=users_ids,
        )
        notification_type = NotificationType.get_by_name(
            name=NOTIFICATION_TYPES_ENUM.NEW_EVENT_CREATION_IN_FAVORED_CATEGORY.value
        )
        subscription_to_this_notification_type_users_ids = (
            SubscriptionToNotificationType.objects.filter(
                notification_type=notification_type
            ).values_list("user_id", flat=True)
        )
        user_not_subscribed_to_notification_type = User.objects.exclude(
            id__in=subscription_to_this_notification_type_users_ids
        ).values_list("pk", flat=True)

        related_devices = related_devices.filter(
            user_id__in=user_not_subscribed_to_notification_type
        )
        if len(related_devices) > 0:
            notifications = Notification.bulk_insert(
                [
                    Notification(
                        user=device.user,
                        type=notification_type,
                        target_phone_id=device.registration_id,
                        email=device.user.email,
                        channels=[NOTIFICATION_CHANNELS_ENUM.PUSH.value, NOTIFICATION_CHANNELS_ENUM.INBOX.value],
                        message=f'Un évènement a été publié dans la catégorie "{event.type.name}"'
                                f' que vous avez choisi comme favori. Veuillez Vérifier !',
                        title=f"{event.name} nouvellement publié",
                        data={"entityId": event_id, "entityLink": event.get_dynamic_link(), "type": "EVENT",
                              "logLevel": "info"},
                        extra_data={
                            "eventImage": get_event_image_uri(event.get_cover_image_url),
                            "categoryName": event.type.name,
                            "eventLink": event.get_dynamic_link(),
                        },
                        image=get_event_image_uri(event.get_cover_image_url),
                    ) for device in related_devices
                ]
            )
            notifications.bulk_send()


@shared_task()
def create_notification_for_zoi_containing_event_location(event_id):
    with transaction.atomic():
        time.sleep(10)
        event = Event.objects.get(pk=event_id)
        users_ids = ZoneOfInterest.objects.filter(
            geofence__contains=event.location
        ).values_list("user_id", flat=True)

        if len(users_ids) < 0:
            return False

        related_devices = MobileDevice.objects.select_related("user").filter(
            # ~Q(
            #     notifications_history__notification__data__eventId=event_id,
            #     notifications_history__timestamp__gte=datetime.now() - timedelta(hours=1),
            # ),
            user_id__in=users_ids,
        )
        if len(related_devices) > 0:
            notification_type = NotificationType.get_by_name(
                name=NOTIFICATION_TYPES_ENUM.EVENT_LOCATION_INSIDE_ZONE_OF_INTEREST.value
            )
            notifications = Notification.bulk_insert(
                [
                    Notification(
                        user=device.user,
                        target_phone_id=device.registration_id,
                        email=device.user.email,
                        channels=[NOTIFICATION_CHANNELS_ENUM.PUSH.value, NOTIFICATION_CHANNELS_ENUM.INBOX.value],
                        type=notification_type,
                        message="Un évènement aura lieu près d' une zone d' intérêt que vous "
                                "avez créé. Veuillez Vérifier !",
                        title="Nouvel Évènement Publié",
                        data={"entityId": event_id, "entityLink": event.get_dynamic_link(), "type": "EVENT",
                              "logLevel": "info"},
                        image=get_event_image_uri(event.get_cover_image_url)
                    ) for device in related_devices]
            )
            notifications.bulk_send()


@shared_task()
def create_notification_for_poi_near_by_event_location(event_id):
    with transaction.atomic():
        event = Event.objects.get(pk=event_id)
        users_ids = (
            PointOfInterest.objects.annotate_spherical_distance(
                ("location_lat", "location_long"), (event.location_lat, event.location_long)
            )
            .filter(spherical_distance__lte=F("approximate_distance"))
            .values_list("user_id", flat=True)
        )

        if len(users_ids) < 0:
            return False

        related_devices = MobileDevice.objects.select_related("user").filter(
            # ~Q(
            #     notifications_history__notification__data__eventId=event_id,
            #     notifications_history__timestamp__gte=datetime.now() - timedelta(hours=1),
            # ),
            user_id__in=users_ids,
        )
        if len(related_devices) > 0:
            notification_type = NotificationType.get_by_name(
                name=NOTIFICATION_TYPES_ENUM.EVENT_LOCATION_NEAR_BY_USER_POI.value
            )
            notifications = Notification.bulk_insert(
                [
                    Notification(
                        user=device.user,
                        target_phone_id=device.registration_id,
                        email=device.user.email,
                        channels=[NOTIFICATION_CHANNELS_ENUM.PUSH.value, NOTIFICATION_CHANNELS_ENUM.INBOX.value],
                        type=notification_type,
                        title=f"{event.name} nouvellement publié.",
                        message="Cet évènement aura lieu près d' un point d' intérêt que vous "
                                "avez choisi. Veuillez Vérifier !",
                        data={"entityId": event_id, "entityLink": event.get_dynamic_link(), "type": "EVENT",
                              "logLevel": "info"},
                        image=get_event_image_uri(event.get_cover_image_url))
                    for device in related_devices
                ]
            )
            notifications.bulk_send()


@shared_task()
def create_notification_for_event_publisher_about_event_validation(event_id):
    with transaction.atomic():
        event = Event.objects.select_related('organization').get(pk=event_id)

        related_devices = MobileDevice.objects.filter(
            user_id__in=[event.publisher_id, event.organization.owner_id]
        ).distinct("user__email")

        if len(related_devices) > 0:
            notification_type = NotificationType.get_by_name(
                name=NOTIFICATION_TYPES_ENUM.EVENT_VALIDATED.value
            )
            event_link = event.get_dynamic_link()
            # Todo: X
            # Todo: Bulk send notification with
            notifications = Notification.bulk_insert(
                [
                    Notification(
                        user=device.user,
                        target_phone_id=device.registration_id,
                        email=device.user.email,
                        type=notification_type,
                        channels=[NOTIFICATION_CHANNELS_ENUM.EMAIL.value, NOTIFICATION_CHANNELS_ENUM.PUSH.value,
                                  NOTIFICATION_CHANNELS_ENUM.INBOX.value],
                        message=f"L' évènement {event.name} que votre organisation a publié vient d' être validé."
                                " Veuillez Vérifier !",
                        title=f"{event.name} nouvellement validé",
                        data={
                            "entityId": event_id,
                            "entityLink": event_link,
                            "type": "EVENT",
                            "logLevel": "info"
                        },
                        extra_data={
                            "eventName": event.name,
                            "organizationOwnerName": device.user.get_full_name(),
                            "eventLink": event_link
                        },
                        image=get_event_image_uri(event.get_cover_image_url))
                    for device in related_devices
                ]
            )
            notifications.bulk_send()


# Implementation
@shared_task()
def create_notification_for_event_publisher_followers(event_id):
    with transaction.atomic():
        event = Event.objects.get(pk=event_id)
        users_ids = event.organization.users_followings_me.values_list(
            "follower", flat=True
        )
        if len(users_ids) < 0:
            return False
        related_devices = MobileDevice.objects.filter(
            user_id__in=users_ids,
        )
        if len(related_devices) > 0:
            notification_type = NotificationType.get_by_name(
                name=NOTIFICATION_TYPES_ENUM.FOLLOWED_EVENT_PUBLISHER.value
            )

            notifications = Notification.bulk_insert(
                [
                    Notification(
                        user=device.user,
                        target_phone_id=device.registration_id,
                        email=device.user.email,
                        type=notification_type,
                        # channels=[NOTIFICATION_CHANNELS_ENUM.PUSH.value, NOTIFICATION_CHANNELS_ENUM.INBOX.value],
                        channels=[NOTIFICATION_CHANNELS_ENUM.INBOX.value],
                        message=f"L' Organisation {event.organization.name} que vous suivez vient de publier un "
                                "évènement. Veuillez Vérifier !",
                        title=f"{event.name} nouvellement publié",
                        data={"entityId": event_id, "entityLink": event.get_dynamic_link(), "type": "EVENT",
                              "logLevel": "info"},
                        extra_data={

                        },
                        image=get_event_image_uri(event.get_cover_image_url))
                    for device in related_devices
                ]
            )
            notifications.bulk_send()


# Implementation OK
@shared_task()
def notify_users_about_nearly_sold_out_of_ticket_event(event_id, ticket_name, percentage, remaining_quantity):
    with transaction.atomic():
        # Todo: Prefetch data related to organization
        event = Event.objects.select_related("organization").prefetch_related("tickets").get(pk=event_id)
        events_tickets = event.tickets.all()

        logger.info("\n Begin Notifications About Nearly Sold Out of Ticket \n")

        notifications_list = []

        # Notifications to simple users

        related_favourite_events = event.adds_like_favourite.all()

        for favorite_event in related_favourite_events:
            user_mobile_device = MobileDevice.objects.filter(user__pk=favorite_event.user_id).first()

            users_notification_type = NotificationType.get_by_name(
                name=NOTIFICATION_TYPES_ENUM.NEARLY_SOLD_OUT_OF_TICKETS_OF_FAVOURED_EVENT.value,
            )
            if not Notification.objects.filter(
                    type=users_notification_type,
                    data__eventId=str(event_id),
                    data__percentage=percentage,
                    user_id=favorite_event.user_id
            ).exists():
                notifications_list.append(
                    Notification(
                        type=users_notification_type,
                        user=favorite_event.user,
                        target_phone_id=user_mobile_device.registration_id if user_mobile_device else "",
                        channels=[NOTIFICATION_CHANNELS_ENUM.EMAIL.value,
                                  NOTIFICATION_CHANNELS_ENUM.PUSH.value,
                                  NOTIFICATION_CHANNELS_ENUM.INBOX.value],
                        email=favorite_event.user.email,
                        message=f"Les tickets pour l' évènement {event.name} que vous ajouté en favoris s' épuisent, "
                                f"nous vous invitons à vous procurer votre ticket avant épuisement total. ",
                        title="Alerte - Tickets en voie d' épuisement",
                        data={"entityId": str(event.pk), "percentage": percentage, "type": "EVENT",
                              "logLevel": "info"},
                        extra_data={
                            "userName": favorite_event.user.get_full_name(),
                            "eventName": event.name,
                            "ticketName": ticket_name,
                            "remainingQuantity": ticket_name,
                            "eventLink": event.get_dynamic_link()
                        },
                        image=get_event_image_uri(event.get_cover_image_url),
                    )
                )

        # Notify the event owner

        owner_notification_type = NotificationType.get_by_name(
            name=NOTIFICATION_TYPES_ENUM.NEARLY_SOLD_OUT_OF_TICKETS.value
        )

        owner_mobile_device = MobileDevice.objects.filter(user__pk=event.organization.owner_id).first()

        notifications_list.append(
            Notification(
                type=owner_notification_type,
                user=event.organization.owner,
                target_phone_id=owner_mobile_device.registration_id if owner_mobile_device else "",
                channels=[NOTIFICATION_CHANNELS_ENUM.EMAIL.value, NOTIFICATION_CHANNELS_ENUM.PUSH.value,
                          NOTIFICATION_CHANNELS_ENUM.INBOX.value],
                email=event.organization.owner.email,
                message=f"Les tickets pour l' évènement {event.name} que vous avez créé s' épuisent, nous vous"
                        f" invitons à vérifier et completer les quantités disponibles si besoin.",
                title="Alerte - Tickets en voie d' épuisement",
                data={"entityId": str(event.pk), "percentage": percentage, "type": "EVENT",
                      "logLevel": "info"},
                extra_data={
                    "organizerName": event.organization.owner.get_full_name(),
                    "ticketType": ticket_name,
                    "percentageReached": percentage,
                    "eventName": event.name,
                    "remainingTicketsDetails":
                        [
                            {"ticketType": ticket.name, "remainingQuantity": str(ticket.available_quantity)}

                            for ticket in events_tickets
                        ]
                },
                image=get_event_image_uri(event.get_cover_image_url),
            )
        )

        notifications = Notification.bulk_insert(
            notifications_list
        )
        logger.info(notifications)
        notifications.bulk_send()
        logger.info("\n Finished Notifications About Nearly Sold Out of Ticket \n")


# Implementation OK
@shared_task()
def notify_users_about_the_approach_of_favourite_event():
    with transaction.atomic():
        # Todo: Review the usage of time before start logic here
        events = Event.objects.filter(time_before_start__gte=0)

        event_approach_notification_moments_variable = Variable.objects.get(
            name=VARIABLE_NAMES_ENUM.EVENT_APPROACH_NOTIFICATIONS_MOMENTS.value
        )
        # event_approach_notification_moments_variable_values_as_list  ====== eanmvval
        eanmvval = list(
            event_approach_notification_moments_variable.possible_values.annotate(
                value_as_int=Cast("value", IntegerField())
            )
            .order_by("value_as_int")
            .values_list("value_as_int", flat=True)
        )
        eanmvval_preceded_by_zero = eanmvval.copy()
        eanmvval_preceded_by_zero[:0] = [0]
        intervals = list(itertools.zip_longest(eanmvval_preceded_by_zero, eanmvval))[:-1]
        replacers = {
            "day": "Jour",
            "days": "Jours",
            "month": "Mois",
            "months": "Mois",
            "year": "Année",
            "years": "Années",
        }

        logger.info("\n Begin Notifications About Favourite Event Task \n")

        notifications_list = []

        for interval in intervals:

            events_in_interval = events.filter(
                valid=True,
                active=True,
                time_before_start__gte=interval[0],
                time_before_start__lte=interval[1],
            )

            related_favourite_events = FavouriteEvent.objects.select_related("user").select_related("event").filter(
                event__pk__in=list(events_in_interval.values_list("pk", flat=True))
            )

            for favorite_event in related_favourite_events:
                remaining_time = f"{replace_english_words(replacers, timedelta(seconds=interval[1]).__str__())}"
                mobile_device = MobileDevice.objects.filter(user__pk=favorite_event.user_id).first()

                notification_type = NotificationType.get_by_name(
                    name=NOTIFICATION_TYPES_ENUM.APPROACH_OF_FAVOURED_EVENT.value
                )

                if not Notification.objects.filter(
                        type=notification_type,
                        data__entityId=str(favorite_event.event_id),
                        data__remainingTime=remaining_time,
                        user_id=favorite_event.user_id
                ).only('pk').exists():
                    _channels = []
                    if favorite_event.receive_news_by_email:
                        _channels.append(NOTIFICATION_CHANNELS_ENUM.EMAIL.value)

                    if mobile_device:
                        _channels.append(NOTIFICATION_CHANNELS_ENUM.PUSH.value)
                    # Todo: x

                    notifications_list.append(
                        Notification(
                            type=notification_type,
                            user=favorite_event.user,
                            target_phone_id=mobile_device.registration_id if mobile_device else "",
                            channels=_channels,
                            email=favorite_event.user.email,
                            message=f"Il reste environ {remaining_time} pour l' évènement {favorite_event.event.name} que vous avez choisi comme favoris",
                            title="Évènement Favoris en Approche",
                            data={"entityId": str(favorite_event.event_id), "remainingTime": remaining_time,
                                  "type": "EVENT",
                                  "logLevel": "info"},
                            # Todo: add precision about the remaining time before event starts ( On the template also )
                            extra_data={
                                "userName": favorite_event.user.get_full_name(),
                                "eventName": favorite_event.event.name,
                                "eventDate": favorite_event.event.date.strftime('%d/%m/%Y'),
                                "eventTime": favorite_event.event.hour.strftime('%H:%M'),
                                "eventLocation": favorite_event.event.location_name,
                                "eventLink": favorite_event.event.get_dynamic_link(),
                            },
                            image=get_event_image_uri(favorite_event.event.get_cover_image_url),
                        )
                    )
        if len(notifications_list) > 0:
            notifications = Notification.bulk_insert(
                notifications_list
            )
            notifications.bulk_send()

        logger.info("\n Finished Notifications About Event Tas \n")


@shared_task()
def notify_user_about_transaction_issue(transaction_id, message=None, category=None, is_success=True):
    with transaction.atomic():
        category_text = {
            "WITHDRAW": "de retrait",
            "ORDER_PAYMENT": "d' achat de ticket",
            "SUBSCRIPTION_PAYMENT": "d' abonnement",
            "EVENT_HIGHLIGHTING_PAYMENT": "de mise en avant d' évènement",
            "PAYMENT": "de paiement"
        }

        if category not in category_text.keys():
            raise ValueError('Unknown category chosen.')

        _transaction = Transaction.objects.get(pk=transaction_id)

        notification_type = NotificationType.get_by_name(
            name=NOTIFICATION_TYPES_ENUM.END_OF_TRANSACTION_PROCESSING.value,
        )

        user_devices = [MobileDevice.objects.filter(user__pk=_transaction.user_id).distinct().last()]

        notifications = Notification.bulk_insert(
            [
                Notification(
                    type=notification_type,
                    user=_transaction.user,
                    target_phone_id=device.registration_id,
                    channels=[NOTIFICATION_CHANNELS_ENUM.PUSH.value, NOTIFICATION_CHANNELS_ENUM.INBOX.value],
                    data={
                        "entityId": str(_transaction.pk),
                        # "type": category,
                        "type": "TRANSACTION",
                        "logLevel": "success" if is_success else "error",
                        "status": is_success
                    },
                    extra_data={
                        "message": message if message else f"",
                        "title": f"Fin de traitement de la transaction {category_text[category]}",
                        "status": is_success
                    },
                    message=message if message else f"",
                    title=f"Fin de traitement de la transaction {category_text[category]}",
                )
                for device in user_devices if device
            ]
        )
        notifications.bulk_send()


# Implementation Ok
@shared_task()
def notify_users_about_order_receipt(order_id):
    with transaction.atomic():
        order = Order.objects.select_related("user").select_related("item", "item__ticket", "item__ticket__event").get(
            pk=order_id)
        mobile_device = MobileDevice.objects.filter(user__pk=order.user_id).last()

        notification_type = NotificationType.get_by_name(
            name=NOTIFICATION_TYPES_ENUM.ORDER_RECEIPT.value
        )
        order_item = order.item
        order_details = [
            {
                "ticketType": order_item.ticket.name,
                "quantity": order_item.quantity,
                "eventName": order_item.ticket.event.name,
                "price": str(order_item.line_total)
            }
        ]

        # Notify the user that make the command about receipt of the order
        target_email = order.email if order.email and order.email != "" else order.user.email
        if target_email:
            notification = Notification.objects.create(
                type=notification_type,
                user=order.user,
                target_phone_id=mobile_device.registration_id if mobile_device else "",
                channels=[NOTIFICATION_CHANNELS_ENUM.EMAIL.value],
                email=target_email,
                data={
                    "entityId": str(order.pk),
                    "type": "ORDER",
                    "logLevel": "success"},
                extra_data={
                    "fullName": order.user.get_full_name(),
                    "orderId": order.order_id,
                    "orderDetails": order_details
                },
                message="",
                title="Reception de commande.",
            )

            notification.send()


@shared_task()
def notify_users_about_end_of_order_processing(order_id):
    with transaction.atomic():
        order = Order.objects.select_related("user").select_related("item", "item__ticket", "item__ticket__event").get(
            pk=order_id)
        mobile_device = MobileDevice.objects.filter(user__pk=order.user_id).last()

        notification_type = NotificationType.get_by_name(
            name=NOTIFICATION_TYPES_ENUM.END_OF_TICKETS_GENERATION_FOR_ORDER.value
        )

        # Todo: x
        # Todo: format order details

        # Notify the user that make the command about end of processing
        target_email = order.email if order.email and order.email != "" else order.user.email
        if target_email:
            notification = Notification.objects.create(
                type=notification_type,
                user=order.user,
                target_phone_id=mobile_device.registration_id if mobile_device else "",
                channels=[NOTIFICATION_CHANNELS_ENUM.EMAIL.value, NOTIFICATION_CHANNELS_ENUM.PUSH.value,
                          NOTIFICATION_CHANNELS_ENUM.INBOX.value],
                email=target_email,
                data={"entityId": str(order.pk), "type": "ORDER", "logLevel": "success"},
                # Todo: Generate ticket list link
                # Todo: Rewrite the tickets list link logique
                extra_data={
                    "fullName": order.user.get_full_name(),
                    "orderId": order.order_id,
                    "ticketsListLink": order.item.ticket.event.get_dynamic_link()
                },
                message=f"La commande {order.order_id} que vous avez passé à été traité avec succès, "
                        f" Veuillez vérifiez la liste de vos tickets.",
                title="Fin de traitement de commande.",
            )

            notification.send()


@shared_task()
def notify_users_about_end_of_pseudo_anonymous_order_processing(order_id):
    order = Order.objects.select_related("user").prefetch_related("related_e_tickets").get(
        pk=order_id)

    # Notify the user that make the command about end of processing
    target_email = order.email if order.email and order.email != "" else order.user.email
    if target_email:
        # Todo: This is a temporary solution to send the email this way using smtp configs
        send_e_tickets_email_for_order(
            order_id=order.order_id,
            user_email=target_email,
            user_full_name=order.user.get_full_name(),
            e_tickets=order.related_e_tickets.all(),
        )


@shared_task()
def notify_users_about_end_of_withdraw_processing(withdraw_id):
    with transaction.atomic():
        withdraw = Withdraw.objects.select_related("organization").get(pk=withdraw_id)
        owner = withdraw.organization.owner
        mobile_device = MobileDevice.objects.filter(user__pk=owner.pk).last()

        notification_type = NotificationType.get_by_name(
            name=NOTIFICATION_TYPES_ENUM.WITHDRAW_REQUEST_SUCCESSFUL.value
        )

        notification = Notification.objects.create(
            type=notification_type,
            user=owner,
            target_phone_id=mobile_device.registration_id if mobile_device else "",
            channels=[NOTIFICATION_CHANNELS_ENUM.EMAIL.value, NOTIFICATION_CHANNELS_ENUM.PUSH.value,
                      NOTIFICATION_CHANNELS_ENUM.INBOX.value],
            email=owner.email,
            data={"entityId": str(withdraw.pk), "type": "WITHDRAW", "logLevel": "success"},
            extra_data={
                "fullName": owner.get_full_name(),
                "withdrawRequestDate": withdraw.timestamp.date().strftime('%d/%m/%Y'),
                "withdrawRequestAmount": withdraw.amount,
                "withdrawRequestMode": withdraw.method,
            },
            message=f"La demande de retrait de {withdraw.amount} F CFA que vous avez fait, a été traité avec succès",
            title="Demande de retrait traitée.",
        )

        notification.send()


@shared_task()
def notify_users_about_end_of_event_highlight_processing(event_highlight_id):
    with transaction.atomic():
        event_highlight = EventHighlighting.objects.select_related('type').get(pk=event_highlight_id)
        owner = User.objects.filter(organizations_own__published_events__uuid=event_highlight.event_id).first()

        notification_type = NotificationType.get_by_name(
            name=NOTIFICATION_TYPES_ENUM.EVENT_HIGHLIGHTING_SUCCESSFUL.value
        )

        notification = Notification.objects.create(
            type=notification_type,
            user=owner,
            target_phone_id="",
            channels=[NOTIFICATION_CHANNELS_ENUM.EMAIL.value, NOTIFICATION_CHANNELS_ENUM.INBOX.value],
            email=owner.email,
            data={"entityId": str(event_highlight.event.pk), "type": "EVENT", "logLevel": "success"},
            extra_data={
                "fullName": owner.get_full_name(),
                "highlightTypeName": event_highlight.type.name,
                "highlightStartDate": event_highlight.start_date.strftime('%d/%m/%Y'),
                "highlightEndDate": event_highlight.end_date.strftime('%d/%m/%Y'),
                "eventDynamicLink": event_highlight.event.get_dynamic_link(),
            },
            message=f"La demande de mise en avant de l' évènement {event_highlight.event.name} a été "
                    f"traité avec succès.",
            title="Mise en avant réussie.",
        )

        notification.send()


@shared_task()
def notify_users_about_end_of_subscription_processing(subscription_id):
    with transaction.atomic():
        subscription = Subscription.objects.select_related('organization').get(pk=subscription_id)
        owner = subscription.organization.owner

        notification_type = NotificationType.get_by_name(
            name=NOTIFICATION_TYPES_ENUM.SUBSCRIPTION_SUCCESSFUL.value
        )

        notification = Notification.objects.create(
            type=notification_type,
            user=owner,
            target_phone_id="",
            channels=[NOTIFICATION_CHANNELS_ENUM.EMAIL.value, NOTIFICATION_CHANNELS_ENUM.INBOX.value],
            email=owner.email,
            data={"entityId": str(subscription.pk), "type": "SUBSCRIPTION", "logLevel": "success"},
            extra_data={
                "fullName": owner.get_full_name(),
                "subscriptionStartDate": subscription.start_date.strftime('%d/%m/%Y'),
                "subscriptionEndDate": subscription.end_date.strftime('%d/%m/%Y'),
            },
            message=f"La demande de souscription d' abonnement de l' organisation {subscription.organization.name}"
                    f" a été traité avec succès.",
            title="Souscription d' abonnement réussie.",
        )

        notification.send()


@shared_task()
def notify_users_about_new_membership_creation(organization_membership_id):
    with transaction.atomic():
        membership = OrganizationMembership.objects \
            .select_related('organization') \
            .select_related('user') \
            .prefetch_related('roles') \
            .get(pk=organization_membership_id)
        
        print("le membre est !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(membership)

        first_role = membership.roles.all().first()
        user_role = first_role.name if first_role else "MEMBER"  # ✅ Valeur par défaut

        # user_role = membership.roles.all().first().name

        notification_type = NotificationType.get_by_name(
            name=NOTIFICATION_TYPES_ENUM.NEW_MEMBERSHIP_CREATION.value
        )

        notification = Notification.objects.create(
            type=notification_type,
            user=membership.user,
            target_phone_id="",
            channels=[NOTIFICATION_CHANNELS_ENUM.EMAIL.value, NOTIFICATION_CHANNELS_ENUM.INBOX.value],
            email=membership.user.email,
            data={"entityId": str(membership.pk), "type": "ORGANIZATION", "logLevel": "success"},
            extra_data={
                "userName": membership.user.get_full_name(),
                "userRole": user_role,
                "organizationName": membership.organization.name,
                # Todo: Generate firebase link
                "organizationLink": ""

            },
            message=f"Vous avez été ajouté à l' organization {membership.organization.name}"
                    f" en tant que {user_role} avec succès.",
            title="Alerte nouvelle organisation.",
        )

        notification.send()


@shared_task()
def one_signal_register_device(device_id):
    device = MobileDevice.objects.get(pk=device_id)
    device.create_device_on_one_signal()


@shared_task()
def one_signal_update_device(device_id):
    device = MobileDevice.objects.get(pk=device_id)
    device.update_device_on_one_signal()


@shared_task()
def one_signal_delete_device(player_id):
    Processor.Registerer.delete_device(player_id=player_id)
