from backend.security.encryption import decrypt_credential


def _result_ok(result) -> bool:
    if result is None:
        return True
    status = str(getattr(result, "status", "") or "").upper()
    if not status:
        return True
    return status in {"SENT", "SUCCESS"}


def dispatch_email_message(
    account,
    recipient: str,
    subject: str,
    body: str,
    from_name: str = "",
    high_priority: bool = False,
    reply_to: str = "",
):
    """
    Route a campaign (or single) send through the correct transport for the account.

    Supports:
      - microsoft / outlook  → SMTP + XOAUTH2 (preserves From Name)
      - google / gmail       → Gmail API
      - zeptomail            → ZeptoMail API
      - bell                 → Bell/Sympatico SMTP
      - smtp (default)       → generic SMTP
    """
    credential = getattr(account, "credential", None)
    provider_type = (account.provider or "smtp").strip().lower()
    sender_name = from_name or account.from_name or ""
    effective_reply = (reply_to or "").strip() or None

    # ---------------------------------------------------------
    # Microsoft / Outlook — SMTP + XOAUTH2
    # ---------------------------------------------------------
    if provider_type in {"microsoft", "outlook"}:
        if not credential or not credential.oauth_access_token_enc:
            raise RuntimeError(
                "Microsoft OAuth access token is missing. Reconnect the Outlook account."
            )

        from backend.transports.microsoft_smtp import MicrosoftSmtpTransport

        access_token = decrypt_credential(credential.oauth_access_token_enc)
        refresh_token = ""
        if credential.oauth_refresh_token_enc:
            refresh_token = decrypt_credential(credential.oauth_refresh_token_enc)

        transport = MicrosoftSmtpTransport(
            access_token=access_token,
            from_email=account.email,
            from_name=sender_name,
            refresh_token=refresh_token,
            smtp_host=getattr(account, "smtp_host", None) or "smtp.office365.com",
            smtp_port=getattr(account, "smtp_port", None) or 587,
        )
        result = transport.send_email(
            to_email=recipient,
            subject=subject,
            html_body=body,
            high_priority=high_priority,
            reply_to=effective_reply,
        )
        if not _result_ok(result):
            raise RuntimeError(getattr(result, "message", None) or "Microsoft SMTP send failed")
        return result

    # ---------------------------------------------------------
    # Google / Gmail — Gmail API
    # ---------------------------------------------------------
    if provider_type in {"google", "gmail"}:
        if not credential or not credential.oauth_access_token_enc:
            raise RuntimeError(
                "Google OAuth access token is missing. Reconnect the Gmail account."
            )

        from backend.transports.google import GmailApiTransport

        access_token = decrypt_credential(credential.oauth_access_token_enc)
        refresh_token = ""
        if credential.oauth_refresh_token_enc:
            refresh_token = decrypt_credential(credential.oauth_refresh_token_enc)

        transport = GmailApiTransport(
            access_token=access_token,
            refresh_token=refresh_token,
            from_email=account.email,
            from_name=sender_name,
        )
        result = transport.send_email(
            to_email=recipient,
            subject=subject,
            html_body=body,
            high_priority=high_priority,
            reply_to=effective_reply,
        )
        if not _result_ok(result):
            raise RuntimeError(getattr(result, "message", None) or "Gmail API send failed")
        return result

    # ---------------------------------------------------------
    # ZeptoMail API
    # ---------------------------------------------------------
    if provider_type == "zeptomail" or (
        credential and getattr(credential, "zeptomail_api_key_enc", None)
    ):
        from backend.transports.zeptomail import ZeptoMailTransport

        api_key = (
            decrypt_credential(credential.zeptomail_api_key_enc)
            if credential and credential.zeptomail_api_key_enc
            else ""
        )
        transport = ZeptoMailTransport(
            {
                "from_email": account.email,
                "from_name": sender_name,
                "api_key": api_key,
                "reply_to": effective_reply or "",
            }
        )
        result = transport.send_email(
            to_email=recipient,
            subject=subject,
            html_body=body,
            high_priority=high_priority,
            reply_to=effective_reply,
        )
        if not _result_ok(result):
            raise RuntimeError(getattr(result, "message", None) or "ZeptoMail send failed")
        return result

    password = (
        decrypt_credential(credential.smtp_password_enc)
        if credential and credential.smtp_password_enc
        else ""
    )

    # ---------------------------------------------------------
    # Bell / Sympatico SMTP
    # ---------------------------------------------------------
    if provider_type == "bell" or (
        account.smtp_host and "sympatico" in str(account.smtp_host).lower()
    ):
        from backend.transports.bell import BellSympaticoTransport

        transport = BellSympaticoTransport(
            {
                "from_email": account.email,
                "from_name": sender_name,
                "host": account.smtp_host or "smtphm.sympatico.ca",
                "port": account.smtp_port or 587,
                "security": account.smtp_security or "starttls",
                "username": account.smtp_username or account.email,
                "password": password,
            }
        )
        result = transport.send_email(
            to_email=recipient,
            subject=subject,
            html_body=body,
            high_priority=high_priority,
            reply_to=effective_reply,
        )
        if not _result_ok(result):
            raise RuntimeError(getattr(result, "message", None) or "Bell SMTP send failed")
        return result

    # ---------------------------------------------------------
    # Generic SMTP
    # ---------------------------------------------------------
    from backend.transports.smtp import send_smtp_email

    result = send_smtp_email(
        host=account.smtp_host or "smtp.gmail.com",
        port=account.smtp_port or 587,
        security=account.smtp_security or "starttls",
        username=account.smtp_username or account.email,
        password=password,
        from_email=account.email,
        from_name=sender_name,
        to_email=recipient,
        subject=subject,
        html_body=body,
        reply_to=effective_reply,
        high_priority=high_priority,
    )
    if not _result_ok(result):
        raise RuntimeError(getattr(result, "message", None) or "SMTP send failed")
    return result
