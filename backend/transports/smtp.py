"""
Inbuilt SMTP delivery engine (Aerion-style).

Connects with STARTTLS (587) or SSL (465), authenticates, and sends a
clean RFC 5322 message with controllable From display name.
Tracking pixels are intentionally not used.
"""

from __future__ import annotations

import smtplib
import ssl
import logging
from typing import Optional

from backend.transports.base import DeliveryResult
from backend.transports.mime_builder import build_outbound_message, message_as_bytes

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30


def verify_smtp_auth(host: str, port: int, security: str, username: str, password: str) -> dict:
    if not host or not username or not password:
        raise ValueError("SMTP host, username, and password are required.")

    try:
        server = _connect(host, int(port), security)
        server.login(username, password)
        try:
            server.quit()
        except Exception:
            pass
        return {
            "success": True,
            "message": f"SMTP authentication successful with {host}:{port}",
            "host": host,
            "port": port,
            "security": security,
        }
    except Exception as e:
        logger.error("SMTP transport verification failed for %s:%s - %s", host, port, e)
        raise


def _connect(host: str, port: int, security: str, timeout: int = DEFAULT_TIMEOUT):
    sec = (security or "starttls").strip().lower()
    if sec in {"ssl", "ssl/tls", "smtps"} or port == 465:
        ctx = ssl.create_default_context()
        server = smtplib.SMTP_SSL(host, port, timeout=timeout, context=ctx)
        server.ehlo()
        return server

    server = smtplib.SMTP(host, port, timeout=timeout)
    server.ehlo()
    if sec in {"starttls", "tls", ""} or port == 587:
        ctx = ssl.create_default_context()
        server.starttls(context=ctx)
        server.ehlo()
    return server


def send_smtp_email(
    host: str,
    port: int,
    security: str,
    username: str,
    password: str,
    from_email: str,
    from_name: str,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str = "",
    reply_to: Optional[str] = None,
    high_priority: bool = False,
    tracking_id: str = None,
    tracking_domain: str = "",
) -> DeliveryResult:
    """Send via inbuilt SMTP. tracking_* args are ignored (pixels removed)."""
    try:
        msg = build_outbound_message(
            from_email=from_email,
            from_name=from_name or "",
            to_email=to_email,
            subject=subject or "",
            html_body=html_body or "",
            text_body=text_body or "",
            reply_to=reply_to,
            high_priority=high_priority,
        )
        raw = message_as_bytes(msg)

        server = _connect(host, int(port or 587), security or "starttls")
        try:
            server.login(username, password)
            server.sendmail(from_email, [to_email], raw)
        finally:
            try:
                server.quit()
            except Exception:
                pass

        return DeliveryResult(
            status="SENT",
            message=f"Email sent via inbuilt SMTP ({host}:{port}).",
        )
    except Exception as e:
        logger.error("SMTP send failed via %s:%s - %s", host, port, e)
        return DeliveryResult(
            status="FAILED",
            message=f"SMTP send failed: {e}",
            retryable=True,
        )
