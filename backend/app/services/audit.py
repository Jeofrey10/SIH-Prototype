"""Audit logging service."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import AuditLog

logger = logging.getLogger(__name__)


def write_audit(
    db: Session,
    *,
    actor_user_id: UUID | str | None = None,
    actor_email: str | None = None,
    actor_role: str | None = None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    institution_id: UUID | str | None = None,
    complaint_id: UUID | str | None = None,
    outcome: str = "SUCCESS",
    before_data: dict | None = None,
    after_data: dict | None = None,
    before_state: dict | None = None,
    after_state: dict | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
    ip: str | None = None,
    request_id: str | None = None,
) -> AuditLog:
    """Write an audit log entry."""
    before = before_data if before_data is not None else before_state
    after = after_data if after_data is not None else after_state
    client_ip = ip_address if ip_address is not None else ip

    # Sanitize: never store password hashes or tokens
    for data in (before, after, details):
        if data:
            for key in list(data.keys()):
                if any(s in key.lower() for s in ("password", "hash", "token", "secret")):
                    data[key] = "***REDACTED***"

    log = AuditLog(
        occurred_at=datetime.now(timezone.utc),
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        institution_id=institution_id,
        complaint_id=complaint_id,
        outcome=outcome,
        before_data=before,
        after_data=after,
        details=details,
        ip_address=client_ip,
        request_id=request_id,
    )
    db.add(log)
    return log


def write_denied_audit(
    db: Session,
    *,
    actor_user_id: UUID | str | None = None,
    actor_email: str | None = None,
    actor_role: str | None = None,
    action: str = "ACCESS_DENIED",
    entity_type: str = "SYSTEM",
    entity_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
    ip: str | None = None,
    request_id: str | None = None,
    complaint_id: UUID | str | None = None,
    institution_id: UUID | str | None = None,
) -> None:
    """Write a DENIED audit row in a SEPARATE session so it persists on rollback."""
    from app.db.session import get_audit_session
    audit_session = get_audit_session()
    try:
        write_audit(
            audit_session,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            outcome="DENIED",
            details=details,
            ip_address=ip_address or ip,
            request_id=request_id,
            complaint_id=complaint_id,
            institution_id=institution_id,
        )
        audit_session.commit()
    except Exception:
        audit_session.rollback()
        logger.exception("Failed to write denied audit log")
    finally:
        audit_session.close()
