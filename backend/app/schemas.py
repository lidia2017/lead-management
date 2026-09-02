"""Pydantic request/response schemas (the API contract)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import LeadState


class LeadRead(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr
    resume_filename: str
    resume_content_type: str
    state: LeadState
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeadList(BaseModel):
    items: list[LeadRead]
    total: int
    limit: int
    offset: int


class LeadUpdate(BaseModel):
    # Only the state is mutable from the internal UI.
    state: LeadState


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str

    model_config = ConfigDict(from_attributes=True)
