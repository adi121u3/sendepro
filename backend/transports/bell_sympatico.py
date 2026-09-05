from typing import Dict, Any
import smtplib
import ssl
import logging
from backend.transports.base import BaseTransport, DeliveryResult
from backend.security.credentials import CredentialManager

logger = logging.getLogger(__name__)

class BellSympaticoTransport(BaseTransport):
    PROVIDER_NAME = "Bell Sympatico"

    def __init__(self, account_config: Dict[str, Any]):
        super().__init__(account_config)
        self.credential_key = account_config.get("credential_key")
        self.password = ""
        if self.credential_key:
            try:
                self.password = CredentialManager.get_secret(self.credential_key) or ""
            except Exception as exc:
                logger.error(f"Unable to load Bell Sympatico credential: {exc}")
        
        self.host = account_config.get("host", "smtp.sympatico.ca")
        self.port = int(account_config.get("port", 465))
        self.security = account_config.get("security", "ssl")
        self.username = account_config.get("username") or self.from_email

    def _validate_config(self):
        if not self.username:
            return False, "Bell Sympatico email/username is missing."
        if not self.password:
            return False, "Bell Sympatico password is missing."
        return True, ""

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
                if self.security.lower() == "starttls":
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    server.ehlo()

            server.login(self.username, self.password)
            server.quit()

            return self.success_result(
                status="CONNECTED",
                message=f"Bell Sympatico connection successful with {self.host}:{self.port}"
            )
        except Exception as exc:
            logger.error(f"Bell Sympatico connection failed: {exc}")
            return self.failure_result(
                status="FAILED",
                message=f"Bell Sympatico authentication failed: {str(exc)}",
                retryable=True
            )
