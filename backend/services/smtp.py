import smtplib
import ssl
import logging

logger = logging.getLogger(__name__)

def test_smtp_connection(host: str, port: int, security: str, username: str, password: str) -> dict:
    """
    Performs a real SMTP connection, TLS negotiation, and full authentication handshake.
    - STARTTLS (port 587): uses smtplib.SMTP, issues starttls()
    - SSL/TLS (port 465): uses smtplib.SMTP_SSL
    Returns success dict or raises detailed Exception on failure.
    """
    if not host or not username or not password:
        raise ValueError("Host, username, and password are required for SMTP testing.")

    try:
        logger.info(f"Connecting to SMTP host {host}:{port} with security '{security}' for user {username}")
        if security.lower() == "ssl" or port == 465:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, timeout=15, context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=15)
            server.ehlo()
            if security.lower() == "starttls":
                logger.info("Initiating STARTTLS handshake...")
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()

        logger.info(f"Authenticating with SMTP server {host}:{port} as {username}...")
        server.login(username, password)
        server.quit()
        logger.info(f"SMTP authentication successful for {username} on {host}:{port}")
        return {
            "success": True,
            "message": f"SMTP authentication successful with {host}:{port}",
            "host": host,
            "port": port,
            "security": security
        }
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication Error for {username}@{host}:{port}: {e.smtp_error}")
        raise RuntimeError(f"SMTP Authentication failed (Invalid username or password): {e.smtp_error.decode('utf-8', errors='ignore') if isinstance(e.smtp_error, bytes) else str(e)}")
    except smtplib.SMTPConnectError as e:
        logger.error(f"SMTP Connection Error to {host}:{port}: {e}")
        raise RuntimeError(f"Could not connect to SMTP server {host}:{port}: {e}")
    except smtplib.SMTPException as e:
        logger.error(f"SMTP Protocol Error for {host}:{port}: {e}")
        raise RuntimeError(f"SMTP protocol error: {str(e)}")
    except TimeoutError:
        logger.error(f"SMTP Connection Timeout to {host}:{port}")
        raise RuntimeError(f"Connection timed out while connecting to {host}:{port}")
    except Exception as e:
        logger.error(f"Unexpected SMTP test error for {host}:{port}: {e}")
        raise RuntimeError(f"SMTP connection failed: {str(e)}")
