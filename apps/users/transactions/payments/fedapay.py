import json
from dataclasses import dataclass
from typing import Optional

from rest_framework.exceptions import APIException

from apps.users.transactions.utils.fedapay import FedapayUtil, PaymentItem
from apps.xlib.enums import FEDAPAY_ENDPOINT_ENUM


@dataclass
class FedapayService:
    fedapay_util = FedapayUtil()
    _client = fedapay_util.get_client()

    def create_payment(
            self, amount: int, firstname: str, lastname: str, email: Optional[str], transaction_id: str = "",
            is_dev_mode=False,
    ) -> PaymentItem:

        payload = {
            "description": "Transaction sur WuloEvents",
            "amount": amount,
            # "callback_url": f"https://api.wuloevents.com/v1/transactions/{transaction_id}/payment-callback",
            # "callback_url": f"https://8660-41-138-89-241.ngrok-free.app/v1/transactions/payment-callbacks",
            "currency": {"iso": "XOF"},
            "customer": {
                "firstname": firstname,
                "lastname": lastname,
                "email": email,
            },
        }
        if is_dev_mode:
            payload["customer"]["phone_number"] = {
                "number": "+22997808080",
                "country": "bj"
            }
        endpoint = self.fedapay_util.get_url(FEDAPAY_ENDPOINT_ENUM.CREATE_TRANSACTION.value)
        try:
            r = self._client.post(
                endpoint,
                data=json.dumps(payload),
                timeout=30,
            )
            response = r.json()
            return PaymentItem.from_data(response.get("v1/transaction"))
        except Exception as e:
            raise APIException("Payment creation failed") from e

    def send_request(self, amount: int, firstname: str, lastname: str, email: str, transaction_id: str) -> PaymentItem:
        payment = self.create_payment(amount, firstname, lastname, email, transaction_id, is_dev_mode=False)
        data = self.generate_payment_link(payment.id)
        payment.payment_url = data.get("url")
        return payment

    def generate_payment_link(self, transaction_id: str):
        try:
            endpoint = self.fedapay_util.get_url(
                FEDAPAY_ENDPOINT_ENUM.GET_TRANSACTION_LINK.value.replace("{id}", str(transaction_id)))
            r = self._client.post(
                endpoint,
            )
            response = r.json()
            return response
        except Exception as e:
            raise APIException("Payment creation failed") from e

    def check_status(self, transaction_id: str):
        try:
            endpoint = self.fedapay_util.get_url(
                FEDAPAY_ENDPOINT_ENUM.STATUS_TRANSACTION.value.replace("{id}", str(transaction_id)))
            response = self._client.get(endpoint)
            return response.json().get("v1/transaction").get("status")

        except Exception as e:
            raise ValueError(
                "Erreur lors de l' envoi de la demande de verification du statut"
            ) from e
