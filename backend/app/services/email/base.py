"""Email service interface + a small message value object."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EmailMessage:
    to: str
    subject: str
    body: str
    sender: str


class EmailService(ABC):
    @abstractmethod
    def send(self, message: EmailMessage) -> None:
        """Deliver a single message. Implementations should not raise on
        transient failures in a way that breaks the caller — the caller runs
        this in a background task and logs failures."""
