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


def _account_response(account: Account) -> dict:
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


def _get_credentials(db: Session, account_id: int) -> AccountCredential | None:
    return db.query(AccountCredential).filter(AccountCredential.account_id == account_id).first()


def _ensure_credentials(db: Session, account_id: int) -> AccountCredential:
    cred = _get_credentials(db, account_id)
    if cred is None:
        cred = AccountCredential(account_id=account_id)
        db.add(cred)
        db.flush()
    return cred


def _is_oauth_provider(provider: str | None) -> bool:
    return (provider or "").strip().lower() in {"google", "gmail", "microsoft", "outlook"}


def _normalize_provider(provider: str | None) -> str:
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
    if refresh_token:
        cred.oauth_refresh_token_enc = encrypt_credential(refresh_token)
    if expires_at is not None:
        cred.oauth_token_expires_at = expires_at
    cred.updated_at = datetime.utcnow()
    db.add(cred)
    return cred


def _log_activity(db: Session, *, event_type: str, severity: str, message: str, entity_id: int | None = None):
    try:
        db.add(ActivityLog(event_type=event_type, severity=severity, message=message, entity_id=entity_id))
        db.flush()
    except Exception:
        db.rollback()


@router.get("", response_model=List[AccountResponse])
def get_accounts(db: Session = Depends(get_db)):
    accounts = db.query(Account).order_by(Account.id.asc()).all()
    return [_account_response(account) for account in accounts]


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    provider = _normalize_provider(payload.provider)
    existing = db.query(Account).filter(Account.email == payload.email, Account.provider == provider).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"An account already exists for {payload.email} using provider {provider}.")

    account = Account(
        provider=provider,
        name=payload.name,
        email=payload.email,
        from_name=(payload.from_name.strip() if payload.from_name and payload.from_name.strip() else payload.name),
        smtp_host=payload.smtp_host,
        smtp_port=payload.smtp_port or 587,
        smtp_security=payload.smtp_security or "starttls",
        smtp_username=payload.smtp_username or payload.email,
        enabled=payload.enabled if payload.enabled is not None else True,
        daily_limit=payload.daily_limit if payload.daily_limit is not None else 500,
        status="active",
    )
    db.add(account)
    db.flush()

    if any(v for v in (payload.smtp_password, payload.zeptomail_api_key, payload.oauth_access_token, payload.oauth_refresh_token)):
        db.add(AccountCredential(
            account_id=account.id,
            smtp_password_enc=encrypt_credential(payload.smtp_password) if payload.smtp_password else None,
            zeptomail_api_key_enc=encrypt_credential(payload.zeptomail_api_key) if payload.zeptomail_api_key else None,
            oauth_access_token_enc=encrypt_credential(payload.oauth_access_token) if payload.oauth_access_token else None,
            oauth_refresh_token_enc=encrypt_credential(payload.oauth_refresh_token) if payload.oauth_refresh_token else None,
        ))

    _log_activity(db, event_type="account_created", severity="info", message=f"Account '{account.name}' ({account.email}) [{account.provider}] created successfully.", entity_id=account.id)
    db.commit()
    db.refresh(account)
    return _account_response(account)


