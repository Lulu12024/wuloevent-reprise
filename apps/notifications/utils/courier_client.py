from courier.client import Courier
from django.conf import settings

from helpers.singleton import Singleton


class CourierClient(Courier, metaclass=Singleton):

    def __init__(self):
        super(CourierClient, self).__init__(
            authorization_token=settings.COURIER_AUTH_TOKEN
        )
