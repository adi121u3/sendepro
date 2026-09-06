"""
Bell / Sympatico SMTP transport.

Official endpoints:
  Primary : smtphm.sympatico.ca
  Legacy  : smtp.sympatico.ca
  Ports   : 587 STARTTLS | 465 SSL

Username = full email address.
Password = Bell webmail password (or app password).

Connection strategy:
  1. Try the account's configured host/port/security first.
  2. On network / TLS failures, walk a fixed fallback list.
  3. On clear AUTH rejection, stop early (same credentials will fail everywhere).
"""

from __future__ import annotations

from dataclasses import dataclass
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

DEFAULT_TIMEOUT = 25


@dataclass(frozen=True)
class BellEndpoint:
    host: str
    port: int
    security: str  # starttls | ssl

    @property
    def label(self) -> str:
        return f"{self.host}:{self.port}/{self.security}"


# Ordered fallbacks after the account's preferred endpoint.
BELL_FALLBACKS: List[BellEndpoint] = [
    BellEndpoint("smtphm.sympatico.ca", 587, "starttls"),
    BellEndpoint("smtphm.sympatico.ca", 465, "ssl"),
    BellEndpoint("smtp.sympatico.ca", 587, "starttls"),
    BellEndpoint("smtp.sympatico.ca", 465, "ssl"),
]


def _normalize_security(value: str | None, port: int) -> str:
    sec = (value or "").strip().lower()
    if sec in {"tls", "start_tls", "starttls"}:
        return "starttls"
    if sec in {"ssl", "ssl/tls", "smtps"}:
        return "ssl"
    if port == 465:
        return "ssl"
    return "starttls"


