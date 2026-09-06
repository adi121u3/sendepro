import os
import base64
import json
import logging
import requests
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from urllib.parse import urlencode
from backend.database import get_db
from backend.models import Account, AccountCredential, ActivityLog
from backend.security.encryption import encrypt_credential, decrypt_credential

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/oauth", tags=["oauth"])


def _required_client_id(provider: str) -> str:
    env_name = "GOOGLE_CLIENT_ID" if provider == "google" else "MICROSOFT_CLIENT_ID"
    client_id = os.getenv(env_name, "").strip()
    if not client_id:
        raise HTTPException(
            status_code=503,
            detail=f"{env_name} is not configured. Add the OAuth client ID to the backend environment.",
        )
    return client_id


def _redirect_uri(provider: str) -> str:
    env_name = "MICROSOFT_REDIRECT_URI" if provider == "microsoft" else "GOOGLE_REDIRECT_URI"
    redirect_uri = os.getenv(env_name, "").strip() or os.getenv("OAUTH_REDIRECT_URI", "").strip()
    if not redirect_uri:
        raise HTTPException(
            status_code=503,
            detail=f"{env_name} or OAUTH_REDIRECT_URI is not configured.",
        )
    return redirect_uri


def _microsoft_authority() -> str:
    tenant_id = os.getenv("MICROSOFT_TENANT_ID", "common").strip() or "common"
    return f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0"


# IMPORTANT:
# Microsoft does NOT allow mixing different resource scopes in one token.
# outlook.office.com + graph.microsoft.com together => AADSTS70011 invalid_scope.
#
# For Aerion-style SMTP + XOAUTH2 we only need:
#   https://outlook.office.com/SMTP.Send
# plus OIDC scopes for identity (openid / email / profile / offline_access).
MICROSOFT_SCOPES = (
    "openid offline_access email profile "
    "https://outlook.office.com/SMTP.Send"
)


def _decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without signature verification (identity claims only)."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return {}
        payload = parts[1]
        padding = "=" * (-len(payload) % 4)
        raw = base64.urlsafe_b64decode(payload + padding)
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning("Failed to decode id_token: %s", exc)
        return {}


def _microsoft_identity(token_data: dict, access_token: str) -> tuple[str, str]:
    """
    Resolve email + display name for a Microsoft SMTP token.

    Prefer OIDC id_token claims (works with outlook.office.com resource).
    Graph /me will NOT accept an outlook.office.com access token.
    """
    email = ""
    name = ""

    id_token = token_data.get("id_token") or ""
    if id_token:
        claims = _decode_jwt_payload(id_token)
        email = (
            claims.get("email")
            or claims.get("preferred_username")
            or claims.get("upn")
            or ""
        )
        name = claims.get("name") or claims.get("given_name") or ""

    # Fallback: some tenants put username in the access token audience flow only
    if not email and access_token:
        claims = _decode_jwt_payload(access_token)
        email = (
            claims.get("email")
            or claims.get("unique_name")
            or claims.get("upn")
            or claims.get("preferred_username")
            or ""
        )
        if not name:
            name = claims.get("name") or ""

    email = str(email or "").strip()
    name = str(name or "").strip() or email
    return email, name


@router.get("/authorize")
def oauth_authorize(provider: str = Query(..., description="google or microsoft")):
    """Initiates browser-based OAuth2 authorization flow for Gmail or Microsoft 365."""
    provider = provider.lower()

    if provider == "google":
        redirect_uri = _redirect_uri("google")
        auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
            "client_id": _required_client_id("google"),
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": (
                "https://www.googleapis.com/auth/gmail.send "
                "https://www.googleapis.com/auth/userinfo.email "
                "https://www.googleapis.com/auth/userinfo.profile"
            ),
            "access_type": "offline",
            "prompt": "consent",
            "state": "google",
        })
    elif provider in ["microsoft", "outlook"]:
        provider = "microsoft"
        redirect_uri = _redirect_uri(provider)
        auth_url = _microsoft_authority() + "/authorize?" + urlencode({
            "client_id": _required_client_id("microsoft"),
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "response_mode": "query",
            "scope": MICROSOFT_SCOPES,
            "prompt": "consent",
            "state": "microsoft",
        })
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported OAuth provider: {provider}")

    return RedirectResponse(url=auth_url)


