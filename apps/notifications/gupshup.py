"""
Created on November 5, 2025
@author:
    Beaudelaire LAHOUME, alias root-lr
"""
import json
import logging
from typing import Dict, List, Optional, Union
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class GupshupError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, payload: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}

class GupshupWhatsAppClient:
    """
    Client Gupshup WhatsApp Business API.

    Réfs :
    - Session messages: POST /wa/api/v1/msg (text|image|document|audio|video|...)
    - Template messages: POST /wa/api/v1/template/msg
    - Opt-in: POST /wa/api/v1/app/opt/in
    """
    def __init__(
        self,
        api_key: str = None,
        app_name: str = None,
        source: str = None,
        base_url: str = None,
        timeout: int = None,
    ):
        self.api_key = api_key or settings.GUPSHUP_API_KEY
        self.app_name = app_name or settings.GUPSHUP_APP_NAME
        self.source = source or settings.GUPSHUP_WHATSAPP_SOURCE
        self.base_url = (base_url or settings.GUPSHUP_API_BASE).rstrip("/")
        self.timeout = timeout or getattr(settings, "GUPSHUP_TIMEOUT", 15)

        if not all([self.api_key, self.app_name, self.source]):
            raise ValueError("Gupshup config missing (api_key/app_name/source)")

        self._headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "apikey": self.api_key,
        }

    # ---------- helpers ----------
    def _post_form(self, url: str, data: Dict) -> dict:
        try:
            resp = requests.post(url, headers=self._headers, data=data, timeout=self.timeout)
        except requests.RequestException as exc:
            logger.exception("Gupshup request error")
            raise GupshupError(f"Network error: {exc}") from exc

        if resp.status_code >= 400:
            raise GupshupError(f"HTTP {resp.status_code}: {resp.text}", status_code=resp.status_code)

        try:
            payload = resp.json()
        except ValueError:
            payload = {"raw": resp.text}

        if isinstance(payload, dict) and payload.get("status") in {"fail", "failed", "error"}:
            raise GupshupError(payload.get("message", "Gupshup error"), payload=payload)

        return payload

    def _session_endpoint(self) -> str:
        return f"{self.base_url}/wa/api/v1/msg"

    def _template_endpoint(self) -> str:
        return f"{self.base_url}/wa/api/v1/template/msg"

    def _optin_endpoint(self) -> str:
        return f"{self.base_url}/wa/api/v1/app/opt/in"

    # ---------- core API ----------
    def send_text(self, to: str, text: str, **kwargs) -> dict:
        """
        Session text message
        Docs: POST /wa/api/v1/msg with message={"type":"text","text":"..."}.
        """
        message = {"type": "text", "text": text}
        data = {
            "channel": "whatsapp",
            "source": self.source,
            "destination": to,
            "src.name": self.app_name,
            "message": json.dumps(message),
        }
        data.update(kwargs or {})
        return self._post_form(self._session_endpoint(), data)

    def send_media_url(self, to: str, media_type: str, url: str, caption: Optional[str] = None, **kwargs) -> dict:
        """
        Session media via URL. media_type in {"image","document","audio","video"}.
        Docs: POST /wa/api/v1/msg with message={"type": <media_type>, "url": "...", "caption": "..."}.
        """
        if media_type not in {"image", "document", "audio", "video"}:
            raise ValueError("Invalid media_type")

        message = {"type": media_type, "url": url}
        if caption:
            message["caption"] = caption

        data = {
            "channel": "whatsapp",
            "source": self.source,
            "destination": to,
            "src.name": self.app_name,
            "message": json.dumps(message),
        }
        data.update(kwargs or {})
        return self._post_form(self._session_endpoint(), data)

    def send_location(self, to: str, latitude: float, longitude: float, name: str = "", address: str = "", **kwargs) -> dict:
        """
        Session location message.
        message={"type":"location","longitude":...,"latitude":...,"name":"...","address":"..."}
        """
        message = {
            "type": "location",
            "longitude": longitude,
            "latitude": latitude,
        }
        if name:
            message["name"] = name
        if address:
            message["address"] = address

        data = {
            "channel": "whatsapp",
            "source": self.source,
            "destination": to,
            "src.name": self.app_name,
            "message": json.dumps(message),
        }
        data.update(kwargs or {})
        return self._post_form(self._session_endpoint(), data)

    def send_quick_replies(self, to: str, title: str, options: List[str], **kwargs) -> dict:
        """
        Session quick replies
        message={"type":"quick_reply","msg":"<title>","options":[{"type":"text","title":"..."}]}
        """
        msg_opts = [{"type": "text", "title": opt} for opt in options]
        message = {"type": "quick_reply", "msg": title, "options": msg_opts}
        data = {
            "channel": "whatsapp",
            "source": self.source,
            "destination": to,
            "src.name": self.app_name,
            "message": json.dumps(message),
        }
        data.update(kwargs or {})
        return self._post_form(self._session_endpoint(), data)

    def send_template(self, to: str, template_name: str, language: str, params: List[Union[str, dict]] = None, **kwargs) -> dict:
        """
        Template (HSM) message.
        Docs: POST /wa/api/v1/template/msg
        payload: template={"name":"<name>","language":"<code>","params":[...]}
        """
        template = {"name": template_name, "language": language}
        if params:
            template["params"] = params

        data = {
            "channel": "whatsapp",
            "source": self.source,
            "destination": to,
            "src.name": self.app_name,
            "template": json.dumps(template),
        }
        data.update(kwargs or {})
        return self._post_form(self._template_endpoint(), data)

    def opt_in(self, phone_e164: str) -> dict:
        """
        Opt-in WhatsApp pour un utilisateur.
        Docs: POST /wa/api/v1/app/opt/in with user, channel=whatsapp, appname.
        """
        data = {
            "user": phone_e164,
            "channel": "whatsapp",
            "appname": self.app_name,
        }
        return self._post_form(self._optin_endpoint(), data)
