"""
Aerion-style MIME construction for outbound mail.

Goals (matching what works for inbox + From Name):
  - Real RFC 5322 From: Display Name <email@domain>
  - multipart/alternative with text/plain first, then text/html
  - Proper Date + Message-ID
  - Optional Reply-To
  - NO open-tracking pixels (they hurt deliverability)
"""

from __future__ import annotations

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from typing import Optional

from backend.utils.deliverability import html_to_text


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

    name = (from_name or "").strip()
    addr = (from_email or "").strip()
    if name and addr:
        msg["From"] = formataddr((name, addr))
    else:
        msg["From"] = addr or name

    msg["To"] = (to_email or "").strip()
    msg["Subject"] = subject or ""
    msg["Date"] = formatdate(localtime=True)

    try:
        domain = addr.split("@")[-1] if "@" in addr else "localhost"
        msg["Message-ID"] = make_msgid(domain=domain)
    except Exception:
        pass

    if reply_to and str(reply_to).strip():
        msg["Reply-To"] = str(reply_to).strip()

    if high_priority:
        msg["X-Priority"] = "1"
        msg["X-MSMail-Priority"] = "High"
        msg["Importance"] = "High"

    html = html_body if isinstance(html_body, str) else ""
    plain = (text_body or "").strip() or html_to_text(html) or (subject or "").strip() or " "

    # text/plain first (Aerion / RFC preference for clients)
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    if html.strip():
        msg.attach(MIMEText(html, "html", "utf-8"))
    else:
        msg.attach(MIMEText(f"<p>{plain}</p>", "html", "utf-8"))

    return msg


def message_as_bytes(msg: MIMEMultipart) -> bytes:
    """Serialize with CRLF for SMTP DATA."""
    # as_bytes() already uses policy that produces correct line endings on modern Python
    return msg.as_bytes()
