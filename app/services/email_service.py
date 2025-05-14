# app/services/email_service.py
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_email_blocking(
    smtp_server: str,
    smtp_port: int,
    msg: MIMEMultipart,
    smtp_user: str | None,
    smtp_password: str | None,
    use_tls: bool,
):
    """
    Blocking helper function to send email.
    This function is intended to be run in a separate thread.
    """
    with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:  # Added timeout
        if use_tls:
            server.starttls()
        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)
        server.send_message(msg)


async def send_email_async(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str | None = None,
) -> bool:
    """
    Asynchronously sends an email.

    Args:
        to_email: The recipient's email address.
        subject: The subject of the email.
        html_content: The HTML content of the email.
        text_content: Optional plain text content of the email. If not provided,
        a simple text version might be derived or skipped.

    Returns:
        True if the email was sent successfully (or simulated in dev), False otherwise.
    """
    if not all(
        [
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            settings.SMTP_USER,
            # settings.SMTP_PASSWORD, # Password can be None for some local SMTP servers
            settings.EMAILS_FROM_EMAIL,
        ]
    ):
        logger.warning(
            "SMTP settings (SMTP_HOST, SMTP_PORT, SMTP_USER, EMAILS_FROM_EMAIL) "
            "are not fully configured. Email sending skipped."
        )
        if settings.ENVIRONMENT == "development":
            logger.info(f"DEV MODE: Email simulation for {to_email} with subject '{subject}'")
            logger.debug(f"HTML Content (first 200 chars): {html_content[:200]}...")
            logger.debug(f"Text Content (first 200 chars): {str(text_content)[:200]}...")
            return True  # Simulate success in dev if not configured for actual sending
        return False

    # Construct From header
    from_header = settings.EMAILS_FROM_EMAIL
    if settings.EMAILS_FROM_NAME:
        from_header = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_header
    msg["To"] = to_email

    # Attach plain text part first, then HTML part
    if text_content:
        part1 = MIMEText(text_content, "plain", "utf-8")
        msg.attach(part1)
    else:
        # Fallback plain text if not provided (simple extraction, can be improved)
        # For robustness, it's better to always provide explicit text_content
        import re

        fallback_text = re.sub("<[^<]+?>", "", html_content)  # Basic HTML strip
        part1 = MIMEText(fallback_text[:500], "plain", "utf-8")  # Limit length
        msg.attach(part1)

    part2 = MIMEText(html_content, "html", "utf-8")
    msg.attach(part2)

    try:
        # smtplib is blocking, so run it in a separate thread using asyncio.to_thread
        await asyncio.to_thread(
            _send_email_blocking,
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            msg,
            settings.SMTP_USER,
            settings.SMTP_PASSWORD,
            settings.SMTP_TLS,
        )
        logger.info(f"Email sent successfully to {to_email} with subject: {subject}")
        return True
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error while sending email to {to_email}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error sending email to {to_email}: {e}", exc_info=True)
    return False
