"""Selects the configured email backend and builds the two lead emails."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.models import Lead
from app.services.email.base import EmailMessage, EmailService
from app.services.email.console import ConsoleEmailService
from app.services.email.sendgrid import SendgridEmailService
from app.services.email.smtp import SmtpEmailService


@lru_cache
def get_email_service() -> EmailService:
    backend = settings.email_backend.lower()
    if backend == "smtp":
        return SmtpEmailService()
    if backend == "sendgrid":
        return SendgridEmailService()
    return ConsoleEmailService()


def build_prospect_email(lead: Lead) -> EmailMessage:
    return EmailMessage(
        to=lead.email,
        sender=settings.email_from,
        subject="We received your submission",
        body=(
            f"Hi {lead.first_name},\n\n"
            "Thank you for submitting your information. Our team has received "
            "your details and an attorney will reach out to you shortly.\n\n"
            "Best regards,\nThe Legal Team"
        ),
    )


def build_attorney_email(lead: Lead) -> EmailMessage:
    return EmailMessage(
        to=settings.attorney_notify_email,
        sender=settings.email_from,
        subject=f"New lead: {lead.first_name} {lead.last_name}",
        body=(
            "A new lead has been submitted.\n\n"
            f"Name:  {lead.first_name} {lead.last_name}\n"
            f"Email: {lead.email}\n"
            f"Lead ID: {lead.id}\n"
            f"State: {lead.state.value}\n\n"
            "Review it in the internal dashboard and mark it REACHED_OUT once "
            "you have contacted the prospect."
        ),
    )


def send_lead_emails(lead: Lead) -> None:
    """Send both emails. Runs inside a FastAPI BackgroundTask."""
    service = get_email_service()
    service.send(build_prospect_email(lead))
    service.send(build_attorney_email(lead))
