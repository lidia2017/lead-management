"""SMTP email backend — works with MailHog in dev or any SMTP server."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage as MimeMessage

from app.core.config import settings
from app.services.email.base import EmailMessage, EmailService

logger = logging.getLogger("email.smtp")


class SmtpEmailService(EmailService):
    def send(self, message: EmailMessage) -> None:
        mime = MimeMessage()
        mime["From"] = message.sender
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.body)

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                if settings.smtp_username and settings.smtp_password:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(mime)
            logger.info("Sent email to %s via SMTP", message.to)
        except Exception:  # pragma: no cover - network dependent
            logger.exception("Failed to send email to %s via SMTP", message.to)
