"""
Microsoft / Outlook SMTP + XOAUTH2 (Aerion-style delivery).

Graph /me/sendMail forces the Azure AD mailbox display name.
SMTP lets us set the real RFC 5322 From header:

    From: My Test Name <user@outlook.com>
"""

from __future__ import annotations

import base64
import logging
import os
import smtplib
import ssl
from typing import Optional

import requests

from backend.transports.base import DeliveryResult
from backend.transports.mime_builder import build_outbound_message, message_as_bytes

logger = logging.getLogger(__name__)

DEFAULT_SMTP_HOST = "smtp.office365.com"
DEFAULT_SMTP_PORT = 587

# Must match backend/api/oauth.py — do not mix outlook.office.com with graph.microsoft.com
MICROSOFT_SMTP_SCOPES = "openid offline_access https://outlook.office.com/SMTP.Send"


def _build_xoauth2_string(email: str, access_token: str) -> str:
    auth_string = f"user={email}\x01auth=Bearer {access_token}\x01\x01"
    return base64.b64encode(auth_string.encode("utf-8")).decode("ascii")


def _refresh_microsoft_token(refresh_token: str) -> Optional[str]:
    if not refresh_token:
        return None

    client_id = os.getenv("MICROSOFT_CLIENT_ID", "").strip()
    client_secret = os.getenv("MICROSOFT_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        logger.warning(
            "Cannot refresh Microsoft token: MICROSOFT_CLIENT_ID or "
            "MICROSOFT_CLIENT_SECRET is not configured."
        )
        return None

    tenant_id = os.getenv("MICROSOFT_TENANT_ID", "common").strip() or "common"
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    try:
        response = requests.post(
            token_url,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
                "scope": MICROSOFT_SMTP_SCOPES,
            },
            timeout=20,
        )
    except requests.RequestException as exc:
        logger.error("Microsoft token refresh request failed: %s", exc)
        return None

    if not response.ok:
        logger.warning(
            "Microsoft token refresh failed: HTTP %s — %s",
            response.status_code,
            (response.text or "")[:300],
        )
        return None

    new_token = response.json().get("access_token")
    if not new_token:
        return None

    logger.info("Microsoft access token refreshed successfully for SMTP.")
    return new_token


class MicrosoftSmtpTransport:
    def __init__(
        self,
        access_token: str,
        from_email: str,
        from_name: str = "",
        refresh_token: str = "",
        smtp_host: str = DEFAULT_SMTP_HOST,
        smtp_port: int = DEFAULT_SMTP_PORT,
    ):
        self.access_token = (access_token or "").strip()
        self.refresh_token = (refresh_token or "").strip()
        self.from_email = (from_email or "").strip()
        self.from_name = (from_name or "").strip()
        self.smtp_host = (smtp_host or DEFAULT_SMTP_HOST).strip()
        self.smtp_port = int(smtp_port or DEFAULT_SMTP_PORT)

    def _smtp_send_once(self, to_email: str, raw_message: bytes) -> None:
        context = ssl.create_default_context()
        server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
        try:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()

            xoauth2 = _build_xoauth2_string(self.from_email, self.access_token)
            code, response = server.docmd("AUTH", "XOAUTH2 " + xoauth2)
            if code != 235:
                detail = (
                    response.decode("utf-8", errors="replace")
                    if isinstance(response, (bytes, bytearray))
                    else str(response)
                )
                raise smtplib.SMTPAuthenticationError(code, detail)

            server.sendmail(self.from_email, [to_email], raw_message)
        finally:
            try:
                server.quit()
            except Exception:
                try:
                    server.close()
                except Exception:
                    pass

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
        if not self.access_token:
            return DeliveryResult(
                status="FAILED",
                message=(
                    "Microsoft OAuth access token is missing or expired. "
                    "Reconnect the Outlook account."
                ),
                retryable=False,
            )

        if not self.from_email:
            return DeliveryResult(
                status="FAILED",
                message="Microsoft sender email address is missing.",
                retryable=False,
            )

        if not to_email or not str(to_email).strip():
            return DeliveryResult(
                status="FAILED",
                message="Recipient email address is required.",
                retryable=False,
            )

        to_email = str(to_email).strip()

        message = build_outbound_message(
            from_email=self.from_email,
            from_name=self.from_name,
            to_email=to_email,
            subject=subject or "",
            html_body=html_body or "",
            text_body=text_body or "",
            reply_to=reply_to,
            high_priority=high_priority,
        )
        raw_message = message_as_bytes(message)

        logger.info(
            "Microsoft SMTP+XOAUTH2 send: from_email=%s from_name=%r to=%s subject=%r host=%s",
            self.from_email,
            self.from_name,
            to_email,
            subject,
            self.smtp_host,
        )

        last_error: Optional[Exception] = None

        for attempt in range(2):
            try:
                self._smtp_send_once(to_email, raw_message)
                logger.info(
                    "Microsoft SMTP accepted email: from=%s from_name=%r to=%s",
                    self.from_email,
                    self.from_name,
                    to_email,
                )
                return DeliveryResult(
                    status="SENT",
                    message="Email sent successfully via Microsoft SMTP (XOAUTH2).",
                    retryable=False,
                )

            except smtplib.SMTPAuthenticationError as exc:
                last_error = exc
                logger.warning(
                    "Microsoft SMTP XOAUTH2 auth failed (attempt %s): %s",
                    attempt + 1,
                    exc,
                )
                if attempt == 0 and self.refresh_token:
                    new_token = _refresh_microsoft_token(self.refresh_token)
                    if new_token:
                        self.access_token = new_token
                        continue
                return DeliveryResult(
                    status="FAILED",
                    message=(
                        "Microsoft SMTP authentication failed. "
                        "Reconnect the Outlook account for SMTP.Send scope. "
                        f"Detail: {exc}"
                    ),
                    retryable=False,
                )

            except smtplib.SMTPRecipientsRefused as exc:
                return DeliveryResult(
                    status="FAILED",
                    message=f"Recipient refused by Microsoft SMTP: {exc}",
                    retryable=False,
                )

            except smtplib.SMTPException as exc:
                return DeliveryResult(
                    status="FAILED",
                    message=f"Microsoft SMTP error: {exc}",
                    retryable=True,
                )

            except (OSError, TimeoutError) as exc:
                return DeliveryResult(
                    status="FAILED",
                    message=(
                        f"Could not connect to Microsoft SMTP "
                        f"({self.smtp_host}:{self.smtp_port}): {exc}"
                    ),
                    retryable=True,
                )

            except Exception as exc:
                last_error = exc
                logger.exception("Unexpected Microsoft SMTP failure")
                return DeliveryResult(
                    status="FAILED",
                    message=f"Microsoft SMTP send failed: {exc}",
                    retryable=True,
                )

        return DeliveryResult(
            status="FAILED",
            message=f"Microsoft SMTP send failed after retry. Last error: {last_error}",
            retryable=True,
        )
