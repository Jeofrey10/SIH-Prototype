"""Overdue complaint scanning job."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Complaint, User
from app.services.analytics import OPEN_STATUSES
from app.services.audit import write_audit
from app.services.notifications import create_notification

logger = logging.getLogger(__name__)


def run_overdue_scan(
    db: Session,
    actor: User | None = None,
    ip: str | None = None,
    request_id: str | None = None,
) -> dict[str, int]:
    """
    Scans for open complaints with target_date < today.
    Creates OVERDUE and ESCALATION_RECOMMENDED notifications with dedupe keys.
    Writes OVERDUE_SCAN_RUN audit row.
    """
    today = datetime.now(timezone.utc).date()
    overdue_complaints = (
        db.query(Complaint)
        .filter(
            Complaint.status.in_(OPEN_STATUSES),
            Complaint.target_date < today,
        )
        .all()
    )

    supervisors = (
        db.query(User.id)
        .filter(User.role == "SUPERVISOR", User.is_active.is_(True))
        .all()
    )
    supervisor_ids = [s.id for s in supervisors]

    notifications_created = 0

    for c in overdue_complaints:
        days_ov = (today - c.target_date).days if c.target_date else 0
        target_str = str(c.target_date)

        # Mark escalation_recommended = True if overdue by >= 7 days
        if days_ov >= 7 and not c.escalation_recommended:
            c.escalation_recommended = True

        # Recipients: owner (or primary bureau officials if no owner) AND all supervisors
        recipients: set[UUID] = set(supervisor_ids)
        if c.owner_user_id:
            recipients.add(c.owner_user_id)
        elif c.primary_bureau_id:
            officials = (
                db.query(User.id)
                .filter(User.bureau_id == c.primary_bureau_id, User.is_active.is_(True))
                .all()
            )
            for u in officials:
                recipients.add(u.id)

        # OVERDUE notifications
        for uid in recipients:
            dedupe_key = f"OVERDUE:{c.id}:{target_str}:{uid}"
            res = create_notification(
                db,
                user_id=uid,
                type="OVERDUE",
                title=f"Complaint Overdue: {c.reference_number}",
                message=f"Target resolution date {target_str} was missed ({days_ov} days overdue).",
                complaint_id=c.id,
                institution_id=c.institution_id,
                dedupe_key=dedupe_key,
            )
            if res:
                notifications_created += 1

        # ESCALATION_RECOMMENDED notifications (for supervisors)
        if c.escalation_recommended:
            for s_id in supervisor_ids:
                dedupe_key = f"ESCRECO:{c.id}:{target_str}:{s_id}"
                res = create_notification(
                    db,
                    user_id=s_id,
                    type="ESCALATION_RECOMMENDED",
                    title=f"Escalation Recommended: {c.reference_number}",
                    message=f"Complaint is {days_ov} days overdue and qualifies for escalation review.",
                    complaint_id=c.id,
                    institution_id=c.institution_id,
                    dedupe_key=dedupe_key,
                )
                if res:
                    notifications_created += 1

    db.flush()

    # Record audit log
    write_audit(
        db,
        actor_user_id=actor.id if actor else None,
        actor_email=actor.email if actor else "system",
        actor_role=actor.role if actor else "SYSTEM",
        action="OVERDUE_SCAN_RUN",
        entity_type="SYSTEM",
        entity_id="OVERDUE_SCAN",
        after_state={
            "overdue_count": len(overdue_complaints),
            "notifications_dispatched": notifications_created,
        },
        ip=ip,
        request_id=request_id,
    )

    logger.info(
        "Overdue scan complete: %d overdue complaints, %d notifications created",
        len(overdue_complaints),
        notifications_created,
    )

    return {
        "overdue_cases_found": len(overdue_complaints),
        "notifications_created": notifications_created,
    }
