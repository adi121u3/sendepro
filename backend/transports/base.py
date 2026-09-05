from typing import Dict, Any

class DeliveryResult:
    def __init__(self, status: str, message: str, retryable: bool = False):
        self.status = status
        self.message = message
        self.retryable = retryable

    def to_dict(self):
        return {
            "status": self.status,
            "message": self.message,
            "retryable": self.retryable
        }

class BaseTransport:
    def __init__(self, account_config: Dict[str, Any]):
        self.account_config = account_config
        self.from_email = account_config.get("from_email") or account_config.get("username") or ""

    def success_result(self, status: str = "SUCCESS", message: str = "Success") -> DeliveryResult:
        return DeliveryResult(status=status, message=message, retryable=False)

    def failure_result(self, status: str = "FAILED", message: str = "Failed", retryable: bool = False) -> DeliveryResult:
        return DeliveryResult(status=status, message=message, retryable=retryable)
