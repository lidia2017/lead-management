"""Notification dispatch.

Sending is keyed by ``lead_id`` (not a passed-in object) so the exact same code
path works whether it runs inline in a BackgroundTask or in a separate Celery
worker process that must re-load the lead from the database.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import BackgroundTasks
from sqlmodel import Session

from app.core.config import settings
from app.core.database import engine
from app.models import Lead
from app.services.email.factory import send_lead_emails

logger = logging.getLogger("notifications")


def send_lead_notifications(lead_id: str | uuid.UUID) -> None:
    """Load the lead and send both emails. Safe to call from any process."""
    with Session(engine) as session:
        lead = session.get(Lead, uuid.UUID(str(lead_id)))
        if lead is None:
            logger.warning("Lead %s not found; skipping notifications", lead_id)
            return
        send_lead_emails(lead)


def dispatch_lead_notifications(
    lead_id: uuid.UUID, background_tasks: BackgroundTasks
) -> None:
    """Route the work: enqueue to Celery, or run inline after the response."""
    if settings.email_delivery.lower() == "celery":
        # Imported lazily so the inline path (and tests) never import Celery.
        from app.worker import send_lead_emails_task

        send_lead_emails_task.delay(str(lead_id))
        logger.info("Enqueued lead notifications for %s", lead_id)
    else:
        background_tasks.add_task(send_lead_notifications, str(lead_id))
