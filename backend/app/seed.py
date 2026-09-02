"""Seed the initial attorney user if none exists."""
from __future__ import annotations

import logging

from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import engine
from app.core.security import hash_password
from app.models import User

logger = logging.getLogger("seed")


def seed_attorney() -> None:
    with Session(engine) as session:
        existing = session.exec(select(User)).first()
        if existing is not None:
            return
        user = User(
            email=settings.seed_attorney_email.lower(),
            hashed_password=hash_password(settings.seed_attorney_password),
            full_name=settings.seed_attorney_name,
            role="attorney",
        )
        session.add(user)
        session.commit()
        logger.info("Seeded attorney user: %s", settings.seed_attorney_email)
