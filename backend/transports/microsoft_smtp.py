"""
Microsoft / Outlook SMTP transport using OAuth2 XOAUTH2.

Unlike Microsoft Graph /me/sendMail (which forces the mailbox Azure AD
display name), SMTP lets the client control the RFC 5322 From header:

    From: My Test Name <user@outlook.com>

This matches how desktop clients such as Aerion deliver mail for
Outlook / Microsoft 365 accounts.
"""

from __future__ import annotations

import base64
import logging
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Optional

import requests

from backend.transports.base import DeliveryResult

logger = logging.getLogger(__name__)

# Standard Microsoft 365 / Outlook.com SMTP endpoint
DEFAULT_SMTP_HOST = "smtp.office365.com"
DEFAULT_SMTP_PORT = 587


def _build_xoauth2_string(email: str, access_token: str) -> str:
    """
    Build the SASL XOAUTH2 initial client response.

    Format (RFC-style):
        base64("user=" + email + "\\x01auth=Bearer " + token + "\\x01\\x01")
    """
    auth_string = f"user={email}\x01auth=Bearer {access_token}\x01\x01"
    return base64.b64encode(auth_string.encode("utf-8")).decode("ascii")


def _refresh_microsoft_token(refresh_token: str) -> Optional[str]:
    """
    Exchange a refresh token for a new access token.
    Returns the new access token, or None on failure.
    """
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
    token_url = (
        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    )

    try:
        response = requests.post(
            token_url,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
                # Request both Graph (legacy) and SMTP scopes so existing
                # tokens remain usable after scope expansion.
                "scope": (
                    "https://outlook.office.com/SMTP.Send "
                    "https://graph.microsoft.com/Mail.Send "
                    "https://graph.microsoft.com/User.Read "
                    "offline_access"
                ),
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
    """
    Send mail through Microsoft 365 / Outlook via SMTP + XOAUTH2.

    The compose-time From Name is written into the real MIME From header
    and is therefore visible to recipients (unlike Graph sendMail).
    """

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

    # ---------------------------------------------------------
    # MIME construction — this is where From Name is applied
    # ---------------------------------------------------------

    def _build_message(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str = "",
        reply_to: Optional[str] = None,
        high_priority: bool = False,
        tracking_id: Optional[str] = None,
        tracking_domain: str = "",
    ) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")

        # Critical: use formataddr so the display name is correctly
        # encoded (including non-ASCII) and appears in the From header.
        if self.from_name:
            msg["From"] = formataddr((self.from_name, self.from_email))
        else:
            msg["From"] = self.from_email

        msg["To"] = to_email
        msg["Subject"] = subject or ""

        if reply_to and str(reply_to).strip():
            msg["Reply-To"] = str(reply_to).strip()

        if high_priority:
            msg["X-Priority"] = "1 (Highest)"
            msg["X-MSMail-Priority"] = "High"
            msg["Importance"] = "High"

        final_html = html_body if isinstance(html_body, str) else ""
        if tracking_id and tracking_domain:
            domain = tracking_domain.strip().rstrip("/")
            if domain.lower().startswith("https://"):
                pixel_url = f"{domain}/api/track?id={tracking_id}"
                tracking_tag = (
                    f'<img src="{pixel_url}" alt="" width="1" '
                    f'height="1" style="display:none;"/>'
                )
                if "</body>" in final_html.lower():
                    # Case-insensitive-ish insert before </body>
                    idx = final_html.lower().rfind("</body>")
                    final_html = (
                        final_html[:idx] + tracking_tag + final_html[idx:]
                    )
                else:
                    final_html += tracking_tag

        if text_body and str(text_body).strip():
            msg.attach(MIMEText(str(text_body), "plain", "utf-8"))

        if final_html.strip():
            msg.attach(MIMEText(final_html, "html", "utf-8"))
        elif not (text_body and str(text_body).strip()):
            # Ensure the message has at least an empty body part
            msg.attach(MIMEText("", "plain", "utf-8"))

        return msg

    # ---------------------------------------------------------
    # SMTP + XOAUTH2 delivery
    # ---------------------------------------------------------

    def _smtp_send_once(self, to_email: str, raw_message: bytes) -> None:
        """
        Open an SMTP connection, authenticate with XOAUTH2, and send.

        Raises on failure so the caller can decide whether to refresh
        the token and retry.
        """
        context = ssl.create_default_context()
        server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
        try:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()

            xoauth2 = _build_xoauth2_string(self.from_email, self.access_token)
            # AUTH XOAUTH2 <base64-string>
            code, response = server.docmd("AUTH", "XOAUTH2 " + xoauth2)
            if code != 235:
                # Decode response for a clearer error message
                detail = response.decode("utf-8", errors="replace") if isinstance(response, (bytes, bytearray)) else str(response)
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

        message = self._build_message(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            reply_to=reply_to,
            high_priority=high_priority,
            tracking_id=tracking_id,
            tracking_domain=tracking_domain,
        )
        raw_message = message.as_bytes()

        # Safe debug log — never log tokens
        logger.info(
            "Microsoft SMTP+XOAUTH2 send: "
            "from_email=%s from_name=%r to=%s subject=%r host=%s",
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
                    "Microsoft SMTP accepted email: "
                    "from=%s from_name=%r to=%s",
                    self.from_email,
                    self.from_name,
                    to_email,
                )

                return DeliveryResult(
                    status="SENT",
                    message=(
                        "Email sent successfully via Microsoft SMTP "
                        "(XOAUTH2)."
                    ),
                    retryable=False,
                )

            except smtplib.SMTPAuthenticationError as exc:
                last_error = exc
                logger.warning(
                    "Microsoft SMTP XOAUTH2 auth failed (attempt %s): %s",
                    attempt + 1,
                    exc,
                )

                # Try a single token refresh then retry once
                if attempt == 0 and self.refresh_token:
                    new_token = _refresh_microsoft_token(self.refresh_token)
                    if new_token:
                        self.access_token = new_token
                        continue

                return DeliveryResult(
                    status="FAILED",
                    message=(
                        "Microsoft SMTP authentication failed. "
                        "The OAuth token may be expired or missing the "
                        "SMTP.Send scope. Reconnect the Outlook account "
                        "so it can request SMTP permissions. "
                        f"Detail: {exc}"
                    ),
                    retryable=False,
                )

            except smtplib.SMTPRecipientsRefused as exc:
                logger.error("Microsoft SMTP recipients refused: %s", exc)
                return DeliveryResult(
                    status="FAILED",
                    message=f"Recipient refused by Microsoft SMTP: {exc}",
                    retryable=False,
                )

            except smtplib.SMTPException as exc:
                last_error = exc
                logger.error("Microsoft SMTP error: %s", exc)
                return DeliveryResult(
                    status="FAILED",
                    message=f"Microsoft SMTP error: {exc}",
                    retryable=True,
                )

            except (OSError, TimeoutError) as exc:
                last_error = exc
                logger.error("Microsoft SMTP connection failed: %s", exc)
                return DeliveryResult(
                    status="FAILED",
                    message=(
                        "Could not connect to Microsoft SMTP "
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
            message=(
                "Microsoft SMTP send failed after retry. "
                f"Last error: {last_error}"
            ),
            retryable=True,
        )
