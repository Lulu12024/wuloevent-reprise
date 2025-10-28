from dataclasses import dataclass

from apps.users.transactions.withdraws.fedapay import FedapayService
from apps.xlib.enums import TRANSACTIONS_POSSIBLE_GATEWAYS


@dataclass
class WithdrawAdapter:
    GATEWAY: str = TRANSACTIONS_POSSIBLE_GATEWAYS.FEDAPAY.value

    def get_gateway_instance(self):
        if self.GATEWAY == TRANSACTIONS_POSSIBLE_GATEWAYS.FEDAPAY.value:
            return FedapayService()

        return NotImplemented()
