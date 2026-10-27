"""Issue Threads router for managing complaint clusters and consolidated briefs."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas import IssueThreadResponse, ThreadBriefUpdateRequest
from app.services import threads as thread_service

router = APIRouter(prefix="/threads", tags=["threads"])


@router.get("", response_model=list[dict])
def list_threads(
    status: str | None = Query("ACTIVE"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all consolidated issue threads."""
    return thread_service.list_threads(db, status=status)


@router.get("/{thread_id}", response_model=dict)
def get_thread_detail(
    thread_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full visual graph and brief details for an issue thread."""
    return thread_service.get_thread_detail(db, thread_id)


@router.patch("/{thread_id}")
def update_thread_brief(
    thread_id: UUID,
    req: ThreadBriefUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update editable consolidated brief for an issue thread."""
    thread = thread_service.update_thread_brief(
        db,
        thread_id=thread_id,
        brief=req.brief,
        title=req.title,
    )
    db.commit()
    return thread_service.get_thread_detail(db, thread_id)
