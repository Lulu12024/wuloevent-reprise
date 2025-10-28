import json
import logging
from dataclasses import dataclass

from rest_framework.exceptions import APIException
from rest_framework.status import is_success

from apps.users.transactions.utils.fedapay import FedapayUtil, PaymentItem
from apps.xlib.enums import FEDAPAY_ENDPOINT_ENUM

logger = logging.getLogger(__name__)


@dataclass
class FedapayService:
    fedapay_util = FedapayUtil()
    _client = fedapay_util.get_client()

    def initialize(
            self,
            amount: int,
            withdraw_mode: str,
            firstname: str,
            lastname: str,
            email: str,
            phone: str,
    ) -> PaymentItem:
        payload = {
            "amount": amount,
            "currency": {"iso": "XOF"},
            "mode": withdraw_mode,
            "customer": {
                "firstname": firstname,
                "lastname": lastname,
                "email": email,
                "phone_number": {"number": phone, "country": "bj"},
            },
        }

        endpoint = self.fedapay_util.get_url(FEDAPAY_ENDPOINT_ENUM.CREATION_PAYOUT.value)

        r = self._client.post(endpoint, data=json.dumps(payload), timeout=30)
        response = r.json()

        error = "response_code" in response and response.get("response_code") != "00" or not response.get("success",
                                                                                                          True)
        if not is_success(r.status_code) or error:
            raise APIException("Withdraw initialization failed")

        return PaymentItem.from_data(response.get("v1/payout", {}))

    def disburse(self, transaction_id: str = None):
        payload = {
            "payouts": [
                {"id": transaction_id},
            ]
        }
        endpoint = self.fedapay_util.get_url(FEDAPAY_ENDPOINT_ENUM.START_PAYOUT.value)

        r = self._client.put(endpoint, data=json.dumps(payload), timeout=30)
        response = r.json()

        logger.info(response)

        disburse_response = response.get("v1/payouts")[0]

        logger.info(disburse_response)

        error = disburse_response.get("status", "failed") == "failed"

        if not is_success(r.status_code) or error:
            raise APIException("Withdraw disburse failed")

        return disburse_response
