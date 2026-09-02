"""Celery worker for durable, retryable email delivery.

Run with:
    celery -A app.worker.celery_app worker --loglevel=info

Moving email off the request path means a slow or down mail provider never
blocks (or loses) a lead submission: the API enqueues and returns immediately,
and the worker pool scales independently of the API.
"""
from __future__ import annotations

import logging

from celery import Celery

from app.core.config import settings
from app.services.notifications import send_lead_notifications

logger = logging.getLogger("worker")

celery_app = Celery(
    "lead_management",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=10,
    task_time_limit=60,
)


@celery_app.task(
    name="send_lead_emails",
    bind=True,
    max_retries=5,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def send_lead_emails_task(self, lead_id: str) -> None:
    logger.info("Worker sending notifications for lead %s", lead_id)
    send_lead_notifications(lead_id)
