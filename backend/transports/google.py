import base64
import logging
import os
from typing import Optional

import requests

from backend.transports.base import DeliveryResult
from backend.transports.mime_builder import build_outbound_message, message_as_bytes

logger = logging.getLogger(__name__)


class GmailApiTransport:
    SEND_ENDPOINT = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

    def __init__(self, access_token: str, refresh_token: str = "", from_email: str = "", from_name: str = ""):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.from_email = from_email
        self.from_name = from_name

    def _refresh_access_token(self) -> bool:
        if not self.refresh_token:
            return False
        response = requests.post(
            self.TOKEN_ENDPOINT,
            data={
                "client_id": os.getenv("GOOGLE_CLIENT_ID", "").strip(),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", "").strip(),
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=20,
        )
        if not response.ok:
            return False
        token = response.json().get("access_token")
        if not token:
            return False
        self.access_token = token
        return True

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str = "",
        reply_to: Optional[str] = None,
        high_priority: bool = False,
        tracking_id: Optional[str] = None,
        tracking_domain: str = "",
    ) -> DeliveryResult:
        # tracking_id / tracking_domain intentionally ignored — no pixels
        message = build_outbound_message(
            from_email=self.from_email,
            from_name=self.from_name or "",
            to_email=to_email,
            subject=subject or "",
            html_body=html_body or "",
            text_body=text_body or "",
            reply_to=reply_to,
            high_priority=high_priority,
        )
        encoded_message = base64.urlsafe_b64encode(message_as_bytes(message)).decode().rstrip("=")

        for attempt in range(2):
            response = requests.post(
                self.SEND_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                json={"raw": encoded_message},
                timeout=20,
            )
            if response.status_code == 401 and attempt == 0 and self._refresh_access_token():
                continue
            if response.status_code == 401:
                return DeliveryResult(
                    status="FAILED",
                    message="Google OAuth access expired. Reconnect the Gmail account.",
                    retryable=False,
                )
            if not response.ok:
                detail = response.text[:500] or response.reason
                logger.error("Gmail API send failed: %s", detail)
                return DeliveryResult(
                    status="FAILED",
                    message=f"Gmail API send failed: {detail}",
                    retryable=True,
                )
            return DeliveryResult(status="SENT", message="Email sent successfully via Gmail API.")

        return DeliveryResult(
            status="FAILED",
            message="Google OAuth access expired. Reconnect the Gmail account.",
            retryable=False,
        )
