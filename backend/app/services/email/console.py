"""Console email backend — prints messages to stdout.

Perfect for local dev and tests: proves the send seam without any external
account. Also used as a safe default.
"""
from __future__ import annotations

import logging

from app.services.email.base import EmailMessage, EmailService

logger = logging.getLogger("email.console")


class ConsoleEmailService(EmailService):
    def send(self, message: EmailMessage) -> None:
        logger.info(
            "\n===== EMAIL (console backend) =====\n"
            "From: %s\nTo: %s\nSubject: %s\n\n%s\n"
            "===================================",
            message.sender,
            message.to,
            message.subject,
            message.body,
        )