@router.get("/callback")
def oauth_callback(
    code: str = Query(...),
    state: str = Query(None),
    provider: str = Query(None, description="google or microsoft"),
    db: Session = Depends(get_db),
):
    """Handles OAuth callback, exchanges code for tokens, stores account + credentials."""
    try:
        provider = (provider or state or "").lower()
        if provider == "outlook":
            provider = "microsoft"
        if provider not in {"google", "microsoft"}:
            raise HTTPException(status_code=400, detail="OAuth provider is missing or unsupported.")

        client_secret_name = "GOOGLE_CLIENT_SECRET" if provider == "google" else "MICROSOFT_CLIENT_SECRET"
        client_secret = os.getenv(client_secret_name, "").strip()
        if not client_secret:
            raise HTTPException(
                status_code=503,
                detail=f"{client_secret_name} is not configured. Add the OAuth client secret to the backend environment.",
            )

        client_id = _required_client_id(provider)
        redirect_uri = _redirect_uri(provider)
        token_url = (
            "https://oauth2.googleapis.com/token"
            if provider == "google"
            else _microsoft_authority() + "/token"
        )
        token_data_payload = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        if provider == "microsoft":
            token_data_payload["scope"] = MICROSOFT_SCOPES

        token_response = requests.post(token_url, data=token_data_payload, timeout=20)
        if not token_response.ok:
            try:
                provider_error = token_response.json()
                error_code = provider_error.get("error", "unknown_error")
                error_description = provider_error.get("error_description", "")
                detail = f"{error_code}: {error_description}".strip(": ")
            except ValueError:
                detail = token_response.text[:500] or token_response.reason
            raise HTTPException(
                status_code=400,
                detail=f"{provider.capitalize()} token exchange failed: {detail}",
            )

        token_data = token_response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token", "")
        if not access_token:
            raise HTTPException(status_code=400, detail="OAuth provider did not return an access token.")

        if provider == "google":
            profile_response = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=20,
            )
            profile_response.raise_for_status()
            profile = profile_response.json()
            email = profile.get("email") or ""
            name = profile.get("name") or email
        else:
            email, name = _microsoft_identity(token_data, access_token)

        email = str(email or "").strip()
        name = str(name or "").strip() or email
        if not email:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Microsoft did not return an email address in the token. "
                    "Ensure the app registration allows personal Microsoft accounts "
                    "and that email/profile scopes are granted."
                ),
            )

        expires_in = int(token_data.get("expires_in", 3600))

        existing = db.query(Account).filter(Account.email == email, Account.provider == provider).first()
        if existing:
            account = existing
            account.name = name
            account.status = "active"
            account.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(account)

            cred = db.query(AccountCredential).filter(AccountCredential.account_id == account.id).first()
            if cred:
                cred.oauth_access_token_enc = encrypt_credential(access_token)
                if refresh_token:
                    cred.oauth_refresh_token_enc = encrypt_credential(refresh_token)
                cred.oauth_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                cred.updated_at = datetime.utcnow()
            else:
                cred = AccountCredential(
                    account_id=account.id,
                    oauth_access_token_enc=encrypt_credential(access_token),
                    oauth_refresh_token_enc=encrypt_credential(refresh_token or ""),
                    oauth_token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                )
                db.add(cred)
            db.commit()
        else:
            account = Account(
                provider=provider,
                name=name,
                email=email,
                from_name=name,
                enabled=True,
                daily_limit=500,
                status="active",
            )
            db.add(account)
            db.commit()
            db.refresh(account)

            cred = AccountCredential(
                account_id=account.id,
                oauth_access_token_enc=encrypt_credential(access_token),
                oauth_refresh_token_enc=encrypt_credential(refresh_token or ""),
                oauth_token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
            )
            db.add(cred)
            db.commit()

        log = ActivityLog(
            event_type="oauth_connected",
            severity="info",
            message=f"OAuth2 browser flow completed for {email} via {provider} (SMTP.Send).",
            entity_id=account.id,
        )
        db.add(log)
        db.commit()

        html_content = f"""
        <html>
            <head>
                <title>OAuth Authorization Successful</title>
                <style>
                    body {{ font-family: sans-serif; background: #020617; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
                    .card {{ background: #0f172a; border: 1px solid #1e293b; padding: 32px; border-radius: 16px; text-align: center; max-width: 400px; box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.5); }}
                    h2 {{ color: #34d399; margin-bottom: 12px; }}
                    p {{ color: #94a3b8; font-size: 14px; margin-bottom: 24px; }}
                    .btn {{ background: #f59e0b; color: #020617; font-weight: bold; padding: 10px 20px; border-radius: 8px; text-decoration: none; display: inline-block; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h2>✓ OAuth Authorization Successful</h2>
                    <p>Successfully authenticated <b>{email}</b> with Microsoft SMTP. You can close this window.</p>
                    <a href="/" class="btn" onclick="window.close();">Return to App</a>
                </div>
                <script>
                    setTimeout(() => {{
                        if (window.opener) {{
                            window.opener.location.reload();
                            window.close();
                        }}
                    }}, 1500);
                </script>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth callback error: {str(e)}")