@router.post("/oauth-connect", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def oauth_connect(payload: OAuthConnectRequest, db: Session = Depends(get_db)):
    provider = _normalize_provider(payload.provider)
    if provider not in {"google", "microsoft"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth provider must be 'google' or 'microsoft'.")
    if not payload.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth account email is required.")
    if not payload.access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth access token is required.")

    existing = db.query(Account).filter(Account.email == payload.email, Account.provider == provider).first()
    if existing:
        account = existing
        account.name = payload.name
        if payload.from_name is not None:
            cleaned = payload.from_name.strip()
            if cleaned:
                account.from_name = cleaned
        elif not account.from_name:
            account.from_name = payload.name
        account.status = "active"
        account.updated_at = datetime.utcnow()
        _save_oauth_credentials(db, account.id, payload.access_token, payload.refresh_token)
    else:
        account = Account(
            provider=provider,
            name=payload.name,
            email=payload.email,
            from_name=(payload.from_name.strip() if payload.from_name and payload.from_name.strip() else payload.name),
            enabled=True,
            daily_limit=500,
            status="active",
        )
        db.add(account)
        db.flush()
        _save_oauth_credentials(db, account.id, payload.access_token, payload.refresh_token)

    _log_activity(db, event_type="oauth_connected", severity="info", message=f"OAuth2 account '{account.name}' ({account.email}) connected via {provider}.", entity_id=account.id)
    db.commit()
    db.refresh(account)
    return _account_response(account)


@router.put("/{account_id}", response_model=AccountResponse)
def update_account(account_id: int, payload: AccountUpdate, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")

    updates = payload.model_dump(exclude_unset=True)
    smtp_password = updates.pop("smtp_password", None)
    zeptomail_api_key = updates.pop("zeptomail_api_key", None)
    oauth_access_token = updates.pop("oauth_access_token", None)
    oauth_refresh_token = updates.pop("oauth_refresh_token", None)

    if "provider" in updates:
        updates["provider"] = _normalize_provider(updates["provider"])
    if "from_name" in updates and updates["from_name"] is not None:
        updates["from_name"] = updates["from_name"].strip() or None

    for field, value in updates.items():
        if hasattr(account, field):
            setattr(account, field, value)
    account.updated_at = datetime.utcnow()

    if any(v is not None for v in (smtp_password, zeptomail_api_key, oauth_access_token, oauth_refresh_token)):
        cred = _ensure_credentials(db, account.id)
        if smtp_password is not None:
            cred.smtp_password_enc = encrypt_credential(smtp_password) if smtp_password else None
        if zeptomail_api_key is not None:
            cred.zeptomail_api_key_enc = encrypt_credential(zeptomail_api_key) if zeptomail_api_key else None
        if oauth_access_token is not None:
            cred.oauth_access_token_enc = encrypt_credential(oauth_access_token) if oauth_access_token else None
        if oauth_refresh_token is not None:
            cred.oauth_refresh_token_enc = encrypt_credential(oauth_refresh_token) if oauth_refresh_token else None
        cred.updated_at = datetime.utcnow()

    _log_activity(db, event_type="account_updated", severity="info", message=f"Account '{account.name}' ({account.email}) updated successfully.", entity_id=account.id)
    db.commit()
    db.refresh(account)
    return _account_response(account)


@router.post("/{account_id}/test", status_code=status.HTTP_200_OK)
def test_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")

    cred = _get_credentials(db, account.id)
    provider = _normalize_provider(account.provider)

    if _is_oauth_provider(provider) or (cred and cred.oauth_access_token_enc):
        if not cred or not cred.oauth_access_token_enc:
            account.status = "error"
            db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth2 access token is missing. Reconnect the account.")
        account.status = "active"
        account.updated_at = datetime.utcnow()
        db.commit()
        return {"status": "success", "message": f"OAuth account '{account.name}' has a stored access token."}

    try:
        if provider == "zeptomail" or (cred and cred.zeptomail_api_key_enc):
            from backend.transports.zeptomail import ZeptoMailTransport
            api_key = decrypt_credential(cred.zeptomail_api_key_enc) if cred and cred.zeptomail_api_key_enc else ""
            transport = ZeptoMailTransport({"from_email": account.email, "from_name": account.from_name, "api_key": api_key})
            result = transport.test_connection()
            if result.status != "CONNECTED":
                raise Exception(result.message)
            account.status = "active"
            account.updated_at = datetime.utcnow()
            db.commit()
            return result.to_dict()

        if provider == "bell" or (account.smtp_host and "sympatico" in str(account.smtp_host).lower()):
            from backend.transports.bell import BellSympaticoTransport
            password = decrypt_credential(cred.smtp_password_enc) if cred and cred.smtp_password_enc else ""
            transport = BellSympaticoTransport({
                "from_email": account.email,
                "from_name": account.from_name or "",
                "host": account.smtp_host or "smtphm.sympatico.ca",
                "port": account.smtp_port or 587,
                "security": account.smtp_security or "starttls",
                "username": account.smtp_username or account.email,
                "password": password,
            })
            result = transport.test_connection()
            if str(getattr(result, "status", "")).upper() not in {"CONNECTED", "SUCCESS"}:
                raise Exception(getattr(result, "message", "Bell connection failed"))
            account.status = "active"
            account.updated_at = datetime.utcnow()
            db.commit()
            return result.to_dict() if hasattr(result, "to_dict") else {"status": "success", "message": result.message}

        from backend.transports.smtp import verify_smtp_auth
        password = decrypt_credential(cred.smtp_password_enc) if cred and cred.smtp_password_enc else ""
        verify_smtp_auth(
            host=account.smtp_host or "smtp.gmail.com",
            port=account.smtp_port or 587,
            security=account.smtp_security or "starttls",
            username=account.smtp_username or account.email,
            password=password,
        )
        account.status = "active"
        account.updated_at = datetime.utcnow()
        db.commit()
        return {"status": "success", "message": f"SMTP authentication successful for {account.email}."}

    except Exception as exc:
        account.status = "error"
        db.commit()
        diagnostic_msg = diagnose_smtp_error(str(exc)) if "diagnose_smtp_error" in dir() else str(exc)
        try:
            diagnostic_msg = diagnose_smtp_error(str(exc))
        except Exception:
            diagnostic_msg = str(exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=diagnostic_msg)


@router.post("/test-smtp", status_code=status.HTTP_200_OK)
def test_smtp_credentials(payload: dict):
    """Test raw SMTP credentials before saving them."""
    host = (payload.get("host") or "").strip()
    username = (payload.get("username") or "").strip()
    password = (payload.get("password") or "").strip()
    try:
        port = int(payload.get("port", 587))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SMTP port must be a valid number.")

    security = (payload.get("security") or "starttls").strip().lower()
    if security in {"tls", "start_tls"}:
        security = "starttls"
    if security in {"ssl/tls", "smtps"}:
        security = "ssl"

    if not host or not username or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Host, username/email, and password are required for SMTP testing.")

    host_l = host.lower()
    is_bell = (
        "sympatico" in host_l
        or "bell" in host_l
        or username.lower().endswith("@bell.net")
        or username.lower().endswith("@sympatico.ca")
    )

    if is_bell:
        from backend.transports.bell import BellSympaticoTransport
        transport = BellSympaticoTransport({
            "from_email": username,
            "from_name": "",
            "host": host or "smtphm.sympatico.ca",
            "port": port or 587,
            "security": security or "starttls",
            "username": username,
            "password": password,
        })
        result = transport.test_connection()
        status_val = str(getattr(result, "status", "") or "").upper()
        message = str(getattr(result, "message", "") or "")
        if status_val in {"CONNECTED", "SUCCESS", "SENT"}:
            return {"status": "success", "message": message}
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message or "Bell SMTP connection failed.")

    import smtplib
    import ssl
    import socket

    server = None
    try:
        context = ssl.create_default_context()
        timeout = 25
        if security == "ssl" or port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=timeout, context=context)
            server.ehlo()
        else:
            server = smtplib.SMTP(host, port, timeout=timeout)
            server.ehlo()
            if security == "starttls" or port == 587:
                server.starttls(context=context)
                server.ehlo()
        server.login(username, password)
        return {"status": "success", "message": f"SMTP authentication successful with {host}:{port} ({security})."}
    except smtplib.SMTPAuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"SMTP authentication failed: {exc}")
    except (smtplib.SMTPServerDisconnected, smtplib.SMTPException, OSError, socket.error) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SMTP server disconnected unexpectedly during TLS/auth handshake. {exc}",
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"SMTP connection failed: {exc}")
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                try:
                    server.close()
                except Exception:
                    pass


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")
    cred = _get_credentials(db, account.id)
    if cred:
        db.delete(cred)
    db.delete(account)
    db.commit()
    return None
