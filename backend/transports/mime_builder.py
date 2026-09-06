"""
Aerion-style MIME construction for outbound mail.

Verified against an Aerion → Gmail inbox sample:
  From: marce <user@hotmail.com>
  User-Agent: Aerion Email Client
  multipart/alternative; text/plain then text/html
  Content-Transfer-Encoding: quoted-printable
  Simple HTML wrapper (line-height / margin)
  No tracking pixels
"""

from __future__ import annotations

import re
import uuid
from email import charset as charset_mod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate
from typing import Optional

from backend.utils.deliverability import html_to_text

# Prefer quoted-printable for utf-8 (matches Aerion headers)
charset_mod.add_charset("utf-8", charset_mod.SHORTEST, charset_mod.QP, "utf-8")


def _wrap_simple_html(html: str, plain_fallback: str) -> str:
    """
    If the body is already full HTML, keep it.
    If it is plain / minimal, wrap like Aerion:
      <div style="line-height:1.25"><p style="margin:0">...</p></div>
    """
    body = (html or "").strip()
    if not body:
        safe = (plain_fallback or "").replace("&", "&").replace("<", "<").replace(">", ">")
        return (
            '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">'
            f'<div style="line-height:1.25"><p style="margin:0">{safe}</p></div>'
        )

    lower = body.lower()
    if "<html" in lower or "<body" in lower or "<div" in lower or "<p" in lower:
        # Ensure charset meta exists for simple fragments
        if "content-type" not in lower and "charset" not in lower:
            return (
                '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">'
                + body
            )
        return body

    # Plain-ish content → Aerion-style wrapper
    safe = body.replace("&", "&").replace("<", "<").replace(">", ">")
    safe = re.sub(r"\r?\n", "<br>", safe)
    return (
        '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">'
        f'<div style="line-height:1.25"><p style="margin:0">{safe}</p></div>'
    )


def _qp_text(payload: str, subtype: str) -> MIMEText:
    """Build a MIMEText part forced to quoted-printable utf-8."""
    part = MIMEText(payload, subtype, "utf-8")
    # Ensure CTE is quoted-printable (not base64)
    if part.get("Content-Transfer-Encoding", "").lower() != "quoted-printable":
        try:
            part.replace_header("Content-Transfer-Encoding", "quoted-printable")
        except KeyError:
            part.add_header("Content-Transfer-Encoding", "quoted-printable")
    return part


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
    """Build a clean Aerion-style outbound MIME message (no tracking pixels)."""
    msg = MIMEMultipart("alternative")

    name = (from_name or "").strip()
    addr = (from_email or "").strip()
    if name and addr:
        msg["From"] = formataddr((name, addr))
    else:
        msg["From"] = addr or name

    msg["To"] = (to_email or "").strip()
    msg["Subject"] = subject or ""
    msg["Date"] = formatdate(localtime=True)

    # Client identity (Aerion sets User-Agent: Aerion Email Client)
    msg["User-Agent"] = "SendePro Email Client"
    msg["X-Mailer"] = "SendePro"

    # Original client Message-ID (Microsoft may replace the outer Message-ID)
    try:
        msg["Message-ID"] = f"<{uuid.uuid4()}@sendepro>"
    except Exception:
        pass

    if reply_to and str(reply_to).strip():
        msg["Reply-To"] = str(reply_to).strip()

    # Avoid high-priority headers by default (spam signal on cold mail)
    if high_priority:
        msg["X-Priority"] = "1"
        msg["X-MSMail-Priority"] = "High"
        msg["Importance"] = "High"

    html_raw = html_body if isinstance(html_body, str) else ""
    plain = (text_body or "").strip() or html_to_text(html_raw) or (subject or "").strip() or " "
    html = _wrap_simple_html(html_raw, plain)

    # text/plain first, then text/html — both quoted-printable
    msg.attach(_qp_text(plain, "plain"))
    msg.attach(_qp_text(html, "html"))

    return msg


def message_as_bytes(msg: MIMEMultipart) -> bytes:
    """Serialize for SMTP DATA."""
    return msg.as_bytes()
