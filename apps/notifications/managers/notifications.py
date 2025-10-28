import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import courier
from django_softdelete.models import SoftDeleteQuerySet, SoftDeleteManager

from apps.notifications.utils.courier_client import CourierClient
from apps.xlib.enums import (
    NOTIFICATION_CHANNELS_ENUM,
    NOTIFICATION_TYPE_TEMPLATE_BY_CHANNEL_ENUM,
)

logger = logging.getLogger(__name__)


def send_courier_message(message):
    client = CourierClient()

    resp = client.send(message=message)
    return resp


class NotificationQuerySet(SoftDeleteQuerySet):
    def bulk_send(self):
        # Initialize Courier
        if self.count() > 0:
            notifications_types = self.values("type__name").distinct()

            # Send template emails by type

            messages = []
            for notification_type in notifications_types:
                related_notifications = (
                    self.all()
                    if len(notifications_types) < 2
                    else self.filter(type__name=notification_type["type__name"])
                )

                target_template = NOTIFICATION_TYPE_TEMPLATE_BY_CHANNEL_ENUM[
                    notification_type["type__name"]
                ].value

                recipients = []
                # Iterate over each instance of the model
                for instance in related_notifications:
                    if any(
                            element in instance.channels
                            for element in [
                                NOTIFICATION_CHANNELS_ENUM.EMAIL.value,
                                NOTIFICATION_CHANNELS_ENUM.PUSH.value,
                                NOTIFICATION_CHANNELS_ENUM.SMS.value,
                                NOTIFICATION_CHANNELS_ENUM.WHATSAPP.value,
                            ]
                    ):
                        _to = {"data": {**instance.extra_data, "data": instance.data}}
                        for channel in instance.channels:
                            match channel:
                                case NOTIFICATION_CHANNELS_ENUM.EMAIL.value:
                                    _to["email"] = instance.target_email
                                case NOTIFICATION_CHANNELS_ENUM.PUSH.value:
                                    _to["user_id"] = instance.target_phone_id
                                case (
                                    NOTIFICATION_CHANNELS_ENUM.SMS.value
                                    | NOTIFICATION_CHANNELS_ENUM.WHATSAPP.value
                                ):
                                    _to["phone_number"] = instance.target_phone
                        recipients.append(_to)

                if len(recipients) > 0:
                    # Creating the message
                    messages.append(
                        courier.TemplateMessage(
                            template=target_template,
                            to=recipients,
                            routing=courier.Routing(
                                method="all", channels=["email", "push", "sms", "inbox"]
                            ),
                        )
                    )
            if len(messages) > 0:
                logger.info("\n\n\n Start Sending Requests to courier \n\n\n")

                with ThreadPoolExecutor(max_workers=20) as executor:

                    futures = {
                        executor.submit(send_courier_message, message)
                        for message in messages
                    }
                    for future in as_completed(futures):
                        try:
                            result = future.result()
                        except Exception as exc:
                            logger.warning(f"Generated an exception: {exc}")
                            raise exc

                logger.info("\n\n\n End Sending Requests to courier \n\n\n")

        return True


class NotificationManager(SoftDeleteManager):
    def get_queryset(self):
        return NotificationQuerySet(self.model, self._db).filter(is_deleted=False)

# client.send(
#     message=courier.TemplateMessage(
#         template="9EDRXFVKYF4947GX0NXD72NPG6ZS",
#         to=[{
#             "firebaseToken": "",
#         }],
#         data={
#             "categoryName": "Sport",
#             "eventImage": "https://api.wuloevents.com/medias/Event/1000137284_1719745920.jpg",
#             "eventLink": "https://api.wuloevents.com/medias/Event/1000137284_1719745920.jpg",
#         },
#     )
# )
#
# resp = client.send(
#     message=courier.TemplateMessage(
#         template="HS0YC15YTV4J3XHVSPSAE50QZ1T8",
#         to=[{
#             "firebaseToken": "",
#         },
#             {"email": "wesleymontcho@gmail.com"}],
#         data={
#             "categoryName": "Sport",
#             "eventImage": "https://api.wuloevents.com/medias/Event/1000137284_1719745920.jpg",
#             "eventLink": "https://api.wuloevents.com/medias/Event/1000137284_1719745920.jpg",
#         },
#         routing=courier.Routing(method="all", channels=["email"]),
#     )
# )
