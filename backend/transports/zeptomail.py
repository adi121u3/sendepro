"""
ZeptoMail (Zoho) transactional API transport.

Auth header format:
  Authorization: Zoho-enczapikey <API_KEY>

Send endpoint:
  POST https://api.zeptomail.com/v1.1/email
"""

from __future__ import annotations

from typing import Dict, Any
import requests
import logging

from backend.transports.base import BaseTransport, DeliveryResult
from backend.providers.presets import ZEPTOMAIL_ENDPOINT
from backend.security.credentials import CredentialManager

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

        # Accept keys pasted with or without the Zoho prefix.
        prefix = "zoho-enczapikey "
        if raw_key.lower().startswith(prefix):
            raw_key = raw_key[len(prefix) :].strip()

        self.api_key = raw_key
        self.from_name = (account_config.get("from_name") or "").strip()

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
                # ZeptoMail error shapes vary
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

    def test_connection(self) -> DeliveryResult:
        """
        ZeptoMail does not expose a dedicated ping endpoint.

        Strategy:
          1) Validate key presence/format
          2) POST a deliberately invalid minimal payload
             - 401/403 => bad API key
             - 400 with validation error => key is accepted (connected)
             - 200 is unexpected but treated as connected
        """
        valid, error = self._validate_config()
        if not valid:
            return self.failure_result(status="FAILED", message=error, retryable=False)

        # Minimal invalid payload: missing required 'to' causes 400 if auth OK.
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
                        "Check the Send Mail Token and that the sender domain is verified. "
                        f"Detail: {self._response_text(response)}"
                    ),
                    retryable=False,
                )

            if response.status_code in (200, 201):
                return self.success_result(
                    status="CONNECTED",
                    message="ZeptoMail API connection successful.",
                )

            # 400 = request validated enough that auth worked
            if response.status_code == 400:
                return self.success_result(
                    status="CONNECTED",
                    message=(
                        "ZeptoMail API key accepted (auth OK). "
                        "Ready to send from verified domain."
                    ),
                )

            # Method quirks / other responses
            if response.status_code in (404, 405, 422):
                return self.success_result(
                    status="CONNECTED",
                    message=f"ZeptoMail API reachable (HTTP {response.status_code}). Auth headers accepted.",
                )

            return self.failure_result(
                status="FAILED",
                message=f"ZeptoMail API error ({response.status_code}): {self._response_text(response)}",
                retryable=True,
            )
        except requests.Timeout:
            return self.failure_result(
                status="FAILED",
                message="ZeptoMail connection timed out. Check outbound HTTPS access to api.zeptomail.com.",
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

        final_html = html_body or ""
        if tracking_id and tracking_domain:
            pixel_url = f"{tracking_domain.rstrip('/')}/api/track?id={tracking_id}"
            tracking_tag = (
                f'<img src="{pixel_url}" alt="" width="1" height="1" style="display:none;"/>'
            )
            lower = final_html.lower()
            if "</body>" in lower:
                idx = lower.rfind("</body>")
                final_html = final_html[:idx] + tracking_tag + final_html[idx:]
            else:
                final_html += tracking_tag

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

        if reply_to:
            payload["reply_to"] = [{"address": reply_to}]

        headers = self._headers()
        if high_priority:
            # ZeptoMail does not document X-Priority on API; keep as optional client hint only.
            headers["X-Priority"] = "1"

        try:
            response = requests.post(
                ZEPTOMAIL_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code in (200, 201):
                return self.success_result(
                    status="SENT",
                    message="Email sent successfully via ZeptoMail API.",
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
