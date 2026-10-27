"""Notification service."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models import Notification, User
from app.core import permissions


def create_notification(
    db: Session,
    *,
    user_id: UUID,
    type: str,
    title: str,
    message: str | None = None,
    complaint_id: UUID | None = None,
    institution_id: UUID | None = None,
    dedupe_key: str | None = None,
    exclude_actor_id: UUID | None = None,
) -> Notification | None:
    """Create a notification. Skip if user_id == exclude_actor_id."""
    if exclude_actor_id and str(user_id) == str(exclude_actor_id):
        return None

    if dedupe_key:
        # Use INSERT ... ON CONFLICT DO NOTHING for idempotency
        stmt = pg_insert(Notification).values(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            complaint_id=complaint_id,
            institution_id=institution_id,
            is_read=False,
            created_at=datetime.now(timezone.utc),
            dedupe_key=dedupe_key,
        ).on_conflict_do_nothing(index_elements=["dedupe_key"])
        db.execute(stmt)
        return None

    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        complaint_id=complaint_id,
        institution_id=institution_id,
        is_read=False,
    )
    db.add(notif)
    return notif


def notify_users(
    db: Session,
    *,
    user_ids: list[UUID],
    type: str,
    title: str,
    message: str | None = None,
    complaint_id: UUID | None = None,
    institution_id: UUID | None = None,
    exclude_actor_id: UUID | None = None,
    dedupe_key_prefix: str | None = None,
) -> int:
    """Create notifications for multiple users. Returns count created."""
    count = 0
    for uid in user_ids:
        dk = f"{dedupe_key_prefix}:{uid}" if dedupe_key_prefix else None
        n = create_notification(
            db,
            user_id=uid,
            type=type,
            title=title,
            message=message,
            complaint_id=complaint_id,
            institution_id=institution_id,
            exclude_actor_id=exclude_actor_id,
            dedupe_key=dk,
        )
        if n:
            count += 1
    return count


def get_bureau_official_ids(db: Session, bureau_id: UUID) -> list[UUID]:
    """Get IDs of all active officials in a bureau."""
    users = db.query(User.id).filter(
        User.bureau_id == bureau_id,
        User.is_active == True,
    ).all()
    return [u.id for u in users]


def get_supervisor_ids(db: Session) -> list[UUID]:
    """Get IDs of all active supervisors."""
    users = db.query(User.id).filter(
        User.role == permissions.SUPERVISOR,
        User.is_active == True,
    ).all()
    return [u.id for u in users]


def get_notifications(db: Session, user_id: UUID, filters: dict) -> tuple[list[Notification], int]:
    """Get notifications for a user."""
    query = db.query(Notification).filter(Notification.user_id == user_id)

    if "unread" in filters and filters["unread"] is not None:
        if filters["unread"]:
            query = query.filter(Notification.is_read == False)
    if "type" in filters and filters["type"]:
        query = query.filter(Notification.type == filters["type"])

    total = query.count()
    page = filters.get("page", 1)
    page_size = min(filters.get("page_size", 20), 100)
    query = query.order_by(Notification.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size)

    return query.all(), total


def get_unread_count(db: Session, user_id: UUID) -> int:
    """Get count of unread notifications."""
    return db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False,
    ).count()


def mark_read(db: Session, notification_id: UUID, user_id: UUID) -> Notification:
    """Mark a notification as read."""
    from app.core.errors import not_found
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    ).first()
    if not notif:
        raise not_found("Notification")

    notif.is_read = True
    notif.read_at = datetime.now(timezone.utc)
    db.flush()
    return notif


def mark_all_read(db: Session, user_id: UUID) -> int:
    """Mark all notifications as read for a user."""
    now = datetime.now(timezone.utc)
    count = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False,
    ).update({"is_read": True, "read_at": now})
    db.flush()
    return count
