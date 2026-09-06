import base64
import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from typing import Optional

import requests

from backend.transports.base import DeliveryResult
from backend.utils.deliverability import inject_tracking_pixel, html_to_text

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
        # HTTPS-only tracking — never localhost / http / empty domain
        final_html = inject_tracking_pixel(html_body or "", tracking_id, tracking_domain)
        plain = (text_body or "").strip() or html_to_text(final_html) or subject or ""

        message = MIMEMultipart("alternative")
        if self.from_name:
            message["From"] = formataddr((self.from_name, self.from_email))
        else:
            message["From"] = self.from_email
        message["To"] = to_email
        message["Subject"] = subject or ""
        message["Date"] = formatdate(localtime=True)
        try:
            domain = self.from_email.split("@")[-1] if "@" in self.from_email else "localhost"
            message["Message-ID"] = make_msgid(domain=domain)
        except Exception:
            pass

        if reply_to:
            message["Reply-To"] = reply_to

        # High priority is a mild spam signal for cold mail — only when requested
        if high_priority:
            message["X-Priority"] = "1"
            message["Importance"] = "High"

        # Always multipart/alternative with text first, then HTML
        message.attach(MIMEText(plain, "plain", "utf-8"))
        message.attach(MIMEText(final_html or f"<p>{plain}</p>", "html", "utf-8"))

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")

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
