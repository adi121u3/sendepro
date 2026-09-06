"""
Deliverability helpers.

Open-tracking pixels are disabled permanently — they hurt inbox placement
(especially localhost / non-HTTPS URLs) and are not used by Aerion-style
SMTP delivery.
"""

from __future__ import annotations

import re
from html import unescape
from typing import Optional


def is_public_https_origin(url: Optional[str]) -> bool:
    return False  # tracking disabled


def inject_tracking_pixel(
    html_body: str,
    tracking_id: Optional[str] = None,
    tracking_domain: Optional[str] = None,
) -> str:
    """No-op: tracking pixels are not injected."""
    return html_body or ""


def html_to_text(html: str) -> str:
    """Lightweight HTML → plain text for multipart/alternative."""
    if not html:
        return ""
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>", "\n\n", text)
    text = re.sub(r"(?i)</div>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()
