"""
Shared helpers that improve inbox placement and prevent common spam signals.

Critical rule:
  Never inject tracking pixels unless the base URL is a public HTTPS origin.
  http://localhost and bare relative URLs are strong spam / phishing signals
  and are invisible to recipients, so they only hurt reputation.
"""

from __future__ import annotations

import re
from html import unescape
from typing import Optional


def is_public_https_origin(url: Optional[str]) -> bool:
    value = (url or "").strip().rstrip("/")
    if not value.lower().startswith("https://"):
        return False
    host = value[8:].split("/")[0].lower()
    if not host or host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        return False
    if host.endswith(".local") or host.endswith(".internal"):
        return False
    return True


def inject_tracking_pixel(
    html_body: str,
    tracking_id: Optional[str],
    tracking_domain: Optional[str],
) -> str:
    """
    Append a 1x1 open-tracking pixel only when safe.

    Returns the original HTML unchanged when tracking is disabled or unsafe.
    """
    body = html_body or ""
    tid = (tracking_id or "").strip()
    domain = (tracking_domain or "").strip().rstrip("/")

    if not tid or not is_public_https_origin(domain):
        return body

    pixel_url = f"{domain}/api/track?id={tid}"
    tag = (
        f'<img src="{pixel_url}" alt="" width="1" height="1" '
        f'style="display:none;border:0;outline:none;" />'
    )

    lower = body.lower()
    if "</body>" in lower:
        idx = lower.rfind("</body>")
        return body[:idx] + tag + body[idx:]
    return body + tag


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
