"""SendGrid backend — a thin HTTP adapter (no SDK dependency).

Selected via ``EMAIL_BACKEND=sendgrid`` with ``SENDGRID_API_KEY`` set. Shown to
demonstrate that swapping to a real provider is a self-contained change.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings
from app.services.email.base import EmailMessage, EmailService

logger = logging.getLogger("email.sendgrid")

SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


class SendgridEmailService(EmailService):
    def send(self, message: EmailMessage) -> None:
        if not settings.sendgrid_api_key:
            logger.error("SENDGRID_API_KEY not configured; dropping email to %s", message.to)
            return

        payload = {
            "personalizations": [{"to": [{"email": message.to}]}],
            "from": {"email": message.sender},
            "subject": message.subject,
            "content": [{"type": "text/plain", "value": message.body}],
        }
        headers = {
            "Authorization": f"Bearer {settings.sendgrid_api_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = httpx.post(SENDGRID_URL, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            logger.info("Sent email to %s via SendGrid", message.to)
        except Exception:  # pragma: no cover - network dependent
            logger.exception("Failed to send email to %s via SendGrid", message.to)
