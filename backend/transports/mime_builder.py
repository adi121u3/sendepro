"""
Aerion-style MIME construction for outbound mail.

Clean multipart/alternative, controllable From display name, no tracking pixels.
"""

from __future__ import annotations

import re
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate
from typing import Optional

from backend.utils.deliverability import html_to_text


def sanitize_display_name(name: str) -> str:
    """
    Clean display names for the From header.

    Tabs / control characters (e.g. 'David\\tJackson') look abnormal to
    filters and can push messages toward spam.
    """
    if not name:
        return ""
    # Drop control chars except ordinary space
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", str(name))
    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _escape_text(value: str) -> str:
    return (
        (value or "")
        .replace("&", "&")
        .replace("<", "<")
        .replace(">", ">")
    )


def _wrap_simple_html(html: str, plain_fallback: str) -> str:
    body = (html or "").strip()
    if not body:
        safe = _escape_text(plain_fallback).replace("\r\n", "\n").replace("\n", "<br>")
        return (
            "<!DOCTYPE html><html><head>"
            '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">'
            "</head><body>"
            f'<div style="line-height:1.25"><p style="margin:0">{safe}</p></div>'
            "</body></html>"
        )

    lower = body.lower()
    if "<html" in lower or "<body" in lower:
        return body

    if "<div" in lower or "<p" in lower or "<br" in lower or "<span" in lower:
        return (
            "<!DOCTYPE html><html><head>"
            '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">'
            f"</head><body>{body}</body></html>"
        )

    safe = _escape_text(body).replace("\r\n", "\n").replace("\n", "<br>")
    return (
        "<!DOCTYPE html><html><head>"
        '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">'
        "</head><body>"
        f'<div style="line-height:1.25"><p style="margin:0">{safe}</p></div>'
        "</body></html>"
    )


def build_outbound_message(
    *,
    from_email: str,
    from_name: str = "",
    to_email: str,
    subject: str = "",
    html_body: str = "",
    text_body: str = "",
    reply_to: Optional[str] = None,
    high_priority: bool = False,
) -> MIMEMultipart:
    """Build a clean outbound MIME message (no tracking pixels)."""
    msg = MIMEMultipart("alternative")

    name = sanitize_display_name(from_name or "")
    addr = (from_email or "").strip()
    if name and addr:
        msg["From"] = formataddr((name, addr))
    else:
        msg["From"] = addr or name

    msg["To"] = (to_email or "").strip()
    msg["Subject"] = subject or ""
    msg["Date"] = formatdate(localtime=True)
    msg["User-Agent"] = "SendePro Email Client"
    msg["X-Mailer"] = "SendePro"
    msg["MIME-Version"] = "1.0"

    try:
        msg["Message-ID"] = f"<{uuid.uuid4()}@sendepro>"
    except Exception:
        pass

    if reply_to and str(reply_to).strip():
        msg["Reply-To"] = str(reply_to).strip()

    if high_priority:
        msg["X-Priority"] = "1"
        msg["X-MSMail-Priority"] = "High"
        msg["Importance"] = "High"

    html_raw = html_body if isinstance(html_body, str) else ""
    plain = (text_body or "").strip() or html_to_text(html_raw) or (subject or "").strip() or " "
    html = _wrap_simple_html(html_raw, plain)

    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    return msg


def message_as_bytes(msg: MIMEMultipart) -> bytes:
    return msg.as_bytes()
