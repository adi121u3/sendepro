import logging
from typing import Optional

import requests

from backend.transports.base import DeliveryResult

logger = logging.getLogger(__name__)


class MicrosoftGraphTransport:
    """
    Microsoft Graph email transport.

    Sends mail through the authenticated Microsoft 365 / Outlook
    mailbox using:

        POST https://graph.microsoft.com/v1.0/me/sendMail

    Important:
    - The authenticated Microsoft mailbox controls the actual sender.
    - `from_name` is requested as the display name for that mailbox.
    - Microsoft/Exchange may normalize the final display name to the
      mailbox's configured display name.
    - This transport never changes the sender email address.
    """

    ENDPOINT = "https://graph.microsoft.com/v1.0/me/sendMail"

    def __init__(
        self,
        access_token: str,
        from_email: str,
        from_name: str = "",
    ):
        self.access_token = (
            access_token.strip()
            if isinstance(access_token, str)
            else ""
        )

        self.from_email = (
            from_email.strip()
            if isinstance(from_email, str)
            else ""
        )

        self.from_name = (
            from_name.strip()
            if isinstance(from_name, str)
            else ""
        )

    # ---------------------------------------------------------
    # TRACKING
    # ---------------------------------------------------------

    def _build_tracking_tag(
        self,
        tracking_id: Optional[str],
        tracking_domain: str,
    ) -> str:
        """
        Build the tracking pixel only when an HTTPS public
        tracking domain has explicitly been configured.
        """

        if not tracking_id:
            return ""

        domain = (tracking_domain or "").strip().rstrip("/")

        if not domain:
            return ""

        if not domain.lower().startswith("https://"):
            logger.warning(
                "Microsoft tracking disabled because tracking "
                "domain is not HTTPS: %s",
                domain,
            )
            return ""

        pixel_url = (
            f"{domain}/api/track?id={tracking_id}"
        )

        return (
            f'<img src="{pixel_url}" '
            'alt="" '
            'width="1" '
            'height="1" '
            'style="display:none;" />'
        )

    # ---------------------------------------------------------
    # BODY
    # ---------------------------------------------------------

    def _prepare_body(
        self,
        html_body: str,
        text_body: str,
        tracking_id: Optional[str],
        tracking_domain: str,
    ) -> tuple[str, str]:

        html = (
            html_body
            if isinstance(html_body, str)
            else ""
        )

        text = (
            text_body
            if isinstance(text_body, str)
            else ""
        )

        # Prefer HTML when supplied.
        if html.strip():

            final_html = html

            tracking_tag = self._build_tracking_tag(
                tracking_id=tracking_id,
                tracking_domain=tracking_domain,
            )

            if tracking_tag:

                lower_html = final_html.lower()

                body_end = lower_html.rfind("</body>")

                if body_end >= 0:
                    final_html = (
                        final_html[:body_end]
                        + tracking_tag
                        + final_html[body_end:]
                    )
                else:
                    final_html += tracking_tag

            return "HTML", final_html

        # Otherwise use plain text.
        if text.strip():
            return "Text", text

        return "HTML", ""

    # ---------------------------------------------------------
    # MESSAGE
    # ---------------------------------------------------------

    def _build_message(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        reply_to: Optional[str],
        high_priority: bool,
        tracking_id: Optional[str],
        tracking_domain: str,
    ) -> dict:

        content_type, content = self._prepare_body(
            html_body=html_body,
            text_body=text_body,
            tracking_id=tracking_id,
            tracking_domain=tracking_domain,
        )

        message = {
            "subject": subject or "",
            "body": {
                "contentType": content_type,
                "content": content,
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": to_email,
                    }
                }
            ],
        }

        # -----------------------------------------------------
        # FROM NAME
        # -----------------------------------------------------
        #
        # Only add the explicit From object when a name was
        # actually supplied.
        #
        # The address MUST remain the authenticated mailbox.
        #

        if self.from_email:

            from_address = {
                "address": self.from_email,
            }

            if self.from_name:
                from_address["name"] = self.from_name

            message["from"] = {
                "emailAddress": from_address,
            }

        # -----------------------------------------------------
        # REPLY-TO
        # -----------------------------------------------------

        if reply_to:

            clean_reply_to = reply_to.strip()

            if clean_reply_to:
                message["replyTo"] = [
                    {
                        "emailAddress": {
                            "address": clean_reply_to,
                        }
                    }
                ]

        # -----------------------------------------------------
        # PRIORITY
        # -----------------------------------------------------

        if high_priority:
            message["importance"] = "high"

        return message

    # ---------------------------------------------------------
    # GRAPH ERROR
    # ---------------------------------------------------------

    @staticmethod
    def _extract_graph_error(
        response: requests.Response,
    ) -> str:

        try:

            data = response.json()

            if isinstance(data, dict):

                error = data.get("error")

                if isinstance(error, dict):

                    code = error.get("code")
                    message = error.get("message")

                    if code and message:
                        return (
                            f"{code}: {message}"
                        )

                    if message:
                        return str(message)

                message = data.get("message")

                if message:
                    return str(message)

        except (ValueError, TypeError):
            pass

        text = (
            response.text
            if response.text
            else ""
        ).strip()

        if text:
            return text

        return (
            "Microsoft Graph returned "
            f"HTTP {response.status_code}."
        )

    # ---------------------------------------------------------
    # SEND
    # ---------------------------------------------------------

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

        # -----------------------------------------------------
        # VALIDATION
        # -----------------------------------------------------

        if not self.access_token:

            return DeliveryResult(
                status="FAILED",
                message=(
                    "Microsoft OAuth access token is "
                    "missing or expired."
                ),
                retryable=False,
            )

        if not self.from_email:

            return DeliveryResult(
                status="FAILED",
                message=(
                    "Microsoft sender email address "
                    "is missing."
                ),
                retryable=False,
            )

        if not to_email or not str(to_email).strip():

            return DeliveryResult(
                status="FAILED",
                message=(
                    "Recipient email address is required."
                ),
                retryable=False,
            )

        to_email = str(to_email).strip()

        # -----------------------------------------------------
        # BUILD MESSAGE
        # -----------------------------------------------------

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

        payload = {
            "message": message,
            "saveToSentItems": True,
        }

        # -----------------------------------------------------
        # IMPORTANT DEBUG LOG
        # -----------------------------------------------------
        #
        # This tells us exactly which From address/name your
        # application is sending to Graph.
        #
        # It does NOT log the OAuth access token.
        #

        requested_from_name = (
            message
            .get("from", {})
            .get("emailAddress", {})
            .get("name", "")
        )

        requested_from_email = (
            message
            .get("from", {})
            .get("emailAddress", {})
            .get("address", "")
        )

        logger.info(
            "Microsoft Graph send request: "
            "from_email=%s "
            "from_name=%r "
            "to=%s "
            "subject=%r",
            requested_from_email,
            requested_from_name,
            to_email,
            subject,
        )

        try:

            response = requests.post(
                self.ENDPOINT,
                headers={
                    "Authorization": (
                        f"Bearer {self.access_token}"
                    ),
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=payload,
                timeout=20,
            )

        except requests.Timeout:

            logger.error(
                "Microsoft Graph request timed out "
                "while sending to %s",
                to_email,
            )

            return DeliveryResult(
                status="FAILED",
                message=(
                    "Microsoft Graph request timed out. "
                    "Please try again."
                ),
                retryable=True,
            )

        except requests.ConnectionError as exc:

            logger.error(
                "Microsoft Graph connection failed: %s",
                exc,
            )

            return DeliveryResult(
                status="FAILED",
                message=(
                    "Could not connect to Microsoft Graph. "
                    "Please check the internet connection "
                    "and try again."
                ),
                retryable=True,
            )

        except requests.RequestException as exc:

            logger.error(
                "Microsoft Graph request failed: %s",
                exc,
            )

            return DeliveryResult(
                status="FAILED",
                message=(
                    f"Microsoft Graph request failed: {exc}"
                ),
                retryable=True,
            )

        # -----------------------------------------------------
        # RESPONSE HANDLING
        # -----------------------------------------------------

        if response.status_code == 401:

            detail = self._extract_graph_error(response)

            logger.warning(
                "Microsoft Graph authentication failed: %s",
                detail,
            )

            return DeliveryResult(
                status="FAILED",
                message=(
                    "Microsoft OAuth access token is "
                    "expired or invalid. "
                    "Reconnect the Outlook account."
                ),
                retryable=False,
            )

        if response.status_code == 403:

            detail = self._extract_graph_error(response)

            logger.error(
                "Microsoft Graph permission/access error: "
                "%s",
                detail,
            )

            return DeliveryResult(
                status="FAILED",
                message=(
                    "Microsoft Graph rejected the request "
                    "because the account does not have "
                    "permission to send the message: "
                    f"{detail}"
                ),
                retryable=False,
            )

        if response.status_code == 400:

            detail = self._extract_graph_error(response)

            logger.error(
                "Microsoft Graph rejected the message: %s",
                detail,
            )

            return DeliveryResult(
                status="FAILED",
                message=(
                    "Microsoft Graph rejected the email: "
                    f"{detail}"
                ),
                retryable=False,
            )

        if response.status_code == 429:

            detail = self._extract_graph_error(response)

            retry_after = response.headers.get(
                "Retry-After"
            )

            if retry_after:
                detail = (
                    f"{detail} "
                    f"Retry-After: {retry_after} seconds."
                )

            logger.warning(
                "Microsoft Graph rate limited request: %s",
                detail,
            )

            return DeliveryResult(
                status="FAILED",
                message=(
                    f"Microsoft Graph rate limit: {detail}"
                ),
                retryable=True,
            )

        if not response.ok:

            detail = self._extract_graph_error(response)

            logger.error(
                "Microsoft Graph send failed: "
                "HTTP %s - %s",
                response.status_code,
                detail,
            )

            return DeliveryResult(
                status="FAILED",
                message=(
                    "Microsoft Graph send failed "
                    f"(HTTP {response.status_code}): "
                    f"{detail}"
                ),
                retryable=response.status_code >= 500,
            )

        # -----------------------------------------------------
        # SUCCESS
        # -----------------------------------------------------
        #
        # Microsoft Graph normally returns 202 Accepted for
        # sendMail and does not return the sent message object.
        #
        # Therefore we deliberately do NOT try to manufacture
        # a message_id here.
        # -----------------------------------------------------

        logger.info(
            "Microsoft Graph accepted email for delivery: "
            "from=%s "
            "from_name=%r "
            "to=%s "
            "status=%s",
            self.from_email,
            self.from_name,
            to_email,
            response.status_code,
        )

        return DeliveryResult(
            status="SENT",
            message=(
                "Email sent successfully via "
                "Microsoft Graph."
            ),
            retryable=False,
        )