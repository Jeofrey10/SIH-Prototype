"""Notifications router."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.services import notifications as notif_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=dict)
def list_notifications(
    unread: bool | None = Query(None),
    type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List notifications for current user."""
    filters = {
        "unread_only": unread,
        "type": type,
        "page": page,
        "page_size": page_size,
    }
    items, total = notif_service.get_notifications(db, current_user.id, filters)
    return {
        "items": [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "complaint_id": n.complaint_id,
                "institution_id": n.institution_id,
                "is_read": n.is_read,
                "read_at": n.read_at,
                "created_at": n.created_at,
            }
            for n in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/unread-count")
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get count of unread notifications for current user."""
    count = notif_service.get_unread_count(db, current_user.id)
    return {"unread_count": count}


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark notification as read (user can only modify their own)."""
    notif = notif_service.mark_read(db, notification_id, current_user.id)
    db.commit()
    return {"message": "Notification marked as read"}


@router.post("/read-all")
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all notifications for current user as read."""
    count = notif_service.mark_all_read(db, current_user.id)
    db.commit()
    return {"updated_count": count}
