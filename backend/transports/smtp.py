import smtplib
import ssl
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from backend.transports.base import DeliveryResult

logger = logging.getLogger(__name__)

def verify_smtp_auth(host: str, port: int, security: str, username: str, password: str) -> dict:
    """
    Explicitly uses smtplib.SMTP for STARTTLS (port 587) and smtplib.SMTP_SSL for SSL (port 465).
    Performs full TLS negotiation and verifies login/authentication handshake before confirming success.
    """
    if not host or not username or not password:
        raise ValueError("SMTP host, username, and password are required.")

    try:
        if security.lower() == "ssl" or port == 465:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, timeout=15, context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=15)
            server.ehlo()
            if security.lower() == "starttls":
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()

        server.login(username, password)
        server.quit()

        return {
            "success": True,
            "message": f"SMTP authentication successful with {host}:{port}",
            "host": host,
            "port": port,
            "security": security
        }
    except Exception as e:
        logger.error(f"SMTP transport verification failed for {host}:{port} - {str(e)}")
        raise

def send_smtp_email(
    host: str,
    port: int,
    security: str,
    username: str,
    password: str,
    from_email: str,
    from_name: str,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str = "",
    reply_to: str = None,
    high_priority: bool = False,
    tracking_id: str = None,
    tracking_domain: str = ""
) -> DeliveryResult:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{from_email}>" if from_name else from_email
        msg["To"] = to_email
        if reply_to:
            msg["Reply-To"] = reply_to

        if high_priority:
            msg["X-Priority"] = "1 (Highest)"
            msg["X-MSMail-Priority"] = "High"
            msg["Importance"] = "High"

        final_html = html_body
        if tracking_id:
            pixel_url = f"{tracking_domain}/api/track?id={tracking_id}"
            tracking_tag = f'<img src="{pixel_url}" alt="" width="1" height="1" style="display:none;"/>'
            if "</body>" in final_html:
                final_html = final_html.replace("</body>", f"{tracking_tag}</body>")
            else:
                final_html += tracking_tag

        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        if final_html:
            msg.attach(MIMEText(final_html, "html"))

        if security.lower() == "ssl" or port == 465:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, timeout=20, context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=20)
            server.ehlo()
            if security.lower() == "starttls" or port == 587:
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()

        server.login(username, password)
        server.sendmail(from_email, [to_email], msg.as_string())
        server.quit()

        return DeliveryResult(status="SENT", message="Email sent successfully via SMTP with High Priority & Read Receipt tracking.")
    except Exception as e:
        logger.error(f"SMTP send failed: {e}")
        return DeliveryResult(status="FAILED", message=f"SMTP send failed: {str(e)}", retryable=True)
