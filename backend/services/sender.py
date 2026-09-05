from backend.security.encryption import decrypt_credential


def dispatch_email_message(
    account,
    recipient: str,
    subject: str,
    body: str,
    from_name: str = "",
    high_priority: bool = False,
    reply_to: str = "",
):
    credential = getattr(account, "credential", None)
    provider_type = account.provider or "smtp"
    sender_name = from_name or account.from_name or ""

    if provider_type == "zeptomail" or (
        credential and credential.zeptomail_api_key_enc
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
            }
        )
        return transport.send_email(
            to_email=recipient,
            subject=subject,
            html_body=body,
            high_priority=high_priority,
        )

    password = (
        decrypt_credential(credential.smtp_password_enc)
        if credential and credential.smtp_password_enc
        else ""
    )

    if provider_type == "bell" or (
        account.smtp_host and "sympatico" in account.smtp_host.lower()
    ):
        from backend.transports.bell import BellSympaticoTransport

        transport = BellSympaticoTransport(
            {
                "from_email": account.email,
                "from_name": sender_name,
                "host": account.smtp_host,
                "port": account.smtp_port or 587,
                "security": account.smtp_security or "starttls",
                "username": account.smtp_username or account.email,
                "password": password,
            }
        )
        return transport.send_email(
            to_email=recipient,
            subject=subject,
            html_body=body,
            high_priority=high_priority,
        )

    from backend.transports.smtp import send_smtp_email

    return send_smtp_email(
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
        reply_to=reply_to or None,
        high_priority=high_priority,
    )
