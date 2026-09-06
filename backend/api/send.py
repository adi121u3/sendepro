import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    Account,
    AccountCredential,
    ActivityLog,
    DeliveryLog,
)
from backend.security.encryption import decrypt_credential

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/send", tags=["send"])


def _is_success(result) -> bool:
    if result is None:
        return False
    value = str(getattr(result, "status", "") or "").strip().upper()
    return value in {"SENT", "SUCCESS"}


def _result_message(result, default: str = "Email dispatched successfully") -> str:
    if result is None:
        return default
    message = getattr(result, "message", None)
    if message:
        return str(message)
    return default


def _provider_message_id(result) -> Optional[str]:
    if result is None:
        return None
    value = getattr(result, "message_id", None)
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _safe_add_activity_log(
    db: Session,
    *,
    event_type: str,
    severity: str,
    message: str,
    entity_id: Optional[int] = None,
) -> None:
    db.add(
        ActivityLog(
            event_type=event_type,
            severity=severity,
            message=message,
            entity_id=entity_id,
        )
    )


@router.post("", status_code=status.HTTP_200_OK)
def send_email_message(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Send one email through the configured account provider.

    Microsoft/Outlook uses SMTP + XOAUTH2 (Aerion-style) so From Name is preserved.
    All transports use clean MIME without open-tracking pixels.
    """
    account_id = payload.get("sender_account_id")
    recipient = str(payload.get("recipient") or "").strip()
    subject = str(payload.get("subject") or "")
    body = str(payload.get("body") or "")
    from_name = str(payload.get("from_name") or "").strip()
    high_priority = bool(payload.get("high_priority", False))
    reply_to = str(payload.get("reply_to") or "").strip() or None

    if not recipient:
        raise HTTPException(status_code=400, detail="Recipient email is required.")
    if not account_id:
        raise HTTPException(status_code=400, detail="Sender account is required.")

    try:
        account_id = int(account_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Sender account ID must be a valid integer.")

    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Sender account not found.")

    if hasattr(account, "enabled") and account.enabled is False:
        raise HTTPException(status_code=400, detail="The selected sender account is disabled.")

    cred = db.query(AccountCredential).filter(AccountCredential.account_id == account.id).first()
    provider_type = str(account.provider or "smtp").strip().lower()

    requested_from_name = from_name
    effective_from_name = (
        requested_from_name
        or str(getattr(account, "from_name", None) or "").strip()
        or str(getattr(account, "name", None) or "").strip()
        or ""
    )

    logger.info(
        "SEND account_id=%s sender=%s from_name=%r provider=%s",
        account.id,
        account.email,
        effective_from_name,
        provider_type,
    )

    result = None

    try:
        if provider_type in {"microsoft", "outlook"}:
            if not cred or not cred.oauth_access_token_enc:
                raise HTTPException(
                    status_code=400,
                    detail="Microsoft OAuth access token is missing. Reconnect the Outlook account.",
                )
            from backend.transports.microsoft_smtp import MicrosoftSmtpTransport

            access_token = decrypt_credential(cred.oauth_access_token_enc)
            refresh_token = ""
            if cred.oauth_refresh_token_enc:
                refresh_token = decrypt_credential(cred.oauth_refresh_token_enc)
            if not access_token:
                raise HTTPException(
                    status_code=400,
                    detail="Microsoft OAuth access token could not be decrypted. Reconnect Outlook.",
                )

            transport = MicrosoftSmtpTransport(
                access_token=access_token,
                from_email=account.email,
                from_name=effective_from_name,
                refresh_token=refresh_token,
                smtp_host=getattr(account, "smtp_host", None) or "smtp.office365.com",
                smtp_port=getattr(account, "smtp_port", None) or 587,
            )
            result = transport.send_email(
                to_email=recipient,
                subject=subject,
                html_body=body,
                high_priority=high_priority,
                reply_to=reply_to,
            )

        elif provider_type in {"google", "gmail"}:
            if not cred or not cred.oauth_access_token_enc:
                raise HTTPException(
                    status_code=400,
                    detail="Google OAuth access token is missing. Reconnect the Gmail account.",
                )
            from backend.transports.google import GmailApiTransport

            access_token = decrypt_credential(cred.oauth_access_token_enc)
            refresh_token = ""
            if cred.oauth_refresh_token_enc:
                refresh_token = decrypt_credential(cred.oauth_refresh_token_enc)
            if not access_token:
                raise HTTPException(
                    status_code=400,
                    detail="Google OAuth access token could not be decrypted. Reconnect Gmail.",
                )

            transport = GmailApiTransport(
                access_token=access_token,
                refresh_token=refresh_token,
                from_email=account.email,
                from_name=effective_from_name,
            )
            result = transport.send_email(
                to_email=recipient,
                subject=subject,
                html_body=body,
                high_priority=high_priority,
                reply_to=reply_to,
            )

        elif provider_type == "zeptomail":
            if not cred or not cred.zeptomail_api_key_enc:
                raise HTTPException(status_code=400, detail="ZeptoMail API key is missing.")
            from backend.transports.zeptomail import ZeptoMailTransport

            api_key = decrypt_credential(cred.zeptomail_api_key_enc)
            if not api_key:
                raise HTTPException(status_code=400, detail="ZeptoMail API key could not be decrypted.")
            transport = ZeptoMailTransport(
                {
                    "from_email": account.email,
                    "from_name": effective_from_name,
                    "api_key": api_key,
                    "reply_to": reply_to or "",
                }
            )
            result = transport.send_email(
                to_email=recipient,
                subject=subject,
                html_body=body,
                high_priority=high_priority,
                reply_to=reply_to,
            )

        elif provider_type == "bell":
            if not cred or not cred.smtp_password_enc:
                raise HTTPException(status_code=400, detail="Bell SMTP password is missing.")
            from backend.transports.bell import BellSympaticoTransport

            password = decrypt_credential(cred.smtp_password_enc)
            transport = BellSympaticoTransport(
                {
                    "from_email": account.email,
                    "from_name": effective_from_name,
                    "host": getattr(account, "smtp_host", None),
                    "port": getattr(account, "smtp_port", None) or 587,
                    "security": getattr(account, "smtp_security", None) or "starttls",
                    "username": getattr(account, "smtp_username", None) or account.email,
                    "password": password,
                }
            )
            result = transport.send_email(
                to_email=recipient,
                subject=subject,
                html_body=body,
                high_priority=high_priority,
                reply_to=reply_to,
            )

        elif provider_type == "smtp":
            from backend.transports.smtp import send_smtp_email

            password = ""
            if cred and cred.smtp_password_enc:
                password = decrypt_credential(cred.smtp_password_enc)
            result = send_smtp_email(
                host=getattr(account, "smtp_host", None) or "smtp.gmail.com",
                port=getattr(account, "smtp_port", None) or 587,
                security=getattr(account, "smtp_security", None) or "starttls",
                username=getattr(account, "smtp_username", None) or account.email,
                password=password,
                from_email=account.email,
                from_name=effective_from_name,
                to_email=recipient,
                subject=subject,
                html_body=body,
                high_priority=high_priority,
                reply_to=reply_to,
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported email provider: {account.provider}",
            )

        sent_successfully = _is_success(result)
        message_val = _result_message(result)
        provider_message_id = _provider_message_id(result)

        if not sent_successfully:
            db.add(
                DeliveryLog(
                    account_id=account.id,
                    recipient=recipient,
                    provider=provider_type,
                    status="failed",
                    message_id=provider_message_id,
                    error_info=message_val,
                )
            )
            _safe_add_activity_log(
                db,
                event_type="email_send_failed",
                severity="error",
                message=f"Email send failed to {recipient} via {account.name}: {message_val}",
                entity_id=account.id,
            )
            db.commit()
            raise HTTPException(status_code=400, detail=message_val)

        db.add(
            DeliveryLog(
                account_id=account.id,
                recipient=recipient,
                provider=provider_type,
                status="success",
                message_id=provider_message_id,
                error_info=None,
            )
        )
        _safe_add_activity_log(
            db,
            event_type="email_sent",
            severity="info",
            message=(
                f"Email sent to {recipient} via {account.name} "
                f"(from_name={effective_from_name!r})"
            ),
            entity_id=account.id,
        )
        db.commit()

        response = {
            "status": "success",
            "message": message_val,
            "resolved_from_name": effective_from_name,
            "transport": (
                "microsoft_smtp"
                if provider_type in {"microsoft", "outlook"}
                else provider_type
            ),
        }
        if provider_message_id:
            response["provider_message_id"] = provider_message_id
        return response

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected send failure")
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Send failed: {exc}")
