"""
Bell / Sympatico SMTP transport.

Bell officially supports:
  - Host: smtphm.sympatico.ca  (primary)
  - Host: smtp.sympatico.ca    (legacy alias)
  - Port 587 + STARTTLS
  - Port 465 + SSL/TLS

Username must be the full email address.
Password is the Bell webmail password (or app password if enabled).

This transport tries the preferred host/port first, then falls back to
alternate combinations so intermittent network / endpoint issues are
less likely to block the user.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple
import smtplib
import ssl
import logging
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from backend.transports.base import BaseTransport, DeliveryResult
from backend.security.credentials import CredentialManager

logger = logging.getLogger(__name__)

# Preferred order: modern STARTTLS first, then SSL, then legacy host.
BELL_ENDPOINTS: List[Tuple[str, int, str]] = [
    ("smtphm.sympatico.ca", 587, "starttls"),
    ("smtphm.sympatico.ca", 465, "ssl"),
    ("smtp.sympatico.ca", 587, "starttls"),
    ("smtp.sympatico.ca", 465, "ssl"),
]

DEFAULT_TIMEOUT = 25


class BellSympaticoTransport(BaseTransport):
    PROVIDER_NAME = "Bell Sympatico"

    def __init__(self, account_config: Dict[str, Any]):
        super().__init__(account_config)

        self.credential_key = account_config.get("credential_key")
        self.password = (account_config.get("password") or "").strip()

        if not self.password and self.credential_key:
            try:
                self.password = CredentialManager.get_secret(self.credential_key) or ""
            except Exception as exc:
                logger.error("Unable to load Bell Sympatico credential: %s", exc)

        # Prefer explicit account settings; normalize later for fallbacks.
        configured_host = (account_config.get("host") or "").strip() or "smtphm.sympatico.ca"
        configured_port = int(account_config.get("port") or 587)
        configured_security = (account_config.get("security") or "starttls").strip().lower()

        if configured_security in {"tls", "start_tls"}:
            configured_security = "starttls"
        if configured_security in {"ssl/tls", "smtps"}:
            configured_security = "ssl"

        self.host = configured_host
        self.port = configured_port
        self.security = configured_security

        # Username must be the full email for Bell.
        username = (account_config.get("username") or self.from_email or "").strip()
        self.username = username

        self.from_name = (account_config.get("from_name") or "").strip()

    def _validate_config(self):
        if not self.username:
            return False, "Bell Sympatico email/username is missing. Use the full email address."
        if "@" not in self.username:
            return False, "Bell Sympatico username must be the full email address (e.g. name@bell.net)."
        if not self.password:
            return False, "Bell Sympatico password is missing. Re-save the account password and try again."
        return True, ""

    @staticmethod
    def _error_message(exc: Exception) -> str:
        if isinstance(exc, smtplib.SMTPAuthenticationError):
            detail = ""
            try:
                raw = getattr(exc, "smtp_error", b"") or b""
                detail = raw.decode("utf-8", errors="ignore") if isinstance(raw, (bytes, bytearray)) else str(raw)
            except Exception:
                detail = str(exc)
            return (
                "Bell rejected the username or password. "
                "Confirm you can sign in to Bell webmail with the same full email + password. "
                f"Server said: {detail or 'authentication failed'}"
            )

        text = str(exc)
        lower = text.lower()

        if "timed out" in lower or "timeout" in lower or "read operation timed out" in lower:
            return (
                "Connection timed out reaching Bell SMTP. "
                "This is usually a network/firewall issue or the wrong host/port. "
                "We will also try alternate Bell endpoints automatically. "
                f"Detail: {text}"
            )

        if "connection unexpectedly closed" in lower:
            return (
                "Bell closed the connection before login finished. "
                "Often caused by wrong security mode (STARTTLS vs SSL) or blocked port. "
                f"Detail: {text}"
            )

        if isinstance(exc, (socket.gaierror, socket.herror)):
            return f"DNS/network error resolving Bell SMTP host: {text}"

        if isinstance(exc, ConnectionRefusedError):
            return f"Bell SMTP refused the connection (wrong port or blocked): {text}"

        return text

    def _connect(self, host: str, port: int, security: str, timeout: int = DEFAULT_TIMEOUT):
        security = (security or "starttls").lower()
        if security == "ssl" or port == 465:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, timeout=timeout, context=context)
            server.ehlo()
            return server

        server = smtplib.SMTP(host, port, timeout=timeout)
        server.ehlo()
        if security == "starttls" or port == 587:
            context = ssl.create_default_context()
            server.starttls(context=context)
            server.ehlo()
        return server

    def _endpoint_list(self) -> List[Tuple[str, int, str]]:
        """Preferred configured endpoint first, then known Bell fallbacks (deduped)."""
        preferred = (self.host, self.port, self.security)
        seen = set()
        ordered: List[Tuple[str, int, str]] = []

        for item in [preferred, *BELL_ENDPOINTS]:
            key = (item[0].lower(), int(item[1]), item[2].lower())
            if key in seen:
                continue
            seen.add(key)
            ordered.append((item[0], int(item[1]), item[2].lower()))
        return ordered

    def _try_login_across_endpoints(self) -> Tuple[Optional[smtplib.SMTP], Optional[str], List[str]]:
        """
        Attempt login across Bell endpoints.
        Returns (connected_server_or_None, success_endpoint_label, error_trail).
        Caller owns quit() on success.
        """
        errors: List[str] = []
        auth_rejected = False

        for host, port, security in self._endpoint_list():
            label = f"{host}:{port}/{security}"
            try:
                logger.info("Bell SMTP trying %s as %s", label, self.username)
                server = self._connect(host, port, security)
                server.login(self.username, self.password)
                logger.info("Bell SMTP login OK via %s", label)
                return server, label, errors
            except smtplib.SMTPAuthenticationError as exc:
                auth_rejected = True
                msg = self._error_message(exc)
                errors.append(f"{label}: {msg}")
                logger.error("Bell SMTP auth rejected on %s: %s", label, exc)
                # Auth failure is credential-related; still try other endpoints once,
                # but prefer reporting auth clearly if all fail.
            except Exception as exc:
                msg = self._error_message(exc)
                errors.append(f"{label}: {msg}")
                logger.error("Bell SMTP failed on %s: %s", label, exc)

        if auth_rejected:
            errors.insert(
                0,
                "Bell rejected credentials on one or more endpoints. "
                "Double-check full email + webmail password (or app password).",
            )
        return None, None, errors

    def test_connection(self) -> DeliveryResult:
        valid, error = self._validate_config()
        if not valid:
            return self.failure_result(status="FAILED", message=error, retryable=False)

        server, label, errors = self._try_login_across_endpoints()
        if server is not None:
            try:
                server.quit()
            except Exception:
                pass
            return self.success_result(
                status="CONNECTED",
                message=f"Bell Sympatico connection successful via {label}.",
            )

        summary = " | ".join(errors[-4:]) if errors else "Unknown Bell SMTP failure"
        return self.failure_result(
            status="FAILED",
            message=f"Bell Sympatico connection failed after trying multiple endpoints. {summary}",
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

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        if self.from_name:
            msg["From"] = formataddr((self.from_name, self.from_email))
        else:
            msg["From"] = self.from_email
        msg["To"] = to_email

        if reply_to:
            msg["Reply-To"] = reply_to

        if high_priority:
            msg["X-Priority"] = "1"
            msg["X-MSMail-Priority"] = "High"
            msg["Importance"] = "High"

        final_html = html_body or ""
        if tracking_id and tracking_domain:
            pixel_url = f"{tracking_domain.rstrip('/')}/api/track?id={tracking_id}"
            tracking_tag = (
                f'<img src="{pixel_url}" alt="" width="1" height="1" style="display:none;"/>'
            )
            if "</body>" in final_html.lower():
                # case-insensitive-ish replace
                idx = final_html.lower().rfind("</body>")
                final_html = final_html[:idx] + tracking_tag + final_html[idx:]
            else:
                final_html += tracking_tag

        if text_body:
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
        if final_html:
            msg.attach(MIMEText(final_html, "html", "utf-8"))

        server, label, errors = self._try_login_across_endpoints()
        if server is None:
            summary = " | ".join(errors[-4:]) if errors else "Unknown Bell SMTP failure"
            return self.failure_result(
                status="FAILED",
                message=f"Bell Sympatico send failed: {summary}",
                retryable=True,
            )

        try:
            server.sendmail(self.from_email, [to_email], msg.as_string())
            try:
                server.quit()
            except Exception:
                pass
            return self.success_result(
                status="SENT",
                message=f"Email sent successfully via Bell Sympatico ({label}).",
            )
        except Exception as exc:
            try:
                server.quit()
            except Exception:
                pass
            return self.failure_result(
                status="FAILED",
                message=f"Bell Sympatico send failed: {self._error_message(exc)}",
                retryable=True,
            )
