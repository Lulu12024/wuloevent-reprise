from dataclasses import dataclass

from requests import Session

from apps.xlib.enums import FEDAPAY_ENDPOINT_ENUM


@dataclass
class FedapayUtil:
    base_url = FEDAPAY_ENDPOINT_ENUM.BASE_URL.value

    def get_client(self):
        browser = Session()
        browser.verify = False
        browser.headers = {
            "content-type": "application/json",
            "Authorization": f"Bearer {FEDAPAY_ENDPOINT_ENUM.PRIVATE_KEY.value}",
        }
        return browser

    def get_url(self, endpoint: str):
        return f"{self.base_url}{endpoint}"


@dataclass
class PaymentItem:
    id: str
    payment_url: str
    reference: str

    @classmethod
    def from_data(cls, data: dict):
        return cls(
            data.get("id"),
            data.get("url"),
            data.get("reference"),
        )

    def to_json(self):
        return {
            "id": self.id,
            "payment_url": self.payment_url,
            "reference": self.reference,
        }