class BellSympaticoTransport(BaseTransport):
    PROVIDER_NAME = "Bell Sympatico"

    def __init__(self, account_config: Dict[str, Any]):
        super().__init__(account_config)

        self.credential_key = account_config.get("credential_key")
        self.password = (account_config.get("password") or "").strip()
        if not self.password and self.credential_key:
            try:
                self.password = (CredentialManager.get_secret(self.credential_key) or "").strip()
            except Exception as exc:
                logger.error("Unable to load Bell credential: %s", exc)

        host = (account_config.get("host") or "").strip() or "smtphm.sympatico.ca"
        port = int(account_config.get("port") or 587)
        security = _normalize_security(account_config.get("security"), port)

        self.preferred = BellEndpoint(host, port, security)
        self.username = (account_config.get("username") or self.from_email or "").strip()
        self.from_name = (account_config.get("from_name") or "").strip()

        # Back-compat attributes used by older callers / logs
        self.host = self.preferred.host
        self.port = self.preferred.port
        self.security = self.preferred.security

    def _validate_config(self):
        if not self.username:
            return False, "Bell email/username is missing. Use the full email address."
        if "@" not in self.username:
            return False, "Bell username must be the full email (e.g. name@bell.net)."
        if not self.password:
            return False, "Bell password is missing. Re-save the account password and try again."
        return True, ""

    def _endpoint_queue(self) -> List[BellEndpoint]:
        seen = set()
        queue: List[BellEndpoint] = []
        for ep in [self.preferred, *BELL_FALLBACKS]:
            key = (ep.host.lower(), ep.port, ep.security)
            if key in seen:
                continue
            seen.add(key)
            queue.append(ep)
        return queue

    def _open(self, ep: BellEndpoint, timeout: int = DEFAULT_TIMEOUT) -> smtplib.SMTP:
        if ep.security == "ssl" or ep.port == 465:
            ctx = ssl.create_default_context()
            server = smtplib.SMTP_SSL(ep.host, ep.port, timeout=timeout, context=ctx)
            server.ehlo()
            return server

        server = smtplib.SMTP(ep.host, ep.port, timeout=timeout)
        server.ehlo()
        if ep.security == "starttls" or ep.port == 587:
            ctx = ssl.create_default_context()
            server.starttls(context=ctx)
            server.ehlo()
        return server

    @staticmethod
    def _classify(exc: Exception) -> Tuple[str, str]:
        """
        Returns (kind, message) where kind is:
          auth | timeout | closed | network | other
        """
        if isinstance(exc, smtplib.SMTPAuthenticationError):
            detail = ""
            try:
                raw = getattr(exc, "smtp_error", b"") or b""
                detail = (
                    raw.decode("utf-8", errors="ignore")
                    if isinstance(raw, (bytes, bytearray))
                    else str(raw)
                )
            except Exception:
                detail = str(exc)
            return (
                "auth",
                "Bell rejected username/password. "
                "Confirm full email + webmail password (or app password). "
                f"Server: {detail or 'authentication failed'}",
            )

        text = str(exc)
        lower = text.lower()

        if isinstance(exc, (socket.timeout, TimeoutError)) or "timed out" in lower or "timeout" in lower:
            return "timeout", f"Timed out reaching Bell SMTP ({text})"

        if "connection unexpectedly closed" in lower:
            return "closed", f"Bell closed the connection early ({text})"

        if isinstance(exc, (socket.gaierror, socket.herror, ConnectionRefusedError, OSError)):
            return "network", f"Network error reaching Bell SMTP ({text})"

        return "other", text

    def _login_with_fallback(self) -> Tuple[Optional[smtplib.SMTP], Optional[str], List[str]]:
        """
        Try preferred + fallbacks.
        Stop immediately on AUTH failure (credentials won't work on other ports).
        Continue on network/TLS issues.
        """
        trail: List[str] = []

        for ep in self._endpoint_queue():
            try:
                logger.info("Bell SMTP probe %s as %s", ep.label, self.username)
                server = self._open(ep)
                server.login(self.username, self.password)
                logger.info("Bell SMTP OK via %s", ep.label)
                return server, ep.label, trail
            except Exception as exc:
                kind, msg = self._classify(exc)
                trail.append(f"{ep.label}: {msg}")
                logger.error("Bell SMTP %s failed (%s): %s", ep.label, kind, exc)

                if kind == "auth":
                    # Same credentials will fail on every endpoint.
                    trail.insert(
                        0,
                        "Authentication rejected — not trying further endpoints.",
                    )
                    return None, None, trail

        return None, None, trail

    def test_connection(self) -> DeliveryResult:
        valid, error = self._validate_config()
        if not valid:
            return self.failure_result(status="FAILED", message=error, retryable=False)

        server, label, trail = self._login_with_fallback()
        if server is not None:
            try:
                server.quit()
            except Exception:
                pass
            return self.success_result(
                status="CONNECTED",
                message=f"Bell Sympatico connected via {label}.",
            )

        summary = " | ".join(trail[-3:]) if trail else "Unknown failure"
        retryable = not any("Authentication rejected" in t or "rejected username/password" in t for t in trail)
        return self.failure_result(
            status="FAILED",
            message=f"Bell connection failed. {summary}",
            retryable=retryable,
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
        msg["Subject"] = subject or ""
        msg["From"] = formataddr((self.from_name, self.from_email)) if self.from_name else self.from_email
        msg["To"] = to_email
        if reply_to:
            msg["Reply-To"] = reply_to
        if high_priority:
            msg["X-Priority"] = "1"
            msg["X-MSMail-Priority"] = "High"
            msg["Importance"] = "High"

        final_html = html_body or ""
        if tracking_id and tracking_domain:
            pixel = (
                f'<img src="{tracking_domain.rstrip("/")}/api/track?id={tracking_id}" '
                f'alt="" width="1" height="1" style="display:none;"/>'
            )
            lower = final_html.lower()
            if "</body>" in lower:
                idx = lower.rfind("</body>")
                final_html = final_html[:idx] + pixel + final_html[idx:]
            else:
                final_html += pixel

        if text_body:
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
        if final_html:
            msg.attach(MIMEText(final_html, "html", "utf-8"))

        server, label, trail = self._login_with_fallback()
        if server is None:
            summary = " | ".join(trail[-3:]) if trail else "Unknown failure"
            return self.failure_result(
                status="FAILED",
                message=f"Bell send failed. {summary}",
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
                message=f"Email sent via Bell Sympatico ({label}).",
            )
        except Exception as exc:
            try:
                server.quit()
            except Exception:
                pass
            _, msg_err = self._classify(exc)
            return self.failure_result(
                status="FAILED",
                message=f"Bell send failed: {msg_err}",
                retryable=True,
            )
