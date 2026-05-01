"""
Email Service - Handles sending emails via SMTP.
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Handles email sending via SMTP."""

    async def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send an email. Returns True on success."""
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.info(f"Email service not configured. Would send to {to_email}: {subject}")
            # Return True in demo mode to simulate sending
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.FROM_EMAIL
            msg["To"] = to_email

            # Plain text version
            text_part = MIMEText(body, "plain")
            msg.attach(text_part)

            # HTML version (basic formatting)
            html_body = body.replace("\n", "<br>")
            html_part = MIMEText(f"<html><body><p>{html_body}</p></body></html>", "html")
            msg.attach(html_part)

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.FROM_EMAIL, to_email, msg.as_string())

            logger.info(f"Email sent to {to_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
