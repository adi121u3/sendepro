from pathlib import Path
from typing import Dict, Any, List
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
        self.api_key = account_config.get("api_key") or ""
        
        if not self.api_key and self.credential_key:
            try:
                self.api_key = CredentialManager.get_secret(self.credential_key) or ""
            except Exception as exc:
                logger.error(f"Unable to load ZeptoMail credential: {exc}")

    def _headers(self):
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Zoho-enczapikey {self.api_key}",
        }

    def _validate_config(self):
        if not self.api_key:
            return False, "ZeptoMail API key is missing."
        if not self.from_email:
            return False, "ZeptoMail sender address is missing."
        return True, ""

    @staticmethod
    def _response_text(response: requests.Response) -> str:
        try:
            data = response.json()
            if isinstance(data, dict):
                message = data.get("message") or data.get("error") or data.get("error_message")
                if message:
                    return str(message)
        except Exception:
            pass
        return response.text.strip()

    def test_connection(self) -> DeliveryResult:
        valid, error = self._validate_config()
        if not valid:
            return self.failure_result(status="FAILED", message=error, retryable=False)

        try:
            response = requests.get(
                ZEPTOMAIL_ENDPOINT,
                headers=self._headers(),
                timeout=20,
            )
            if response.status_code in (200, 201):
                return self.success_result(
                    status="CONNECTED",
                    message="ZeptoMail API connection successful."
                )
            if response.status_code in (401, 403):
                return self.failure_result(
                    status="FAILED",
                    message=f"Authentication failed: {self._response_text(response)}",
                    retryable=False,
                )
            return self.failure_result(
                status="FAILED",
                message=f"ZeptoMail API error ({response.status_code}): {self._response_text(response)}",
                retryable=True,
            )
        except Exception as exc:
            return self.failure_result(
                status="FAILED",
                message=f"Connection error: {str(exc)}",
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
        tracking_domain: str = ""
    ) -> DeliveryResult:
        valid, error = self._validate_config()
        if not valid:
            return self.failure_result(status="FAILED", message=error, retryable=False)

        final_html = html_body
        if tracking_id:
            pixel_url = f"{tracking_domain}/api/track?id={tracking_id}"
            tracking_tag = f'<img src="{pixel_url}" alt="" width="1" height="1" style="display:none;"/>'
            if "</body>" in final_html:
                final_html = final_html.replace("</body>", f"{tracking_tag}</body>")
            else:
                final_html += tracking_tag

        payload = {
            "from": {"address": self.from_email, "name": self.account_config.get("from_name", "")},
            "to": [{"email_address": {"address": to_email}}],
            "subject": subject,
            "htmlbody": final_html,
        }
        if text_body:
            payload["textbody"] = text_body
        if reply_to:
            payload["reply_to"] = {"address": reply_to}
        
        headers = self._headers()
        if high_priority:
            headers["X-Priority"] = "1 (Highest)"
            headers["Importance"] = "High"

        try:
            response = requests.post(
                ZEPTOMAIL_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=30,
            )
            if response.status_code in (200, 201):
                return self.success_result(status="SENT", message="Email sent successfully via ZeptoMail API with High Priority & Read Receipt.")
            else:
                return self.failure_result(
                    status="FAILED",
                    message=f"ZeptoMail send error ({response.status_code}): {self._response_text(response)}",
                    retryable=True
                )
        except Exception as exc:
            return self.failure_result(
                status="FAILED",
                message=f"ZeptoMail send exception: {str(exc)}",
                retryable=True
            )
