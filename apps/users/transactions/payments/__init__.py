from dataclasses import dataclass

from apps.users.transactions.payments.fedapay import FedapayService
from apps.xlib.enums import TRANSACTIONS_POSSIBLE_GATEWAYS


@dataclass
class PaymentAdapter:

    def __init__(self, gateway: str):
        self.GATEWAY_NAME: str = gateway

    def get_gateway_instance(self):
        if self.GATEWAY_NAME == TRANSACTIONS_POSSIBLE_GATEWAYS.FEDAPAY.value:
            return FedapayService()

        return NotImplemented()
