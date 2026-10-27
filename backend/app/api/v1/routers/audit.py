"""Audit logs router."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.models import AuditLog, User

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=dict)
def list_audit_logs(
    actor_email: str | None = Query(None),
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    complaint_id: UUID | None = Query(None),
    institution_id: UUID | None = Query(None),
    outcome: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_roles("SYSTEM_ADMIN", "SUPERVISOR")),
    db: Session = Depends(get_db),
):
    """List system audit logs (Admin and Supervisor only)."""
    query = db.query(AuditLog)

    if actor_email:
        query = query.filter(AuditLog.actor_email.ilike(f"%{actor_email}%"))
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if complaint_id:
        query = query.filter(AuditLog.complaint_id == complaint_id)
    if institution_id:
        query = query.filter(AuditLog.institution_id == institution_id)
    if outcome:
        query = query.filter(AuditLog.outcome == outcome)
    if date_from:
        query = query.filter(AuditLog.timestamp >= date_from)
    if date_to:
        query = query.filter(AuditLog.timestamp <= date_to)

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(page_size).all()

    return {
        "items": [
            {
                "id": str(log.id),
                "timestamp": log.timestamp,
                "actor_user_id": str(log.actor_user_id) if log.actor_user_id else None,
                "actor_email": log.actor_email,
                "actor_role": log.actor_role,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "complaint_id": str(log.complaint_id) if log.complaint_id else None,
                "institution_id": str(log.institution_id) if log.institution_id else None,
                "before_state": log.before_state,
                "after_state": log.after_state,
                "ip": log.ip,
                "request_id": log.request_id,
                "outcome": log.outcome,
            }
            for log in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
