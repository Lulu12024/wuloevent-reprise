import http.client
import json

from urllib.parse import urlencode


class API:
    def __init__(self, host: str, headers: dict) -> None:
        self.host = host
        self.headers = headers
        self.connection = None

    def initialize(self):
        if self.connection is None:
            self.connection = http.client.HTTPSConnection(self.host)

    def perform_request(self, method: str, route: str, params=None, headers: dict = None) -> dict:
        if params is None:
            params = {}
        if headers is None:
            headers = self.headers
        if self.connection is None:
            raise AssertionError('API not initialized yet')

        endpoint = f"{route}?{urlencode(params)}"

        self.connection.request(method, endpoint, headers=headers)

        res = self.connection.getresponse()
        data = res.read()
        return dict(json.loads(data.decode("utf-8")))
