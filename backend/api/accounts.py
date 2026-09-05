from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Account, AccountCredential, ActivityLog
from backend.schemas.account import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    OAuthConnectRequest,
)
from backend.security.encryption import encrypt_credential, decrypt_credential
from backend.services.smtp_diagnostic import diagnose_smtp_error


router = APIRouter(prefix="/api/accounts", tags=["accounts"])


# ============================================================
# HELPERS
# ============================================================

def _account_response(account: Account) -> dict:
    """
    Convert an Account ORM object into the public API response.

    Credentials are intentionally never returned.
    """

    return {
        "id": account.id,
        "provider": account.provider,
        "name": account.name,
        "email": account.email,
        "from_name": account.from_name,
        "enabled": account.enabled,
        "daily_limit": account.daily_limit,
        "sent_today": 0,
        "status": account.status,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
    }


def _get_credentials(
    db: Session,
    account_id: int,
) -> AccountCredential | None:
    return (
        db.query(AccountCredential)
        .filter(AccountCredential.account_id == account_id)
        .first()
    )


def _ensure_credentials(
    db: Session,
    account_id: int,
) -> AccountCredential:
    """
    Get the existing credential row or create one.
    """

    cred = _get_credentials(db, account_id)

    if cred is None:
        cred = AccountCredential(account_id=account_id)
        db.add(cred)
        db.flush()

    return cred


def _is_oauth_provider(provider: str | None) -> bool:
    return (provider or "").strip().lower() in {
        "google",
        "gmail",
        "microsoft",
        "outlook",
    }


def _normalize_provider(provider: str | None) -> str:
    """
    Normalize aliases so Outlook is stored consistently as Microsoft
    and Gmail is stored consistently as Google.
    """

    value = (provider or "").strip().lower()

    if value == "outlook":
        return "microsoft"

    if value == "gmail":
        return "google"

    return value


def _save_oauth_credentials(
    db: Session,
    account_id: int,
    access_token: str | None,
    refresh_token: str | None,
    expires_at: datetime | None = None,
) -> AccountCredential:

    cred = _ensure_credentials(db, account_id)

    if access_token:
        cred.oauth_access_token_enc = encrypt_credential(access_token)

    # IMPORTANT:
    # OAuth providers may not return a refresh token every time.
    # Never erase an existing refresh token just because the new
    # OAuth response did not contain one.
    if refresh_token:
        cred.oauth_refresh_token_enc = encrypt_credential(refresh_token)

    if expires_at is not None:
        cred.oauth_token_expires_at = expires_at

    cred.updated_at = datetime.utcnow()

    db.add(cred)
    return cred


def _log_activity(
    db: Session,
    *,
    event_type: str,
    severity: str,
    message: str,
    entity_id: int | None = None,
):
    """
    Safely create an activity log.
    """

    try:
        log = ActivityLog(
            event_type=event_type,
            severity=severity,
            message=message,
            entity_id=entity_id,
        )

        db.add(log)
        db.flush()

    except Exception:
        # Logging must never break the actual account operation.
        db.rollback()


# ============================================================
# GET ACCOUNTS
# ============================================================

@router.get(
    "",
    response_model=List[AccountResponse],
)
def get_accounts(
    db: Session = Depends(get_db),
):
    """
    Return all configured sending accounts.

    Credentials and OAuth tokens are never exposed.
    """

    accounts = (
        db.query(Account)
        .order_by(Account.id.asc())
        .all()
    )

    return [
        _account_response(account)
        for account in accounts
    ]


# ============================================================
# CREATE ACCOUNT
# ============================================================

