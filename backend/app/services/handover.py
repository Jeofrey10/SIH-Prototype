"""Handover contract service for inter-bureau case transfer with explicit acceptance."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core import errors, permissions
from app.models import Bureau, CaseAssignment, Complaint, Handover, User
from app.services.audit import write_audit
from app.services.notifications import notify_users


def initiate_handover(
    db: Session,
    complaint_id: UUID,
    data: dict[str, Any],
    actor: User,
    ip: str | None = None,
    request_id: str | None = None,
) -> Handover:
    """Initiate a handover contract for inter-bureau case transfer."""
    if actor.role != "SUPERVISOR":
        raise errors.forbidden("Only supervisors can transfer primary bureau and initiate handovers")

    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise errors.not_found("Complaint", str(complaint_id))

    if complaint.status in ("CLOSED", "RESOLVED"):
        raise errors.bad_request(f"Cannot transfer a complaint that is {complaint.status}")

    # Check if already in transit
    pending_existing = (
        db.query(Handover)
        .filter(Handover.complaint_id == complaint_id, Handover.status == "PENDING")
        .first()
    )
    if pending_existing:
        raise errors.conflict("HANDOVER_PENDING", "Case is already in transit with a pending handover")

    to_bureau_id = data.get("to_bureau_id") or data.get("bureau_id")
    if not to_bureau_id:
        raise errors.validation_error({"to_bureau_id": "Target bureau is required"})
    if isinstance(to_bureau_id, str):
        to_bureau_id = UUID(to_bureau_id)

    to_bureau = db.query(Bureau).filter(Bureau.id == to_bureau_id).first()
    if not to_bureau:
        raise errors.not_found("Bureau", str(to_bureau_id))

    if complaint.primary_bureau_id == to_bureau_id:
        raise errors.bad_request("Target bureau is already the primary bureau")

    # Completeness checks
    context_summary = (data.get("context_summary") or data.get("reason") or "").strip()
    if len(context_summary) < 20:
        raise errors.validation_error({
            "context_summary": "Context summary is mandatory and must be at least 20 characters explaining the case to the receiving bureau"
        })

    key_findings = (data.get("key_findings") or "").strip() or None
    target_owner_id = data.get("target_owner_id") or data.get("owner_user_id")
    if target_owner_id and isinstance(target_owner_id, str):
        target_owner_id = UUID(target_owner_id)

    now = datetime.now(timezone.utc)
    handover = Handover(
        complaint_id=complaint.id,
        from_bureau_id=complaint.primary_bureau_id,
        to_bureau_id=to_bureau_id,
        target_owner_id=target_owner_id,
        initiated_by=actor.id,
        initiated_at=now,
        status="PENDING",
        context_summary=context_summary,
        key_findings=key_findings,
    )
    db.add(handover)

    complaint.handover_status = "IN_TRANSIT"
    complaint.updated_at = now
    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="HANDOVER_INITIATED",
        entity_type="HANDOVER",
        entity_id=str(handover.id),
        complaint_id=complaint.id,
        institution_id=complaint.institution_id,
        after_state={
            "from_bureau_id": str(complaint.primary_bureau_id),
            "to_bureau_id": str(to_bureau_id),
            "to_bureau_code": to_bureau.code,
            "context_summary": context_summary,
        },
        ip=ip,
        request_id=request_id,
    )

    # Notify receiving bureau officials
    officials = (
        db.query(User.id)
        .filter(User.bureau_id == to_bureau_id, User.is_active.is_(True))
        .all()
    )
    recipients = [u[0] for u in officials]
    if target_owner_id and target_owner_id not in recipients:
        recipients.append(target_owner_id)

    if recipients:
        notify_users(
            db,
            user_ids=recipients,
            type="HANDOVER_IN_TRANSIT",
            title=f"Handover Pending: {complaint.reference_number}",
            message=f"Case transferred to your bureau pending acceptance. Context: {context_summary[:100]}...",
            complaint_id=complaint.id,
            institution_id=complaint.institution_id,
            exclude_actor_id=actor.id,
        )

    return handover


def accept_handover(
    db: Session,
    complaint_id: UUID,
    actor: User,
    ip: str | None = None,
    request_id: str | None = None,
) -> Handover:
    """Receiving bureau accepts the handover; ownership transfers formally."""
    handover = (
        db.query(Handover)
        .filter(Handover.complaint_id == complaint_id, Handover.status == "PENDING")
        .first()
    )
    if not handover:
        raise errors.not_found("Pending Handover", str(complaint_id))

    # RB/PGRC official of the receiving bureau or supervisor can accept
    if actor.role != "SUPERVISOR" and actor.bureau_id != handover.to_bureau_id:
        raise errors.forbidden("Only officials of the receiving bureau or supervisors can accept this handover")

    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise errors.not_found("Complaint", str(complaint_id))

    now = datetime.now(timezone.utc)
    old_bureau_id = complaint.primary_bureau_id

    # 1. End old primary assignment
    old_primary = (
        db.query(CaseAssignment)
        .filter(
            CaseAssignment.complaint_id == complaint.id,
            CaseAssignment.role_in_case == "PRIMARY",
            CaseAssignment.is_active.is_(True),
        )
        .first()
    )
    if old_primary:
        old_primary.is_active = False
        old_primary.ended_at = now
        old_primary.ended_by = actor.id

    # 2. Deactivate any existing participating assignment for new primary bureau
    part_row = (
        db.query(CaseAssignment)
        .filter(
            CaseAssignment.complaint_id == complaint.id,
            CaseAssignment.bureau_id == handover.to_bureau_id,
            CaseAssignment.role_in_case == "PARTICIPATING",
            CaseAssignment.is_active.is_(True),
        )
        .first()
    )
    if part_row:
        part_row.is_active = False
        part_row.ended_at = now
        part_row.ended_by = actor.id

    # 3. Create new primary assignment
    new_owner_id = handover.target_owner_id or (actor.id if actor.bureau_id == handover.to_bureau_id else None)
    new_primary = CaseAssignment(
        complaint_id=complaint.id,
        bureau_id=handover.to_bureau_id,
        role_in_case="PRIMARY",
        assigned_user_id=new_owner_id,
        assigned_by=actor.id,
        assigned_at=now,
        reason=f"Handover accepted: {handover.context_summary}",
        is_active=True,
    )
    db.add(new_primary)

    # 4. Retain previous bureau as participating
    if old_bureau_id:
        old_part = CaseAssignment(
            complaint_id=complaint.id,
            bureau_id=old_bureau_id,
            role_in_case="PARTICIPATING",
            assigned_by=actor.id,
            assigned_at=now,
            reason="Retained as participant following accepted handover",
            is_active=True,
        )
        db.add(old_part)

    # Update complaint
    complaint.primary_bureau_id = handover.to_bureau_id
    complaint.owner_user_id = new_owner_id
    complaint.handover_status = None
    complaint.updated_at = now

    # Update handover record
    handover.status = "ACCEPTED"
    handover.responded_by = actor.id
    handover.responded_at = now
    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="HANDOVER_ACCEPTED",
        entity_type="HANDOVER",
        entity_id=str(handover.id),
        complaint_id=complaint.id,
        institution_id=complaint.institution_id,
        after_state={
            "to_bureau_id": str(handover.to_bureau_id),
            "accepted_by": str(actor.id),
        },
        ip=ip,
        request_id=request_id,
    )

    # Notify initiator and former bureau officials
    recipients = [handover.initiated_by]
    notify_users(
        db,
        user_ids=recipients,
        type="HANDOVER_ACCEPTED",
        title=f"Handover Accepted: {complaint.reference_number}",
        message=f"Receiving bureau has accepted the handover of case {complaint.reference_number}.",
        complaint_id=complaint.id,
        institution_id=complaint.institution_id,
        exclude_actor_id=actor.id,
    )

    return handover


def return_handover(
    db: Session,
    complaint_id: UUID,
    return_reason: str,
    actor: User,
    ip: str | None = None,
    request_id: str | None = None,
) -> Handover:
    """Receiving bureau returns the handover with an explicit reason."""
    handover = (
        db.query(Handover)
        .filter(Handover.complaint_id == complaint_id, Handover.status == "PENDING")
        .first()
    )
    if not handover:
        raise errors.not_found("Pending Handover", str(complaint_id))

    if actor.role != "SUPERVISOR" and actor.bureau_id != handover.to_bureau_id:
        raise errors.forbidden("Only officials of the receiving bureau or supervisors can return this handover")

    reason = return_reason.strip() if return_reason else ""
    if len(reason) < 10:
        raise errors.validation_error({
            "return_reason": "Return reason is required and must be at least 10 characters explaining why the case is being returned"
        })

    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise errors.not_found("Complaint", str(complaint_id))

    now = datetime.now(timezone.utc)
    handover.status = "RETURNED"
    handover.return_reason = reason
    handover.responded_by = actor.id
    handover.responded_at = now

    complaint.handover_status = None
    complaint.updated_at = now
    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="HANDOVER_RETURNED",
        entity_type="HANDOVER",
        entity_id=str(handover.id),
        complaint_id=complaint.id,
        institution_id=complaint.institution_id,
        after_state={"return_reason": reason, "returned_by": str(actor.id)},
        ip=ip,
        request_id=request_id,
    )

    # Notify initiator (supervisor)
    notify_users(
        db,
        user_ids=[handover.initiated_by],
        type="HANDOVER_RETURNED",
        title=f"Handover Returned: {complaint.reference_number}",
        message=f"Receiving bureau returned the case. Reason: {reason}",
        complaint_id=complaint.id,
        institution_id=complaint.institution_id,
        exclude_actor_id=actor.id,
    )

    return handover


def get_handovers_for_complaint(
    db: Session,
    complaint_id: UUID,
) -> list[dict[str, Any]]:
    """Retrieve full handover history for a complaint."""
    records = (
        db.query(Handover)
        .filter(Handover.complaint_id == complaint_id)
        .order_by(Handover.initiated_at.desc())
        .all()
    )
    results = []
    for h in records:
        results.append({
            "id": h.id,
            "complaint_id": h.complaint_id,
            "status": h.status,
            "context_summary": h.context_summary,
            "key_findings": h.key_findings,
            "from_bureau": {
                "id": h.from_bureau.id,
                "code": h.from_bureau.code,
                "name": h.from_bureau.name,
            } if h.from_bureau else None,
            "to_bureau": {
                "id": h.to_bureau.id,
                "code": h.to_bureau.code,
                "name": h.to_bureau.name,
            } if h.to_bureau else None,
            "initiated_by": {
                "id": h.initiator.id,
                "full_name": h.initiator.full_name,
            } if h.initiator else None,
            "initiated_at": h.initiated_at,
            "responded_by": {
                "id": h.responder.id,
                "full_name": h.responder.full_name,
            } if h.responder else None,
            "responded_at": h.responded_at,
            "return_reason": h.return_reason,
            "target_owner": {
                "id": h.target_owner.id,
                "full_name": h.target_owner.full_name,
            } if h.target_owner else None,
        })
    return results
