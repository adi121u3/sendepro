import logging
import os
import uuid
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


def _get_tracking_config() -> tuple[Optional[str], Optional[str]]:
    """
    Tracking is disabled unless a real public HTTPS URL is configured.

    Example:
        TRACKING_PUBLIC_URL=https://mail.example.com

    This prevents accidental generation of URLs such as:
        http://localhost:8000/api/track
    """
    tracking_url = os.getenv("TRACKING_PUBLIC_URL", "").strip().rstrip("/")

    if not tracking_url:
        return None, None

    if not tracking_url.lower().startswith("https://"):
        logger.warning(
            "TRACKING_PUBLIC_URL is configured but is not HTTPS. "
            "Email tracking has been disabled."
        )
        return None, None

    tracking_id = str(uuid.uuid4())
    return tracking_id, tracking_url


def _is_success(result) -> bool:
    """Normalize transport result status values."""
    if result is None:
        return False

    value = str(getattr(result, "status", "") or "").strip().upper()

    return value in {
        "SENT",
        "SUCCESS",
    }


def _result_message(result, default: str = "Email dispatched successfully") -> str:
    """Safely obtain the transport result message."""
    if result is None:
        return default

    message = getattr(result, "message", None)

    if message:
        return str(message)

    return default


def _provider_message_id(result) -> Optional[str]:
    """
    Return the real provider message ID only if the transport exposes one.

    IMPORTANT:
    The application's tracking UUID is NOT a provider message ID.
    """
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
    """
    ActivityLog matches the current models.py schema.

    Current ActivityLog fields:
        id
        event_type
        severity
        message
        entity_id
        created_at
    """
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

    Supported providers:
        - microsoft / outlook  (SMTP + XOAUTH2 — preserves From Name)
        - google / gmail
        - zeptomail
        - bell
        - smtp

    The account.provider value is authoritative.
    """

    account_id = payload.get("sender_account_id")
    recipient = str(payload.get("recipient") or "").strip()
    subject = str(payload.get("subject") or "")
    body = str(payload.get("body") or "")
    from_name = str(payload.get("from_name") or "").strip()
    high_priority = bool(payload.get("high_priority", False))

    # ---------------------------------------------------------
    # Basic validation
    # ---------------------------------------------------------

    if not recipient:
        raise HTTPException(
            status_code=400,
            detail="Recipient email is required.",
        )

    if not account_id:
        raise HTTPException(
            status_code=400,
            detail="Sender account is required.",
        )

    try:
        account_id = int(account_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Sender account ID must be a valid integer.",
        )

    # ---------------------------------------------------------
    # Load account
    # ---------------------------------------------------------

    account = (
        db.query(Account)
        .filter(Account.id == account_id)
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=404,
            detail="Sender account not found.",
        )

    if hasattr(account, "enabled") and account.enabled is False:
        raise HTTPException(
            status_code=400,
            detail="The selected sender account is disabled.",
        )

    cred = (
        db.query(AccountCredential)
        .filter(AccountCredential.account_id == account.id)
        .first()
    )

    provider_type = (
        str(account.provider or "smtp")
        .strip()
        .lower()
    )

    # ---------------------------------------------------------
    # From Name priority
    #
    # 1. Compose-time from_name (payload)
    # 2. Account from_name
    # 3. Account name
    # 4. Empty (transport falls back to bare email)
    #
    # Whitespace is normalized; empty string falls through.
    # ---------------------------------------------------------

    requested_from_name = from_name  # already stripped above

    effective_from_name = (
        requested_from_name
        or str(getattr(account, "from_name", None) or "").strip()
        or str(getattr(account, "name", None) or "").strip()
        or ""
    )

    logger.info(
        "SEND DEBUG account_id=%s sender_email=%s "
        "requested_from_name=%r resolved_from_name=%r provider=%s",
        account.id,
        account.email,
        requested_from_name,
        effective_from_name,
        provider_type,
    )

    # ---------------------------------------------------------
    # Tracking
    #
    # IMPORTANT:
    # Do NOT use request.base_url here.
    #
    # request.base_url in development can be:
    #     http://localhost:8000/
    #
    # External recipients cannot access the sender's localhost.
    #
    # Tracking only activates when TRACKING_PUBLIC_URL is configured
    # with HTTPS.
    # ---------------------------------------------------------

    tracking_id, tracking_domain = _get_tracking_config()

    result = None
    sent_successfully = False

    try:
        # =====================================================
        # MICROSOFT / OUTLOOK  →  SMTP + XOAUTH2
        #
        # Graph /me/sendMail forces the mailbox Azure AD display
        # name. SMTP lets us set the real MIME From header, so the
        # Compose From Name reaches the recipient.
        # =====================================================

        if provider_type in {"microsoft", "outlook"}:

            if not cred or not cred.oauth_access_token_enc:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Microsoft OAuth access token is missing. "
                        "Reconnect the Outlook account."
                    ),
                )

            from backend.transports.microsoft_smtp import (
                MicrosoftSmtpTransport,
            )

            access_token = decrypt_credential(
                cred.oauth_access_token_enc
            )

            refresh_token = ""
            if cred.oauth_refresh_token_enc:
                refresh_token = decrypt_credential(
                    cred.oauth_refresh_token_enc
                )

            if not access_token:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Microsoft OAuth access token could not be "
                        "decrypted. Reconnect the Outlook account."
                    ),
                )

            # Optional per-account SMTP host override; default is
            # smtp.office365.com which works for M365 and most
            # Outlook.com mailboxes.
            smtp_host = (
                getattr(account, "smtp_host", None)
                or "smtp.office365.com"
            )
            smtp_port = (
                getattr(account, "smtp_port", None)
                or 587
            )

            transport = MicrosoftSmtpTransport(
                access_token=access_token,
                from_email=account.email,
                from_name=effective_from_name,
                refresh_token=refresh_token,
                smtp_host=smtp_host,
                smtp_port=smtp_port,
            )

            logger.info(
                "SEND DEBUG transport=microsoft_smtp "
                "from_email=%s from_name=%r to=%s",
                account.email,
                effective_from_name,
                recipient,
            )

            result = transport.send_email(
                to_email=recipient,
                subject=subject,
                html_body=body,
                high_priority=high_priority,
                tracking_id=tracking_id,
                tracking_domain=tracking_domain or "",
            )

        # =====================================================
        # GOOGLE / GMAIL
        # =====================================================

        elif provider_type in {"google", "gmail"}:

            if not cred or not cred.oauth_access_token_enc:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Google OAuth access token is missing. "
                        "Reconnect the Gmail account."
                    ),
                )

            from backend.transports.google import GmailApiTransport

            access_token = decrypt_credential(
                cred.oauth_access_token_enc
            )

            refresh_token = ""

            if cred.oauth_refresh_token_enc:
                refresh_token = decrypt_credential(
                    cred.oauth_refresh_token_enc
                )

            if not access_token:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Google OAuth access token could not be "
                        "decrypted. Reconnect the Gmail account."
                    ),
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
                tracking_id=tracking_id,
                tracking_domain=tracking_domain or "",
            )

        # =====================================================
        # ZEPTOMAIL
        # =====================================================

        elif provider_type == "zeptomail":

            if not cred or not cred.zeptomail_api_key_enc:
                raise HTTPException(
                    status_code=400,
                    detail="ZeptoMail API key is missing.",
                )

            from backend.transports.zeptomail import (
                ZeptoMailTransport,
            )

            api_key = decrypt_credential(
                cred.zeptomail_api_key_enc
            )

            if not api_key:
                raise HTTPException(
                    status_code=400,
                    detail="ZeptoMail API key could not be decrypted.",
                )

            transport = ZeptoMailTransport(
                {
                    "from_email": account.email,
                    "from_name": effective_from_name,
                    "api_key": api_key,
                }
            )

            result = transport.send_email(
                to_email=recipient,
                subject=subject,
                html_body=body,
                high_priority=high_priority,
                tracking_id=tracking_id,
                tracking_domain=tracking_domain or "",
            )

        # =====================================================
        # BELL / SYMPATICO
        # =====================================================

        elif provider_type == "bell":

            if not cred or not cred.smtp_password_enc:
                raise HTTPException(
                    status_code=400,
                    detail="Bell SMTP password is missing.",
                )

            from backend.transports.bell import (
                BellSympaticoTransport,
            )

            password = decrypt_credential(
                cred.smtp_password_enc
            )

            transport = BellSympaticoTransport(
                {
                    "from_email": account.email,
                    "from_name": effective_from_name,
                    "host": getattr(account, "smtp_host", None),
                    "port": getattr(account, "smtp_port", None) or 587,
                    "security": (
                        getattr(account, "smtp_security", None)
                        or "starttls"
                    ),
                    "username": (
                        getattr(account, "smtp_username", None)
                        or account.email
                    ),
                    "password": password,
                }
            )

            result = transport.send_email(
                to_email=recipient,
                subject=subject,
                html_body=body,
                high_priority=high_priority,
                tracking_id=tracking_id,
                tracking_domain=tracking_domain or "",
            )

        # =====================================================
        # GENERIC SMTP
        # =====================================================

        elif provider_type == "smtp":

            from backend.transports.smtp import send_smtp_email

            password = ""

            if cred and cred.smtp_password_enc:
                password = decrypt_credential(
                    cred.smtp_password_enc
                )

            result = send_smtp_email(
                host=(
                    getattr(account, "smtp_host", None)
                    or "smtp.gmail.com"
                ),
                port=(
                    getattr(account, "smtp_port", None)
                    or 587
                ),
                security=(
                    getattr(account, "smtp_security", None)
                    or "starttls"
                ),
                username=(
                    getattr(account, "smtp_username", None)
                    or account.email
                ),
                password=password,
                from_email=account.email,
                from_name=effective_from_name,
                to_email=recipient,
                subject=subject,
                html_body=body,
                high_priority=high_priority,
                tracking_id=tracking_id,
                tracking_domain=tracking_domain or "",
            )

        # =====================================================
        # UNKNOWN PROVIDER
        # =====================================================

        else:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported email provider: "
                    f"{account.provider}"
                ),
            )

        # -----------------------------------------------------
        # Evaluate transport result
        # -----------------------------------------------------

        sent_successfully = _is_success(result)
        message_val = _result_message(result)

        provider_message_id = _provider_message_id(result)

        if not sent_successfully:
            # Record the actual provider failure ONCE.
            d_log = DeliveryLog(
                account_id=account.id,
                recipient=recipient,
                provider=provider_type,
                status="failed",
                message_id=provider_message_id,
                error_info=message_val,
            )

            db.add(d_log)

            _safe_add_activity_log(
                db,
                event_type="email_send_failed",
                severity="error",
                message=(
                    f"Email send failed to {recipient} "
                    f"via account {account.name}: {message_val}"
                ),
                entity_id=account.id,
            )

            db.commit()

            raise HTTPException(
                status_code=400,
                detail=message_val,
            )

        # -----------------------------------------------------
        # Successful delivery log
        # -----------------------------------------------------

        d_log = DeliveryLog(
            account_id=account.id,
            recipient=recipient,
            provider=provider_type,
            status="success",
            message_id=provider_message_id,
            error_info=None,
        )

        db.add(d_log)

        # -----------------------------------------------------
        # Successful activity log
        #
        # Only use fields that actually exist in ActivityLog.
        # -----------------------------------------------------

        _safe_add_activity_log(
            db,
            event_type="email_sent",
            severity="info",
            message=(
                f"Email sent successfully to {recipient} "
                f"via account {account.name} "
                f"(from_name={effective_from_name!r})"
            ),
            entity_id=account.id,
        )

        db.commit()

        # -----------------------------------------------------
        # Response
        # -----------------------------------------------------

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

        # Only expose tracking_id when tracking is actually enabled.
        if tracking_id:
            response["tracking_id"] = tracking_id

        # Include provider message ID only when the transport
        # actually supplied one.
        if provider_message_id:
            response["provider_message_id"] = provider_message_id

        return response

    # =========================================================
    # Preserve intended HTTP errors
    # =========================================================

    except HTTPException:
        db.rollback()
        raise

    # =========================================================
    # Unexpected application/database/transport errors
    # =========================================================

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Unexpected email send error for recipient=%s "
            "account_id=%s provider=%s",
            recipient,
            account_id,
            provider_type,
        )

        error_message = str(exc).strip() or "Unknown email send error."

        # Try to record ONE failure log.
        #
        # This uses only fields that exist in the current models.py.
        try:
            failure_log = DeliveryLog(
                account_id=account.id if account else None,
                recipient=recipient,
                provider=provider_type,
                status="failed",
                message_id=None,
                error_info=error_message,
            )

            db.add(failure_log)

            _safe_add_activity_log(
                db,
                event_type="email_send_failed",
                severity="error",
                message=(
                    f"Email send failed to {recipient}: "
                    f"{error_message}"
                ),
                entity_id=account.id if account else None,
            )

            db.commit()

        except Exception:
            db.rollback()

            logger.exception(
                "Failed to record email failure logs."
            )

        raise HTTPException(
            status_code=400,
            detail=error_message,
        )