@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new SMTP, Bell, ZeptoMail, Google, or Microsoft account.
    """

    provider = _normalize_provider(payload.provider)

    # Avoid accidentally creating duplicate provider/email accounts.
    existing = (
        db.query(Account)
        .filter(
            Account.email == payload.email,
            Account.provider == provider,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"An account already exists for "
                f"{payload.email} using provider {provider}."
            ),
        )

    account = Account(
        provider=provider,
        name=payload.name,
        email=payload.email,

        # If no custom From Name was supplied, use the account name.
        from_name=(
            payload.from_name.strip()
            if payload.from_name and payload.from_name.strip()
            else payload.name
        ),

        smtp_host=payload.smtp_host,
        smtp_port=payload.smtp_port or 587,
        smtp_security=payload.smtp_security or "starttls",
        smtp_username=payload.smtp_username or payload.email,

        enabled=(
            payload.enabled
            if payload.enabled is not None
            else True
        ),

        daily_limit=(
            payload.daily_limit
            if payload.daily_limit is not None
            else 500
        ),

        status="active",
    )

    db.add(account)
    db.flush()

    # --------------------------------------------------------
    # Credentials
    # --------------------------------------------------------

    has_credentials = any(
        value
        for value in (
            payload.smtp_password,
            payload.zeptomail_api_key,
            payload.oauth_access_token,
            payload.oauth_refresh_token,
        )
    )

    if has_credentials:
        cred = AccountCredential(
            account_id=account.id,

            smtp_password_enc=(
                encrypt_credential(payload.smtp_password)
                if payload.smtp_password
                else None
            ),

            zeptomail_api_key_enc=(
                encrypt_credential(payload.zeptomail_api_key)
                if payload.zeptomail_api_key
                else None
            ),

            oauth_access_token_enc=(
                encrypt_credential(payload.oauth_access_token)
                if payload.oauth_access_token
                else None
            ),

            oauth_refresh_token_enc=(
                encrypt_credential(payload.oauth_refresh_token)
                if payload.oauth_refresh_token
                else None
            ),
        )

        db.add(cred)

    _log_activity(
        db,
        event_type="account_created",
        severity="info",
        message=(
            f"Account '{account.name}' "
            f"({account.email}) [{account.provider}] "
            f"created successfully."
        ),
        entity_id=account.id,
    )

    db.commit()
    db.refresh(account)

    return _account_response(account)


# ============================================================
# OAUTH CONNECT
# ============================================================

@router.post(
    "/oauth-connect",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def oauth_connect(
    payload: OAuthConnectRequest,
    db: Session = Depends(get_db),
):
    """
    Save an OAuth-connected Google or Microsoft account.

    Important From Name behavior:

    - A supplied payload.from_name is treated as the user's
      explicit custom From Name.
    - If there is already a custom From Name stored on the
      account and payload.from_name is omitted, it is preserved.
    - If this is a new account, the OAuth profile name is used
      as the initial From Name.
    """

    provider = _normalize_provider(payload.provider)

    if provider not in {"google", "microsoft"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "OAuth provider must be 'google' "
                "or 'microsoft'."
            ),
        )

    if not payload.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth account email is required.",
        )

    if not payload.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth access token is required.",
        )

    existing = (
        db.query(Account)
        .filter(
            Account.email == payload.email,
            Account.provider == provider,
        )
        .first()
    )

    # --------------------------------------------------------
    # EXISTING ACCOUNT
    # --------------------------------------------------------

    if existing:
        account = existing

        account.name = payload.name

        # CRITICAL FIX:
        # Only change From Name when the caller explicitly
        # supplied one.
        #
        # This prevents an OAuth reconnect from unexpectedly
        # replacing a user's custom From Name.
        if payload.from_name is not None:
            cleaned_from_name = payload.from_name.strip()

            if cleaned_from_name:
                account.from_name = cleaned_from_name

        # If there is no From Name at all, initialize it.
        elif not account.from_name:
            account.from_name = payload.name

        account.status = "active"
        account.updated_at = datetime.utcnow()

        _save_oauth_credentials(
            db,
            account.id,
            payload.access_token,
            payload.refresh_token,
        )

    # --------------------------------------------------------
    # NEW ACCOUNT
    # --------------------------------------------------------

    else:
        initial_from_name = (
            payload.from_name.strip()
            if payload.from_name and payload.from_name.strip()
            else payload.name
        )

        account = Account(
            provider=provider,
            name=payload.name,
            email=payload.email,
            from_name=initial_from_name,
            enabled=True,
            daily_limit=500,
            status="active",
        )

        db.add(account)
        db.flush()

        _save_oauth_credentials(
            db,
            account.id,
            payload.access_token,
            payload.refresh_token,
        )

    _log_activity(
        db,
        event_type="oauth_connected",
        severity="info",
        message=(
            f"OAuth2 account '{account.name}' "
            f"({account.email}) connected via {provider}."
        ),
        entity_id=account.id,
    )

    db.commit()
    db.refresh(account)

    return _account_response(account)


# ============================================================
# UPDATE ACCOUNT
# ============================================================

@router.put(
    "/{account_id}",
    response_model=AccountResponse,
)
def update_account(
    account_id: int,
    payload: AccountUpdate,
    db: Session = Depends(get_db),
):
    """
    Update account settings.

    This endpoint is particularly important for From Name.

    Example:

        {
            "from_name": "My Test Name"
        }

    will update the database value used by the sending layer.
    """

    account = (
        db.query(Account)
        .filter(Account.id == account_id)
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    updates = payload.model_dump(exclude_unset=True)

    # --------------------------------------------------------
    # Extract encrypted credentials
    # --------------------------------------------------------

    smtp_password = updates.pop("smtp_password", None)
    zeptomail_api_key = updates.pop("zeptomail_api_key", None)
    oauth_access_token = updates.pop("oauth_access_token", None)
    oauth_refresh_token = updates.pop("oauth_refresh_token", None)

    # --------------------------------------------------------
    # Normalize provider
    # --------------------------------------------------------

    if "provider" in updates:
        updates["provider"] = _normalize_provider(
            updates["provider"]
        )

    # --------------------------------------------------------
    # From Name
    # --------------------------------------------------------

    if "from_name" in updates:
        from_name = updates["from_name"]

        if from_name is not None:
            from_name = from_name.strip()

            # Allow intentionally clearing the From Name.
            updates["from_name"] = from_name or None

    # --------------------------------------------------------
    # Apply normal fields
    # --------------------------------------------------------

    for field, value in updates.items():
        if hasattr(account, field):
            setattr(account, field, value)

    account.updated_at = datetime.utcnow()

    # --------------------------------------------------------
    # Credentials
    # --------------------------------------------------------

    credential_values = {
        "smtp_password_enc": smtp_password,
        "zeptomail_api_key_enc": zeptomail_api_key,
        "oauth_access_token_enc": oauth_access_token,
        "oauth_refresh_token_enc": oauth_refresh_token,
    }

    if any(
        value is not None
        for value in credential_values.values()
    ):
        cred = _ensure_credentials(
            db,
            account.id,
        )

        for field, value in credential_values.items():
            if value is not None:
                setattr(
                    cred,
                    field,
                    encrypt_credential(value)
                    if value
                    else None,
                )

        cred.updated_at = datetime.utcnow()

    _log_activity(
        db,
        event_type="account_updated",
        severity="info",
        message=(
            f"Account '{account.name}' "
            f"({account.email}) updated successfully."
        ),
        entity_id=account.id,
    )

    db.commit()
    db.refresh(account)

    return _account_response(account)


# ============================================================
# TEST ACCOUNT
# ============================================================

@router.post(
    "/{account_id}/test",
    status_code=status.HTTP_200_OK,
)
def test_account(
    account_id: int,
    db: Session = Depends(get_db),
):
    """
    Test the configured account.

    OAuth:
        Performs a lightweight credential-presence check.

    ZeptoMail:
        Uses the ZeptoMail transport connection test.

    Bell:
        Uses the Bell/Sympatico transport connection test.

    SMTP:
        Performs SMTP authentication.
    """

    account = (
        db.query(Account)
        .filter(Account.id == account_id)
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    cred = _get_credentials(
        db,
        account.id,
    )

    provider = _normalize_provider(account.provider)

    # --------------------------------------------------------
    # OAuth
    # --------------------------------------------------------

    if _is_oauth_provider(provider) or (
        cred and cred.oauth_access_token_enc
    ):
        if not cred or not cred.oauth_access_token_enc:
            account.status = "error"
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "OAuth2 access token is missing. "
                    "Reconnect the account."
                ),
            )

        account.status = "active"
        account.updated_at = datetime.utcnow()

        db.commit()

        return {
            "status": "success",
            "message": (
                f"OAuth account '{account.name}' "
                f"has a stored access token."
            ),
        }

    try:

        # ----------------------------------------------------
        # ZeptoMail
        # ----------------------------------------------------

        if provider == "zeptomail" or (
            cred and cred.zeptomail_api_key_enc
        ):
            from backend.transports.zeptomail import (
                ZeptoMailTransport,
            )

            api_key = (
                decrypt_credential(
                    cred.zeptomail_api_key_enc
                )
                if cred
                and cred.zeptomail_api_key_enc
                else ""
            )

            transport = ZeptoMailTransport(
                {
                    "from_email": account.email,
                    "from_name": account.from_name,
                    "api_key": api_key,
                }
            )

            result = transport.test_connection()

            if result.status != "CONNECTED":
                raise Exception(result.message)

            account.status = "active"
            account.updated_at = datetime.utcnow()

            db.commit()

            return result.to_dict()

        # ----------------------------------------------------
        # Bell / Sympatico
        # ----------------------------------------------------

        if provider == "bell" or (
            account.smtp_host
            and "sympatico" in account.smtp_host.lower()
        ):
            from backend.transports.bell import (
                BellSympaticoTransport,
            )

            password = (
                decrypt_credential(
                    cred.smtp_password_enc
                )
                if cred
                and cred.smtp_password_enc
                else ""
            )

            transport = BellSympaticoTransport(
                {
                    "from_email": account.email,
                    "from_name": account.from_name,
                    "host": account.smtp_host,
                    "port": account.smtp_port or 587,
                    "security": (
                        account.smtp_security
                        or "starttls"
                    ),
                    "username": (
                        account.smtp_username
                        or account.email
                    ),
                    "password": password,
                }
            )

            result = transport.test_connection()

            if result.status != "CONNECTED":
                raise Exception(result.message)

            account.status = "active"
            account.updated_at = datetime.utcnow()

            db.commit()

            return result.to_dict()

        # ----------------------------------------------------
        # Generic SMTP
        # ----------------------------------------------------

        if not cred or not cred.smtp_password_enc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SMTP password credential is missing.",
            )

        password = decrypt_credential(
            cred.smtp_password_enc
        )

        from backend.transports.smtp import verify_smtp_auth

        result = verify_smtp_auth(
            account.smtp_host,
            account.smtp_port or 587,
            account.smtp_security or "starttls",
            account.smtp_username or account.email,
            password,
        )

        account.status = "active"
        account.updated_at = datetime.utcnow()

        db.commit()

        return result

    except HTTPException:
        raise

    except Exception as exc:
        account.status = "error"
        account.updated_at = datetime.utcnow()

        diagnostic_msg = diagnose_smtp_error(exc)

        _log_activity(
            db,
            event_type="account_test_failed",
            severity="error",
            message=(
                f"Account test failed for "
                f"'{account.name}': {diagnostic_msg}"
            ),
            entity_id=account.id,
        )

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=diagnostic_msg,
        )


# ============================================================
# TEST RAW SMTP CREDENTIALS
# ============================================================

@router.post(
    "/test-smtp",
    status_code=status.HTTP_200_OK,
)
def test_smtp_credentials(
    payload: dict,
):
    """
    Test raw SMTP credentials before saving them.
    """

    host = payload.get("host")
    username = payload.get("username")
    password = payload.get("password")

    try:
        port = int(
            payload.get(
                "port",
                587,
            )
        )
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMTP port must be a valid number.",
        )

    security = (
        payload.get("security")
        or "starttls"
    ).strip().lower()

    if not host or not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Host, username/email, and password "
                "are required for SMTP testing."
            ),
        )

    server = None

    try:
        import smtplib
        import ssl

        context = ssl.create_default_context()

        # ----------------------------------------------------
        # Implicit SSL
        # ----------------------------------------------------

        if security == "ssl" or port == 465:
            server = smtplib.SMTP_SSL(
                host,
                port,
                timeout=10,
                context=context,
            )

        # ----------------------------------------------------
        # Plain / STARTTLS
        # ----------------------------------------------------

        else:
            server = smtplib.SMTP(
                host,
                port,
                timeout=10,
            )

            server.ehlo()

            if security == "starttls" or port == 587:
                server.starttls(
                    context=context
                )
                server.ehlo()

        server.login(
            username,
            password,
        )

        return {
            "status": "success",
            "message": (
                f"SMTP authentication successful "
                f"with {host}:{port}."
            ),
        }

    except Exception as exc:
        diagnostic_msg = diagnose_smtp_error(exc)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=diagnostic_msg,
        )

    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                try:
                    server.close()
                except Exception:
                    pass


# ============================================================
# DELETE ACCOUNT
# ============================================================

@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete an account and its associated credentials.

    Whether the credential row is automatically deleted depends
    on your SQLAlchemy relationship/cascade configuration.
    """

    account = (
        db.query(Account)
        .filter(Account.id == account_id)
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    account_name = account.name
    account_email = account.email

    # Remove credentials explicitly so this does not depend on
    # database-level cascade configuration.
    cred = _get_credentials(
        db,
        account.id,
    )

    if cred is not None:
        db.delete(cred)
        db.flush()

    _log_activity(
        db,
        event_type="account_deleted",
        severity="warning",
        message=(
            f"Account '{account_name}' "
            f"({account_email}) deleted."
        ),
        entity_id=account_id,
    )

    db.delete(account)
    db.commit()

    return None