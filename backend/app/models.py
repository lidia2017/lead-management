"""SQLModel ORM models."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LeadState(str, enum.Enum):
    PENDING = "PENDING"
    REACHED_OUT = "REACHED_OUT"


class Lead(SQLModel, table=True):
    __tablename__ = "leads"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    first_name: str
    last_name: str
    email: str = Field(index=True)

    resume_filename: str
    resume_path: str
    resume_content_type: str

    state: LeadState = Field(default=LeadState.PENDING, index=True)

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    full_name: str
    role: str = Field(default="attorney")
    created_at: datetime = Field(default_factory=_utcnow)
