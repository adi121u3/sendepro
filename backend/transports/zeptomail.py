"""
ZeptoMail (Zoho) transactional API transport.

Auth:  Authorization: Zoho-enczapikey <API_KEY>
Send:  POST https://api.zeptomail.com/v1.1/email
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import requests
import logging

from backend.transports.base import BaseTransport, DeliveryResult
from backend.providers.presets import ZEPTOMAIL_ENDPOINT
from backend.security.credentials import CredentialManager
from backend.utils.deliverability import inject_tracking_pixel, html_to_text

logger = logging.getLogger(__name__)


class ZeptoMailTransport(BaseTransport):
    PROVIDER_NAME = "ZeptoMail API"

    def __init__(self, account_config: Dict[str, Any]):
        super().__init__(account_config)

        self.credential_key = account_config.get("credential_key")
        raw_key = (account_config.get("api_key") or "").strip()

        if not raw_key and self.credential_key:
            try:
                raw_key = (CredentialManager.get_secret(self.credential_key) or "").strip()
            except Exception as exc:
                logger.error("Unable to load ZeptoMail credential: %s", exc)

        prefix = "zoho-enczapikey "
        if raw_key.lower().startswith(prefix):
            raw_key = raw_key[len(prefix) :].strip()

        self.api_key = raw_key
        self.from_name = (account_config.get("from_name") or "").strip()
        self.default_reply_to = (account_config.get("reply_to") or "").strip()

    def _headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Zoho-enczapikey {self.api_key}",
        }

    def _validate_config(self):
        if not self.api_key:
            return False, "ZeptoMail API key is missing. Paste the Send Mail Token from ZeptoMail."
        if len(self.api_key) < 20:
            return False, "ZeptoMail API key looks too short. Copy the full Send Mail Token."
        if not self.from_email:
            return False, "ZeptoMail sender address is missing."
        return True, ""

    @staticmethod
    def _response_text(response: requests.Response) -> str:
        try:
            data = response.json()
            if isinstance(data, dict):
                for key in ("message", "error", "error_message", "errorMessage"):
                    if data.get(key):
                        return str(data[key])
                if isinstance(data.get("error"), dict):
                    inner = data["error"]
                    return str(inner.get("message") or inner)
                details = data.get("details") or data.get("data")
                if details:
                    return str(details)
        except Exception:
            pass
        text = (response.text or "").strip()
        return text[:500] if text else f"HTTP {response.status_code}"

    @staticmethod
    def _build_reply_to(reply_to: Optional[str]) -> Optional[list]:
        if not reply_to:
            return None
        value = reply_to.strip()
        if not value or "@" not in value:
            return None
        name = ""
        address = value
        if "<" in value and ">" in value:
            name = value.split("<")[0].strip().strip('"')
            address = value.split("<")[1].split(">")[0].strip()
        entry: Dict[str, str] = {"address": address}
        if name:
            entry["name"] = name
        return [entry]

    def test_connection(self) -> DeliveryResult:
        valid, error = self._validate_config()
        if not valid:
            return self.failure_result(status="FAILED", message=error, retryable=False)

        probe = {
            "from": {"address": self.from_email, "name": self.from_name or "SendePro"},
            "subject": "connection-test",
            "htmlbody": "<p>connection test</p>",
        }

        try:
            response = requests.post(
                ZEPTOMAIL_ENDPOINT,
                headers=self._headers(),
                json=probe,
                timeout=25,
            )

            if response.status_code in (401, 403):
                return self.failure_result(
                    status="FAILED",
                    message=(
                        "ZeptoMail authentication failed. "
                        "Check the Send Mail Token and verified domain. "
                        f"Detail: {self._response_text(response)}"
                    ),
                    retryable=False,
                )

            if response.status_code in (200, 201, 400, 404, 405, 422):
                return self.success_result(
                    status="CONNECTED",
                    message="ZeptoMail API key accepted. Ready to send from verified domain.",
                )

            return self.failure_result(
                status="FAILED",
                message=f"ZeptoMail API error ({response.status_code}): {self._response_text(response)}",
                retryable=True,
            )
        except requests.Timeout:
            return self.failure_result(
                status="FAILED",
                message="ZeptoMail connection timed out.",
                retryable=True,
            )
        except Exception as exc:
            return self.failure_result(
                status="FAILED",
                message=f"ZeptoMail connection error: {exc}",
                retryable=True,
            )

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str = "",
        reply_to: str = None,
        high_priority: bool = False,
        tracking_id: str = None,
        tracking_domain: str = "",
    ) -> DeliveryResult:
        valid, error = self._validate_config()
        if not valid:
            return self.failure_result(status="FAILED", message=error, retryable=False)

        if not to_email or "@" not in to_email:
            return self.failure_result(
                status="FAILED",
                message="Recipient email is missing or invalid.",
                retryable=False,
            )

        final_html = inject_tracking_pixel(html_body or "", tracking_id, tracking_domain)
        if not text_body:
            text_body = html_to_text(final_html)

        payload: Dict[str, Any] = {
            "from": {
                "address": self.from_email,
                "name": self.from_name or "",
            },
            "to": [
                {
                    "email_address": {
                        "address": to_email,
                    }
                }
            ],
            "subject": subject or "(no subject)",
            "htmlbody": final_html or "<p></p>",
        }

        if text_body:
            payload["textbody"] = text_body

        effective_reply = (reply_to or self.default_reply_to or "").strip()
        reply_payload = self._build_reply_to(effective_reply)
        if reply_payload:
            payload["reply_to"] = reply_payload

        headers = self._headers()
        if high_priority:
            headers["X-Priority"] = "1"

        try:
            response = requests.post(
                ZEPTOMAIL_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code in (200, 201):
                extra = f" Reply-To={effective_reply}" if effective_reply else ""
                return self.success_result(
                    status="SENT",
                    message=f"Email sent successfully via ZeptoMail API.{extra}",
                )

            if response.status_code in (401, 403):
                return self.failure_result(
                    status="FAILED",
                    message=(
                        "ZeptoMail authentication failed while sending. "
                        f"Detail: {self._response_text(response)}"
                    ),
                    retryable=False,
                )

            return self.failure_result(
                status="FAILED",
                message=f"ZeptoMail send error ({response.status_code}): {self._response_text(response)}",
                retryable=response.status_code >= 500,
            )
        except requests.Timeout:
            return self.failure_result(
                status="FAILED",
                message="ZeptoMail send timed out.",
                retryable=True,
            )
        except Exception as exc:
            return self.failure_result(
                status="FAILED",
                message=f"ZeptoMail send exception: {exc}",
                retryable=True,
            )
