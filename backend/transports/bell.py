from typing import Dict, Any
import smtplib
import ssl
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from backend.transports.base import BaseTransport, DeliveryResult
from backend.security.credentials import CredentialManager

logger = logging.getLogger(__name__)

class BellSympaticoTransport(BaseTransport):
    PROVIDER_NAME = "Bell Sympatico"

    def __init__(self, account_config: Dict[str, Any]):
        super().__init__(account_config)
        self.credential_key = account_config.get("credential_key")
        self.password = account_config.get("password") or ""
        if not self.password and self.credential_key:
            try:
                self.password = CredentialManager.get_secret(self.credential_key) or ""
            except Exception as exc:
                logger.error(f"Unable to load Bell Sympatico credential: {exc}")
        
        self.host = account_config.get("host", "smtphm.sympatico.ca")
        self.port = int(account_config.get("port", 587))
        self.security = account_config.get("security", "starttls")
        self.username = account_config.get("username") or self.from_email

    def _validate_config(self):
        if not self.username:
            return False, "Bell Sympatico email/username is missing."
        if not self.password:
            return False, "Bell Sympatico password is missing."
        return True, ""

    @staticmethod
    def _error_message(exc: Exception) -> str:
        if isinstance(exc, smtplib.SMTPAuthenticationError):
            return "Bell Sympatico rejected the username or password. Verify the Bell webmail credentials and update the account."
        return str(exc)

    def test_connection(self) -> DeliveryResult:
        valid, error = self._validate_config()
        if not valid:
            return self.failure_result(status="FAILED", message=error, retryable=False)

        try:
            if self.security.lower() == "ssl" or self.port == 465:
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=15, context=context)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=15)
                server.ehlo()
                if self.security.lower() == "starttls" or self.port == 587:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    server.ehlo()

            server.login(self.username, self.password)
            server.quit()

            return self.success_result(
                status="CONNECTED",
                message=f"Bell Sympatico connection successful with {self.host}:{self.port} (STARTTLS)"
            )
        except Exception as exc:
            logger.error(f"Bell Sympatico connection failed: {exc}")
            return self.failure_result(
                status="FAILED",
                message=f"Bell Sympatico authentication failed: {self._error_message(exc)}",
                retryable=True
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
        tracking_domain: str = ""
    ) -> DeliveryResult:
        valid, error = self._validate_config()
        if not valid:
            return self.failure_result(status="FAILED", message=error, retryable=False)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.account_config.get('from_name', '')} <{self.from_email}>" if self.account_config.get('from_name') else self.from_email
        msg["To"] = to_email
        if reply_to:
            msg["Reply-To"] = reply_to

        if high_priority:
            msg["X-Priority"] = "1 (Highest)"
            msg["X-MSMail-Priority"] = "High"
            msg["Importance"] = "High"

        final_html = html_body
        if tracking_id:
            pixel_url = f"{tracking_domain}/api/track?id={tracking_id}"
            tracking_tag = f'<img src="{pixel_url}" alt="" width="1" height="1" style="display:none;"/>'
            if "</body>" in final_html:
                final_html = final_html.replace("</body>", f"{tracking_tag}</body>")
            else:
                final_html += tracking_tag

        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        if final_html:
            msg.attach(MIMEText(final_html, "html"))

        try:
            if self.security.lower() == "ssl" or self.port == 465:
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=20, context=context)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=20)
                server.ehlo()
                if self.security.lower() == "starttls" or self.port == 587:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    server.ehlo()

            server.login(self.username, self.password)
            server.sendmail(self.from_email, [to_email], msg.as_string())
            server.quit()

            return self.success_result(status="SENT", message="Email sent successfully via Bell Sympatico SMTP (smtphm.sympatico.ca:587 STARTTLS).")
        except Exception as exc:
            return self.failure_result(
                status="FAILED",
                message=f"Bell Sympatico send failed: {self._error_message(exc)}",
                retryable=True
            )
