"""Lead business logic: creation, listing, and state transitions.

Keeping the rules here (not in the route handlers) means the state machine is
enforced in one place and is trivially unit-testable.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlmodel import Session, func, select

from app.models import Lead, LeadState
from app.services.storage import FileStorage

logger = logging.getLogger("lead_service")

# Allowed transitions: from-state -> set of valid to-states.
_ALLOWED_TRANSITIONS: dict[LeadState, set[LeadState]] = {
    LeadState.PENDING: {LeadState.REACHED_OUT},
    LeadState.REACHED_OUT: set(),
}


class LeadValidationError(ValueError):
    """Raised for invalid input (bad file type/size)."""


class InvalidStateTransition(Exception):
    """Raised when an illegal state transition is attempted."""


def validate_resume(content_type: str, size: int, allowed_types: list[str], max_bytes: int) -> None:
    if size <= 0:
        raise LeadValidationError("Resume file is empty.")
    if size > max_bytes:
        raise LeadValidationError(
            f"Resume exceeds the maximum size of {max_bytes // (1024 * 1024)} MB."
        )
    if content_type not in allowed_types:
        raise LeadValidationError(
            f"Unsupported resume type '{content_type}'. Allowed: {', '.join(allowed_types)}."
        )


def create_lead(
    session: Session,
    *,
    first_name: str,
    last_name: str,
    email: str,
    resume_bytes: bytes,
    resume_filename: str,
    resume_content_type: str,
    storage: FileStorage,
) -> Lead:
    stored_path = storage.save(resume_bytes, resume_filename)
    lead = Lead(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        email=email.strip().lower(),
        resume_filename=resume_filename,
        resume_path=stored_path,
        resume_content_type=resume_content_type,
        state=LeadState.PENDING,
    )
    session.add(lead)
    try:
        session.commit()
    except Exception:
        # The blob is already written; if the row didn't persist, don't leave
        # an orphaned file behind.
        session.rollback()
        try:
            storage.delete(stored_path)
        except Exception:
            logger.warning("Failed to clean up orphaned resume %s", stored_path)
        raise
    session.refresh(lead)
    return lead


def list_leads(
    session: Session,
    *,
    state: LeadState | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Lead], int]:
    stmt = select(Lead)
    count_stmt = select(func.count()).select_from(Lead)
    if state is not None:
        stmt = stmt.where(Lead.state == state)
        count_stmt = count_stmt.where(Lead.state == state)
    stmt = stmt.order_by(Lead.created_at.desc()).offset(offset).limit(limit)
    items = list(session.exec(stmt).all())
    total = session.exec(count_stmt).one()
    return items, total


def get_lead(session: Session, lead_id: uuid.UUID) -> Lead | None:
    return session.get(Lead, lead_id)


def transition_state(session: Session, lead: Lead, new_state: LeadState) -> Lead:
    if new_state == lead.state:
        return lead  # idempotent no-op
    if new_state not in _ALLOWED_TRANSITIONS.get(lead.state, set()):
        raise InvalidStateTransition(
            f"Cannot transition from {lead.state.value} to {new_state.value}."
        )
    lead.state = new_state
    lead.updated_at = datetime.now(timezone.utc)
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return lead
