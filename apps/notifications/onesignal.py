import logging

from django.conf import settings
from requests import Session
from rest_framework.status import is_success

logger = logging.getLogger(__name__)
logger.setLevel('INFO')

ONE_SIGNAL_APP_ID = settings.ONE_SIGNAL_APP_ID
ONE_SIGNAL_USER_KEY = settings.ONE_SIGNAL_USER_KEY
ONE_SIGNAL_REST_API_KEY = settings.ONE_SIGNAL_REST_API_KEY

ONE_SIGNAL_NOTIFICATIONS_URL = "https://onesignal.com/api/v1/notifications"
ONE_SIGNAL_DEVICES_URL = "https://onesignal.com/api/v1/players"

browser = Session()
browser.verify = False
browser.headers = {
    "Accept": "application/json",
    "Authorization":  f"Basic {ONE_SIGNAL_REST_API_KEY or ''}",  
    "Content-Type": "application/json"
}


class Processor:
    devices_types = {
        "ios": 0, "android": 1, "amazon": 2, "windowsphone": 3, "chrome": 5,
        "windows": 6, "safari": 7, "firefox": 8, "macos": 9, "alexa": 10,
        "email": 11, "sms": 14,
    }

    @staticmethod
    def assert_response(response):
        if not is_success(int(response.status_code)):
            raise ValueError(response.json().get(
                'errors', ['Unknow Error'])[0])
        return response.json()

    def __init__(self) -> None:
        pass

    class Notifier:
        def __init__(self, player_ids: list, message: str, title: str, image: str) -> None:
            self.player_ids = player_ids
            self.message = message
            self.title = title
            self.image = image

        def push_about_event(self, data: dict = None) -> dict:
            """
            Create a push notification with the template of Event Notifier
            Response Format: {'id': 'a598cd2c-48ed-496c-a200-a41bf1a19882', 'recipients': 1, 'external_id': None}
            """

            payload = {
                "app_id": ONE_SIGNAL_APP_ID,
                "include_player_ids": self.player_ids,
                "contents": {
                    "en": self.message
                },
                "headings": {
                    "en": self.title
                },
                "big_picture": self.image,
                "huawei_big_picture": self.image,
                "data": data,
                "buttons": [{"id": "see", "text": "Voir", "icon": "ic_eye"}, ]
            }
            response = browser.post(ONE_SIGNAL_NOTIFICATIONS_URL, json=payload)
            return Processor.assert_response(response)

        def push(self) -> dict:
            """
            Create a basic push notification
            Response Format: {'id': 'a598cd2c-48ed-496c-a200-a41bf1a19882', 'recipients': 1, 'external_id': None}

            """

            payload = {
                "app_id": ONE_SIGNAL_APP_ID,
                # "include_external_user_ids": self.external_ids,
                "include_external_user_ids": self.player_ids,
                "contents": {
                    "en": self.message
                },
                "headings": {
                    "en": self.title
                },
                "big_picture": self.image,
                "huawei_big_picture": self.image,
            }
            response = browser.post(ONE_SIGNAL_NOTIFICATIONS_URL, json=payload)
            return Processor.assert_response(response)

    class Registerer:

        def __init__(self, device_type, identifier, first_name, last_name, lat, long) -> None:
            self.device_type = Processor.devices_types.get(device_type, 1)
            self.identifier = identifier
            self.first_name = first_name
            self.last_name = last_name
            self.lat = lat
            self.long = long

        def create_device(self):
            """
            Register a new device on onesignal 
            Response Format: {'success': True, 'id': '8e643d04-046b-4dae-bd88-33db8dc38bd2'}
            """
            payload = {
                "app_id": ONE_SIGNAL_APP_ID,
                "device_type": self.device_type,
                "identifier": self.identifier,
                "tags": {
                    "first_name": self.first_name,
                    "last_name": self.last_name,
                },
                "lat": self.lat,
                "long": self.long,
                "notification_types": 1
            }
            response = browser.post(ONE_SIGNAL_DEVICES_URL, json=payload)
            return Processor.assert_response(response)

        def edit_device(self, player_id: str):
            """
            Edit a device registered on one signal

            Response Format: {'success': True}
            """
            payload = {
                "app_id": ONE_SIGNAL_APP_ID,
                "device_type": self.device_type,
                "identifier": self.identifier,
                "lat": self.lat,
                "long": self.long
            }
            response = browser.put(
                f'{ONE_SIGNAL_DEVICES_URL}/{player_id}', json=payload)
            return Processor.assert_response(response)

        def delete_device(player_id: str):
            response = browser.delete(
                f'{ONE_SIGNAL_DEVICES_URL}/{player_id}', params={"app_id": ONE_SIGNAL_APP_ID})
            return Processor.assert_response(response)
