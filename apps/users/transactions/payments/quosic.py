import json
import logging
import os

from django.conf import settings
from func_timeout import func_set_timeout, FunctionTimedOut
from requests import Session

logger = logging.getLogger(__name__)
logger.setLevel('INFO')
environment = os.environ.get("DEV_ENV")
QUOSIC_CONFIG = settings.QUOSIC_CONFIG

QUOSIC_CONFIG_USERNAME = QUOSIC_CONFIG.get('QUOSIC_CONFIG_USERNAME')
QUOSIC_CONFIG_PASSWORD = QUOSIC_CONFIG.get('QUOSIC_CONFIG_PASSWORD')
QUOSIC_CONFIG_CLIENT_ID = QUOSIC_CONFIG.get('QUOSIC_CONFIG_CLIENT_ID')
QUOSIC_CONFIG_BASE_URL = QUOSIC_CONFIG.get('QUOSIC_CONFIG_BASE_URL')
QUOSIC_CONFIG_PAYMENT_REQUEST_ENDPOINTS = QUOSIC_CONFIG.get(
    'QUOSIC_CONFIG_PAYMENT_REQUEST_ENDPOINTS')
QUOSIC_CONFIG_REFUND_REQUEST_ENDPOINT = QUOSIC_CONFIG.get(
    'QUOSIC_CONFIG_REFUND_REQUEST_ENDPOINT')
QUOSIC_CONFIG_PAYMENT_STATUS_ENDPOINTS = QUOSIC_CONFIG.get(
    'QUOSIC_CONFIG_PAYMENT_STATUS_ENDPOINTS')

browser = Session()
browser.auth = (QUOSIC_CONFIG_USERNAME, QUOSIC_CONFIG_PASSWORD)
# browser.cert = certifi.where()
browser.verify = False
browser.headers = {'content-type': 'application/json'}


class Payment():
    def __init__(self, msisdn: str, amount: int, firstname: str, lastname: str, transref: str, way: str) -> None:
        self.msisdn = msisdn
        # self.amount = amount
        self.amount = 100
        self.firstname = firstname
        self.lastname = lastname
        self.transref = transref
        self.way = way
        self.clientid = QUOSIC_CONFIG_CLIENT_ID
        self.browser = browser
        self.payment_status = {}

    def send_request(self) -> dict:
        base_url = QUOSIC_CONFIG_BASE_URL
        url = base_url + QUOSIC_CONFIG_PAYMENT_REQUEST_ENDPOINTS[self.way]
        data = json.dumps({
            "msisdn": self.msisdn,
            "amount": self.amount,
            "firstname": self.firstname,
            "lastname": self.lastname,
            "transref": "{}".format(self.transref),
            "clientid": self.clientid
        })
        r = self.browser.post(url, data=data, timeout=30)
        # return HttpResponse(str(resp['transref']))
        if r.status_code == 202:
            resp = r.json()
            response = {
                'status': "success",
                'text': "",
                'code': r.status_code,
                'responsecode': resp['responsecode'],
                'responsemsg': resp['responsemsg'],
                'transref': resp['transref'],
                'comment': resp['comment'],
            }
        elif r.status_code == 401:
            resp = r.json()
            response = {
                'status': "danger",
                'text': 'Unauthorized',
                'code': r.status_code,
                'responsecode': resp['responsecode'],
                'responsemsg': resp['responsemsg'],
                'transref': resp['transref'],
                'comment': resp['comment'],
            }
        else:
            resp = r.json()
            response = {
                'status': "danger",
                'text': 'Failed',
                'code': r.status_code,
                'responsecode': resp['responsecode'],
                'responsemsg': resp['responsemsg'],
                'transref': resp['transref'],
                'comment': resp['comment'],
            }
        return response

    def check_status(self) -> dict:
        base_url = QUOSIC_CONFIG_BASE_URL
        url = base_url + QUOSIC_CONFIG_PAYMENT_STATUS_ENDPOINTS[self.way]
        data = json.dumps({
            "transref": "{}".format(self.transref),
            "clientid": self.clientid,
        })
        r = self.browser.post(url, data=data, timeout=30)
        if r.status_code == 200:
            resp = r.json()
            response = {
                'status': 'success',
                'issue': resp['responsemsg'],
                'transref': resp['transref'],
                'clientid': self.clientid,

                'server_link': f'{url}',
            }
        else:
            response = {
                'status': "danger",
                'text': 'Failed',
                'code': r.status_code,
            }
        return response

    @func_set_timeout(10 * 60)
    def resolve_status(self):
        import time
        while True:
            self.payment_status = self.check_status()
            if self.payment_status['issue'] != 'PENDING':
                return
            time.sleep(7)

    def wait_for_status_to_be_resolve(self):
        try:
            self.resolve_status()
        except FunctionTimedOut:
            print("La transaction n'a jamais été résolu")
        except Exception as exc:
            logger.exception(exc.__str__())
        return self.payment_status
