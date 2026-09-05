import smtplib
import socket
import ssl
import logging

logger = logging.getLogger(__name__)

def diagnose_smtp_error(e: Exception) -> str:
    """
    Maps smtplib exceptions (socket, timeout, auth) into clear, non-sensitive diagnostic messages for the UI.
    """
    err_str = str(e)
    if isinstance(e, smtplib.SMTPAuthenticationError):
        code, resp = e.smtp_code, e.smtp_error
        resp_msg = resp.decode('utf-8', errors='ignore') if isinstance(resp, bytes) else str(resp)
        return f"SMTP Authentication failed (Code {code}): Invalid username or password ({resp_msg})"
    elif isinstance(e, smtplib.SMTPConnectError):
        return f"SMTP Connection failed: Server refused connection or is unreachable."
    elif isinstance(e, smtplib.SMTPServerDisconnected):
        return f"SMTP server disconnected unexpectedly during TLS/auth handshake."
    elif isinstance(e, socket.timeout) or isinstance(e, TimeoutError):
        return f"SMTP Connection timed out. Please verify host and port."
    elif isinstance(e, socket.gaierror):
        return f"DNS resolution failed: Could not resolve SMTP host."
    elif isinstance(e, ssl.SSLError):
        return f"TLS/SSL negotiation failed: {err_str}"
    else:
        return f"SMTP error: {err_str}"
