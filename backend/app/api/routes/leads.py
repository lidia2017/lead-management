"""Lead routes: public creation + authenticated management."""
from __future__ import annotations

import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response
from pydantic import EmailStr, ValidationError
from pydantic import TypeAdapter
from sqlmodel import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_session
from app.models import LeadState, User
from app.schemas import LeadList, LeadRead, LeadUpdate
from app.services import lead_service
from app.services.email.factory import send_lead_emails
from app.services.storage import FileStorage, get_storage

router = APIRouter(prefix="/api/leads", tags=["leads"])

_email_adapter = TypeAdapter(EmailStr)


@router.post("", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
async def create_lead(
    background_tasks: BackgroundTasks,
    first_name: str = Form(..., min_length=1, max_length=100),
    last_name: str = Form(..., min_length=1, max_length=100),
    email: str = Form(...),
    resume: UploadFile = File(...),
    session: Session = Depends(get_session),
    storage: FileStorage = Depends(get_storage),
) -> LeadRead:
    """Public endpoint. A prospect submits the lead form (multipart)."""
    # Validate email format explicitly (multipart fields are plain strings).
    try:
        _email_adapter.validate_python(email)
    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid email address.",
        )

    contents = await resume.read()
    try:
        lead_service.validate_resume(
            content_type=resume.content_type or "application/octet-stream",
            size=len(contents),
            allowed_types=settings.allowed_resume_types_list,
            max_bytes=settings.max_upload_bytes,
        )
    except lead_service.LeadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    lead = lead_service.create_lead(
        session,
        first_name=first_name,
        last_name=last_name,
        email=email,
        resume_bytes=contents,
        resume_filename=resume.filename or "resume",
        resume_content_type=resume.content_type or "application/octet-stream",
        storage=storage,
    )

    # Fire the two emails after the response is returned.
    background_tasks.add_task(send_lead_emails, lead)
    return lead


@router.get("", response_model=LeadList)
def list_leads(
    state: LeadState | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> LeadList:
    """Authenticated: list leads for the internal dashboard."""
    items, total = lead_service.list_leads(
        session, state=state, limit=limit, offset=offset
    )
    return LeadList(items=items, total=total, limit=limit, offset=offset)


@router.get("/{lead_id}", response_model=LeadRead)
def get_lead(
    lead_id: uuid.UUID,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> LeadRead:
    lead = lead_service.get_lead(session, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


@router.patch("/{lead_id}", response_model=LeadRead)
def update_lead(
    lead_id: uuid.UUID,
    payload: LeadUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> LeadRead:
    """Authenticated: transition a lead's state (PENDING -> REACHED_OUT)."""
    lead = lead_service.get_lead(session, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    try:
        lead = lead_service.transition_state(session, lead, payload.state)
    except lead_service.InvalidStateTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return lead


@router.get("/{lead_id}/resume")
def download_resume(
    lead_id: uuid.UUID,
    session: Session = Depends(get_session),
    storage: FileStorage = Depends(get_storage),
    _: User = Depends(get_current_user),
) -> Response:
    """Authenticated: download the prospect's resume."""
    lead = lead_service.get_lead(session, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    try:
        data = storage.read(lead.resume_path)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume file missing")
    return Response(
        content=data,
        media_type=lead.resume_content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{lead.resume_filename}"'
        },
    )
