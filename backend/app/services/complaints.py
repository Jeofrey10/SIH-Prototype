"""Complaint management service."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session

from app.core import errors, permissions
from app.models import (
    Bureau, CaseAssignment, Complaint, ComplaintNote,
    ComplaintRelation, Institution, StatusHistory, User
)
from app.services.audit import write_audit
from app.services.notifications import notify_users
from app.services.relations.normalizer import get_keywords
from app.services.relations.service import detect_and_persist_relations


PRIORITY_DAYS = {
    "CRITICAL": 7,
    "HIGH": 15,
    "MEDIUM": 30,
    "LOW": 45,
}

VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "REGISTERED": {"UNDER_REVIEW"},
    "UNDER_REVIEW": {"ACTION_INITIATED", "PENDING_INFORMATION", "RESOLVED"},
    "ACTION_INITIATED": {"UNDER_REVIEW", "PENDING_INFORMATION", "RESOLVED"},
    "PENDING_INFORMATION": {"UNDER_REVIEW", "ACTION_INITIATED"},
    "RESOLVED": {"CLOSED", "REOPENED"},
    "CLOSED": {"REOPENED"},
    "REOPENED": {"UNDER_REVIEW", "ACTION_INITIATED", "PENDING_INFORMATION", "RESOLVED"},
}


def _generate_reference_number(db: Session, received_date: date) -> str:
    """Generate reference number: CMP-YYYYMMDD-NNNN."""
    date_str = received_date.strftime("%Y%m%d")
    prefix = f"CMP-{date_str}-"

    count = (
        db.query(func.count(Complaint.id))
        .filter(Complaint.reference_number.like(f"{prefix}%"))
        .scalar()
        or 0
    )
    return f"{prefix}{count + 1:04d}"


def create_complaint(
    db: Session,
    data: dict[str, Any],
    actor: User,
    ip: str | None = None,
    request_id: str | None = None,
) -> tuple[Complaint, list[dict[str, Any]]]:
    """
    POST /complaints
    Registers complaint in one transaction with assignment, history, duplicate detection, audit.
    """
    if actor.role == "SYSTEM_ADMIN":
        raise errors.forbidden("System administrators cannot register complaints")

    institution_id = data["institution_id"]
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise errors.not_found("Institution", str(institution_id))
    if not inst.is_active:
        raise errors.bad_request("Cannot register complaint against inactive institution")

    received_date = data.get("received_date") or datetime.now(timezone.utc).date()
    if isinstance(received_date, str):
        received_date = date.fromisoformat(received_date)

    incident_date = data.get("incident_date")
    if incident_date:
        if isinstance(incident_date, str):
            incident_date = date.fromisoformat(incident_date)
        if incident_date > datetime.now(timezone.utc).date():
            raise errors.validation_error({"incident_date": "Incident date cannot be in the future"})

    # Target date calculation
    priority = data.get("priority", "MEDIUM")
    target_date = data.get("target_date")
    if target_date:
        if isinstance(target_date, str):
            target_date = date.fromisoformat(target_date)
        if target_date < received_date:
            raise errors.validation_error({"target_date": "Target date must be >= received date"})
    else:
        days_to_add = PRIORITY_DAYS.get(priority, 30)
        target_date = received_date + timedelta(days=days_to_add)

    # Primary bureau determination
    primary_bureau_id = data.get("primary_bureau_id")
    if actor.role == "SUPERVISOR":
        if not primary_bureau_id:
            raise errors.validation_error({"primary_bureau_id": "Supervisor must select a primary bureau"})
    else:
        if not actor.bureau_id:
            raise errors.validation_error({"primary_bureau_id": "Official has no assigned bureau"})
        primary_bureau_id = actor.bureau_id

    bureau = db.query(Bureau).filter(Bureau.id == primary_bureau_id).first()
    if not bureau:
        raise errors.not_found("Bureau", str(primary_bureau_id))

    owner_user_id = data.get("owner_user_id")
    if not owner_user_id and actor.bureau_id == primary_bureau_id:
        owner_user_id = actor.id

    now = datetime.now(timezone.utc)
    ref_num = _generate_reference_number(db, received_date)

    text_for_kw = f"{data['title']} {data['description']}"
    keywords = get_keywords(text_for_kw, max_keywords=15)

    complaint = Complaint(
        reference_number=ref_num,
        institution_id=institution_id,
        category=data["category"],
        priority=priority,
        status="REGISTERED",
        source_channel=data["source_channel"],
        complainant_type=data["complainant_type"],
        complainant_name=data.get("complainant_name"),
        complainant_contact=data.get("complainant_contact"),
        incident_reference=data.get("incident_reference"),
        incident_date=incident_date,
        received_date=received_date,
        target_date=target_date,
        title=data["title"],
        description=data["description"],
        keywords=keywords,
        primary_bureau_id=primary_bureau_id,
        owner_user_id=owner_user_id,
        created_by=actor.id,
        created_at=now,
        updated_at=now,
        version=1,
    )
    db.add(complaint)
    db.flush()

    # PRIMARY assignment
    assignment = CaseAssignment(
        complaint_id=complaint.id,
        bureau_id=primary_bureau_id,
        role_in_case="PRIMARY",
        assigned_user_id=owner_user_id,
        assigned_by=actor.id,
        assigned_at=now,
        reason="Initial assignment upon complaint registration",
        is_active=True,
    )
    db.add(assignment)

    # Status history
    history = StatusHistory(
        complaint_id=complaint.id,
        from_status=None,
        to_status="REGISTERED",
        changed_by=actor.id,
        changed_at=now,
        remark="Initial registration",
    )
    db.add(history)
    db.flush()

    # Duplicate detection & persistence
    suggested_relations = detect_and_persist_relations(
        db, complaint, actor=actor, ip=ip, request_id=request_id
    )

    # Notification for owner
    if owner_user_id and str(owner_user_id) != str(actor.id):
        notify_users(
            db,
            user_ids=[owner_user_id],
            type="COMPLAINT_ASSIGNED",
            title=f"New complaint assigned: {complaint.reference_number}",
            message=f"You have been assigned complaint {complaint.reference_number} at {inst.name}.",
            complaint_id=complaint.id,
            institution_id=complaint.institution_id,
            exclude_actor_id=actor.id,
        )

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="COMPLAINT_CREATED",
        entity_type="COMPLAINT",
        entity_id=str(complaint.id),
        complaint_id=complaint.id,
        institution_id=institution_id,
        after_state={
            "reference_number": complaint.reference_number,
            "category": complaint.category,
            "priority": complaint.priority,
            "status": complaint.status,
            "primary_bureau": bureau.code,
            "owner_user_id": str(owner_user_id) if owner_user_id else None,
        },
        ip=ip,
        request_id=request_id,
    )

    related_candidates = []
    for rel in suggested_relations:
        other_id = rel.complaint_b_id if rel.complaint_a_id == complaint.id else rel.complaint_a_id
        other_c = db.query(Complaint).filter(Complaint.id == other_id).first()
        if other_c:
            related_candidates.append({
                "relation_id": rel.id,
                "candidate_id": other_c.id,
                "candidate_reference": other_c.reference_number,
                "candidate_title": other_c.title,
                "candidate_category": other_c.category,
                "candidate_status": other_c.status,
                "candidate_primary_bureau": other_c.primary_bureau.code if other_c.primary_bureau else None,
                "score": rel.score,
                "confidence": rel.confidence,
                "explanation": rel.explanation,
            })

    return complaint, related_candidates


def update_complaint(
    db: Session,
    complaint_id: UUID,
    data: dict[str, Any],
    actor: User,
    ip: str | None = None,
    request_id: str | None = None,
) -> Complaint:
    """PATCH /complaints/{id}"""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise errors.not_found("Complaint", str(complaint_id))

    if not permissions.can_edit_complaint(complaint, actor):
        raise errors.forbidden("You do not have permission to edit this complaint")

    if complaint.status == "CLOSED":
        raise errors.bad_request("Cannot edit closed complaint; reopen first")

    req_version = data.get("version")
    if req_version is None or req_version != complaint.version:
        raise errors.conflict("VERSION_CONFLICT", "Complaint was modified by another user. Please reload.")

    before_state = {
        "title": complaint.title,
        "description": complaint.description,
        "category": complaint.category,
        "priority": complaint.priority,
        "target_date": str(complaint.target_date) if complaint.target_date else None,
    }

    material_change = False

    if "title" in data and data["title"] is not None:
        complaint.title = data["title"].strip()
        material_change = True
    if "description" in data and data["description"] is not None:
        complaint.description = data["description"].strip()
        material_change = True
    if "category" in data and data["category"] is not None:
        complaint.category = data["category"]
        material_change = True
    if "priority" in data and data["priority"] is not None:
        complaint.priority = data["priority"]
    if "source_channel" in data and data["source_channel"] is not None:
        complaint.source_channel = data["source_channel"]
    if "complainant_type" in data and data["complainant_type"] is not None:
        complaint.complainant_type = data["complainant_type"]
    if "complainant_name" in data:
        complaint.complainant_name = data["complainant_name"]
    if "complainant_contact" in data:
        complaint.complainant_contact = data["complainant_contact"]
    if "incident_reference" in data:
        complaint.incident_reference = data["incident_reference"]
        material_change = True
    if "incident_date" in data:
        complaint.incident_date = data["incident_date"]
        material_change = True

    if "target_date" in data and data["target_date"] is not None:
        new_target = data["target_date"]
        if isinstance(new_target, str):
            new_target = date.fromisoformat(new_target)
        if new_target != complaint.target_date:
            reason = data.get("target_date_change_reason")
            if not reason:
                raise errors.validation_error(
                    {"target_date_change_reason": "Reason required when changing target date"}
                )
            complaint.target_date = new_target
            before_state["target_date_change_reason"] = reason

    now = datetime.now(timezone.utc)
    complaint.updated_at = now
    complaint.version += 1

    if material_change:
        text_for_kw = f"{complaint.title} {complaint.description}"
        complaint.keywords = get_keywords(text_for_kw, max_keywords=15)
        detect_and_persist_relations(db, complaint, actor=actor, ip=ip, request_id=request_id)

    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="COMPLAINT_UPDATED",
        entity_type="COMPLAINT",
        entity_id=str(complaint.id),
        complaint_id=complaint.id,
        institution_id=complaint.institution_id,
        before_state=before_state,
        after_state={
            "title": complaint.title,
            "description": complaint.description,
            "category": complaint.category,
            "priority": complaint.priority,
            "target_date": str(complaint.target_date) if complaint.target_date else None,
            "version": complaint.version,
        },
        ip=ip,
        request_id=request_id,
    )

    return complaint


def change_status(
    db: Session,
    complaint_id: UUID,
    data: dict[str, Any],
    actor: User,
    ip: str | None = None,
    request_id: str | None = None,
) -> Complaint:
    """POST /complaints/{id}/status"""
    if actor.role == "SYSTEM_ADMIN":
        raise errors.forbidden("System administrators cannot change complaint status")

    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == complaint_id)
        .with_for_update()
        .first()
    )
    if not complaint:
        raise errors.not_found("Complaint", str(complaint_id))

    if not permissions.can_change_status(complaint, actor):
        raise errors.forbidden("You do not have permission to change the status of this complaint")

    to_status = data["to_status"]
    from_status = complaint.status

    expected_status = data.get("expected_status")
    if expected_status and expected_status != from_status:
        raise errors.conflict(
            "VERSION_CONFLICT",
            f"Expected status {expected_status} but complaint is in {from_status}",
        )

    req_version = data.get("version")
    if req_version is not None and req_version != complaint.version:
        raise errors.conflict(
            "VERSION_CONFLICT",
            "Complaint has been updated by another user. Please reload.",
        )

    valid_next = VALID_STATUS_TRANSITIONS.get(from_status, set())
    if to_status not in valid_next:
        raise errors.conflict(
            "INVALID_STATUS_TRANSITION",
            f"Invalid transition from {from_status} to {to_status}",
        )

    if to_status == "CLOSED" and actor.role != "SUPERVISOR":
        raise errors.forbidden("Only supervisors can close a resolved complaint")
    if from_status == "CLOSED" and to_status == "REOPENED" and actor.role != "SUPERVISOR":
        raise errors.forbidden("Only supervisors can reopen a closed complaint")

    remark = data.get("remark")
    resolution_summary = data.get("resolution_summary")
    now = datetime.now(timezone.utc)

    if to_status == "RESOLVED":
        if not resolution_summary or len(resolution_summary.strip()) < 20:
            raise errors.validation_error(
                {"resolution_summary": "Resolution summary must be at least 20 characters"}
            )
        if not remark:
            raise errors.validation_error({"remark": "Remark is required when resolving"})
        complaint.resolution_summary = resolution_summary.strip()
        complaint.resolved_at = now

    elif to_status == "CLOSED":
        if not remark:
            raise errors.validation_error({"remark": "Remark is required when closing"})
        complaint.closed_at = now

    elif to_status == "REOPENED":
        if not remark or len(remark.strip()) < 5:
            raise errors.validation_error(
                {"remark": "Remark of at least 5 characters is required when reopening"}
            )
        complaint.reopened_count += 1
        complaint.resolved_at = None
        complaint.closed_at = None
        today = datetime.now(timezone.utc).date()
        if complaint.target_date and complaint.target_date < today:
            new_target = data.get("target_date")
            if not new_target:
                raise errors.validation_error(
                    {"target_date": "Target date is in the past; a new target date is required"}
                )
            if isinstance(new_target, str):
                new_target = date.fromisoformat(new_target)
            if new_target < today:
                raise errors.validation_error({"target_date": "New target date must be >= today"})
            complaint.target_date = new_target

    elif to_status == "PENDING_INFORMATION":
        if not remark:
            raise errors.validation_error({"remark": "Remark is required when requesting information"})

    complaint.status = to_status
    complaint.updated_at = now
    complaint.version += 1

    history = StatusHistory(
        complaint_id=complaint.id,
        from_status=from_status,
        to_status=to_status,
        changed_by=actor.id,
        changed_at=now,
        remark=remark,
    )
    db.add(history)

    # Automatic synchronization for waiting-on ledger commitments
    from app.services.waiting_on import auto_sync_on_status_change
    auto_sync_on_status_change(db, complaint, from_status, to_status, actor)

    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="COMPLAINT_STATUS_CHANGED",
        entity_type="COMPLAINT",
        entity_id=str(complaint.id),
        complaint_id=complaint.id,
        institution_id=complaint.institution_id,
        before_state={"status": from_status},
        after_state={"status": to_status, "remark": remark},
        ip=ip,
        request_id=request_id,
    )

    recipients: set[UUID] = set()
    if complaint.owner_user_id:
        recipients.add(complaint.owner_user_id)
    if complaint.created_by:
        recipients.add(complaint.created_by)

    participating_bureau_ids = (
        db.query(CaseAssignment.bureau_id)
        .filter(
            CaseAssignment.complaint_id == complaint.id,
            CaseAssignment.is_active.is_(True),
        )
        .all()
    )
    for (b_id,) in participating_bureau_ids:
        officials = (
            db.query(User.id)
            .filter(User.bureau_id == b_id, User.is_active.is_(True))
            .all()
        )
        for (u_id,) in officials:
            recipients.add(u_id)

    if to_status in ("RESOLVED", "REOPENED", "CLOSED"):
        supervisors = (
            db.query(User.id)
            .filter(User.role == "SUPERVISOR", User.is_active.is_(True))
            .all()
        )
        for (s_id,) in supervisors:
            recipients.add(s_id)

    if recipients:
        notify_users(
            db,
            user_ids=list(recipients),
            type="STATUS_CHANGED",
            title=f"Complaint status updated: {complaint.reference_number}",
            message=f"Status changed from {from_status} to {to_status}.",
            complaint_id=complaint.id,
            institution_id=complaint.institution_id,
            exclude_actor_id=actor.id,
        )

    return complaint


def escalate_complaint(
    db: Session,
    complaint_id: UUID,
    data: dict[str, Any],
    actor: User,
    ip: str | None = None,
    request_id: str | None = None,
) -> Complaint:
    """POST /complaints/{id}/escalate"""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise errors.not_found("Complaint", str(complaint_id))

    if complaint.status in ("RESOLVED", "CLOSED"):
        raise errors.bad_request("Cannot escalate a resolved or closed complaint")

    if complaint.escalation_level > 0:
        raise errors.bad_request("Complaint is already escalated")

    reason = data.get("reason", "").strip()
    if len(reason) < 5:
        raise errors.validation_error({"reason": "Escalation reason must be at least 5 characters"})

    now = datetime.now(timezone.utc)
    complaint.escalation_level = 1
    complaint.escalated_at = now
    complaint.escalated_by = actor.id
    complaint.escalation_reason = reason
    complaint.updated_at = now

    note = ComplaintNote(
        complaint_id=complaint.id,
        author_id=actor.id,
        note_type="ESCALATION_NOTE",
        body=f"Complaint escalated: {reason}",
        created_at=now,
    )
    db.add(note)
    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="COMPLAINT_ESCALATED",
        entity_type="COMPLAINT",
        entity_id=str(complaint.id),
        complaint_id=complaint.id,
        institution_id=complaint.institution_id,
        after_state={"escalation_level": 1, "reason": reason},
        ip=ip,
        request_id=request_id,
    )

    recipients: set[UUID] = set()
    if complaint.owner_user_id:
        recipients.add(complaint.owner_user_id)
    supervisors = (
        db.query(User.id)
        .filter(User.role == "SUPERVISOR", User.is_active.is_(True))
        .all()
    )
    for (s_id,) in supervisors:
        recipients.add(s_id)

    if recipients:
        notify_users(
            db,
            user_ids=list(recipients),
            type="ESCALATED",
            title=f"Complaint Escalated: {complaint.reference_number}",
            message=f"Escalated with reason: {reason}",
            complaint_id=complaint.id,
            institution_id=complaint.institution_id,
            exclude_actor_id=actor.id,
        )

    return complaint


def clear_escalation(
    db: Session,
    complaint_id: UUID,
    data: dict[str, Any],
    actor: User,
    ip: str | None = None,
    request_id: str | None = None,
) -> Complaint:
    """POST /complaints/{id}/clear-escalation"""
    if actor.role != "SUPERVISOR":
        raise errors.forbidden("Only supervisors can clear escalation")

    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise errors.not_found("Complaint", str(complaint_id))

    note_body = data.get("note", "").strip()
    if len(note_body) < 5:
        raise errors.validation_error({"note": "Clearing note must be at least 5 characters"})

    now = datetime.now(timezone.utc)
    complaint.escalation_level = 0
    complaint.updated_at = now

    note = ComplaintNote(
        complaint_id=complaint.id,
        author_id=actor.id,
        note_type="COORDINATION_NOTE",
        body=f"Escalation cleared: {note_body}",
        created_at=now,
    )
    db.add(note)
    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="COMPLAINT_ESCALATION_CLEARED",
        entity_type="COMPLAINT",
        entity_id=str(complaint.id),
        complaint_id=complaint.id,
        institution_id=complaint.institution_id,
        after_state={"escalation_level": 0, "note": note_body},
        ip=ip,
        request_id=request_id,
    )

    return complaint


def add_note(
    db: Session,
    complaint_id: UUID,
    data: dict[str, Any],
    actor: User,
    ip: str | None = None,
    request_id: str | None = None,
) -> ComplaintNote:
    """POST /complaints/{id}/notes"""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise errors.not_found("Complaint", str(complaint_id))

    if not permissions.can_add_note(complaint, actor):
        raise errors.forbidden("You do not have permission to add notes to this complaint")

    body = data.get("body", "").strip()
    if len(body) < 3:
        raise errors.validation_error({"body": "Note body must be at least 3 characters"})

    note_type = data.get("note_type", "ACTION_NOTE")
    if note_type not in ("ACTION_NOTE", "COORDINATION_NOTE"):
        raise errors.validation_error({"note_type": "Invalid note type"})

    now = datetime.now(timezone.utc)
    note = ComplaintNote(
        complaint_id=complaint.id,
        author_id=actor.id,
        bureau_id=actor.bureau_id,
        note_type=note_type,
        body=body,
        created_at=now,
    )
    db.add(note)
    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="COMPLAINT_NOTE_ADDED",
        entity_type="NOTE",
        entity_id=str(note.id),
        complaint_id=complaint.id,
        institution_id=complaint.institution_id,
        after_state={"note_type": note_type},
        ip=ip,
        request_id=request_id,
    )

    return note


def get_notes(
    db: Session,
    complaint_id: UUID,
    actor: User,
) -> list[ComplaintNote]:
    """GET /complaints/{id}/notes"""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise errors.not_found("Complaint", str(complaint_id))

    access_level = permissions.get_complaint_access_level(complaint, actor)
    if access_level != "FULL":
        raise errors.forbidden("You do not have access to view notes for this complaint")

    return (
        db.query(ComplaintNote)
        .filter(ComplaintNote.complaint_id == complaint_id)
        .order_by(ComplaintNote.created_at.asc())
        .all()
    )


def add_participant(
    db: Session,
    complaint_id: UUID,
    data: dict[str, Any],
    actor: User,
    ip: str | None = None,
    request_id: str | None = None,
) -> CaseAssignment:
    """POST /complaints/{id}/participants"""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise errors.not_found("Complaint", str(complaint_id))

    if not permissions.can_manage_participants(complaint, actor):
        raise errors.forbidden("You do not have permission to manage participants")

    bureau_id = data["bureau_id"]
    bureau = db.query(Bureau).filter(Bureau.id == bureau_id).first()
    if not bureau:
        raise errors.not_found("Bureau", str(bureau_id))

    if complaint.primary_bureau_id == bureau_id:
        raise errors.conflict(f"Bureau {bureau.code} is already the primary bureau")

    existing = (
        db.query(CaseAssignment)
        .filter(
            CaseAssignment.complaint_id == complaint_id,
            CaseAssignment.bureau_id == bureau_id,
            CaseAssignment.is_active.is_(True),
        )
        .first()
    )
    if existing:
        raise errors.conflict(f"Bureau {bureau.code} is already participating on this case")

    now = datetime.now(timezone.utc)
    assignment = CaseAssignment(
        complaint_id=complaint.id,
        bureau_id=bureau_id,
        role_in_case="PARTICIPATING",
        assigned_by=actor.id,
        assigned_at=now,
        reason=data.get("reason"),
        is_active=True,
    )
    db.add(assignment)
    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="ASSIGNMENT_PARTICIPANT_ADDED",
        entity_type="ASSIGNMENT",
        entity_id=str(bureau_id),
        complaint_id=complaint.id,
        institution_id=complaint.institution_id,
        after_state={"bureau_code": bureau.code, "reason": data.get("reason")},
        ip=ip,
        request_id=request_id,
    )

    recipients: set[UUID] = set()
    if complaint.owner_user_id:
        recipients.add(complaint.owner_user_id)
    officials = (
        db.query(User.id)
        .filter(User.bureau_id == bureau_id, User.is_active.is_(True))
        .all()
    )
    for (u_id,) in officials:
        recipients.add(u_id)

    if recipients:
        notify_users(
            db,
            user_ids=list(recipients),
            type="PARTICIPATION_ADDED",
            title=f"Participation added: {complaint.reference_number}",
            message=f"Bureau {bureau.code} added as participant on {complaint.reference_number}.",
            complaint_id=complaint.id,
            institution_id=complaint.institution_id,
            exclude_actor_id=actor.id,
        )

    return assignment


def remove_participant(
    db: Session,
    complaint_id: UUID,
    bureau_id: UUID,
    data: dict[str, Any] | None,
    actor: User,
    ip: str | None = None,
    request_id: str | None = None,
) -> None:
    """DELETE /complaints/{id}/participants/{bureau_id}"""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise errors.not_found("Complaint", str(complaint_id))

    if not permissions.can_manage_participants(complaint, actor):
        raise errors.forbidden("You do not have permission to manage participants")

    if complaint.primary_bureau_id == bureau_id:
        raise errors.bad_request("Cannot remove the primary bureau from participation")

    assignment = (
        db.query(CaseAssignment)
        .filter(
            CaseAssignment.complaint_id == complaint_id,
            CaseAssignment.bureau_id == bureau_id,
            CaseAssignment.is_active.is_(True),
        )
        .first()
    )
    if not assignment:
        raise errors.not_found("CaseAssignment", f"bureau_id={bureau_id}")

    now = datetime.now(timezone.utc)
    assignment.is_active = False
    assignment.ended_at = now
    assignment.ended_by = actor.id
    db.flush()

    bureau = db.query(Bureau).filter(Bureau.id == bureau_id).first()
    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="ASSIGNMENT_PARTICIPANT_REMOVED",
        entity_type="ASSIGNMENT",
        entity_id=str(bureau_id),
        complaint_id=complaint.id,
        institution_id=complaint.institution_id,
        after_state={"bureau_code": bureau.code if bureau else None},
        ip=ip,
        request_id=request_id,
    )


def change_owner(
    db: Session,
    complaint_id: UUID,
    data: dict[str, Any],
    actor: User,
    ip: str | None = None,
    request_id: str | None = None,
) -> Complaint:
    """POST /complaints/{id}/owner"""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise errors.not_found("Complaint", str(complaint_id))

    if not permissions.can_change_owner(complaint, actor):
        raise errors.forbidden("You do not have permission to change the owner")

    new_user_id = data.get("user_id")
    if new_user_id:
        new_user = db.query(User).filter(User.id == new_user_id).first()
        if not new_user:
            raise errors.not_found("User", str(new_user_id))
        if new_user.bureau_id != complaint.primary_bureau_id:
            raise errors.validation_error(
                {"user_id": "Owner must belong to the primary bureau"}
            )

    now = datetime.now(timezone.utc)
    old_owner_id = complaint.owner_user_id

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

    new_primary = CaseAssignment(
        complaint_id=complaint.id,
        bureau_id=complaint.primary_bureau_id,
        role_in_case="PRIMARY",
        assigned_user_id=new_user_id,
        assigned_by=actor.id,
        assigned_at=now,
        reason=data.get("reason"),
        is_active=True,
    )
    db.add(new_primary)

    complaint.owner_user_id = new_user_id
    complaint.updated_at = now
    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="ASSIGNMENT_OWNER_CHANGED",
        entity_type="ASSIGNMENT",
        entity_id=str(new_user_id) if new_user_id else "NONE",
        complaint_id=complaint.id,
        institution_id=complaint.institution_id,
        before_state={"owner_user_id": str(old_owner_id) if old_owner_id else None},
        after_state={"owner_user_id": str(new_user_id) if new_user_id else None},
        ip=ip,
        request_id=request_id,
    )

    recipients = [u for u in (new_user_id, old_owner_id) if u]
    if recipients:
        notify_users(
            db,
            user_ids=recipients,
            type="OWNERSHIP_CHANGED",
            title=f"Complaint Ownership Changed: {complaint.reference_number}",
            message="Ownership assignment has been updated.",
            complaint_id=complaint.id,
            institution_id=complaint.institution_id,
            exclude_actor_id=actor.id,
        )

    return complaint


def transfer_primary_bureau(
    db: Session,
    complaint_id: UUID,
    data: dict[str, Any],
    actor: User,
    ip: str | None = None,
    request_id: str | None = None,
) -> Complaint:
    """POST /complaints/{id}/primary-transfer"""
    if actor.role != "SUPERVISOR":
        raise errors.forbidden("Only supervisors can transfer primary bureau")

    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise errors.not_found("Complaint", str(complaint_id))

    new_bureau_id = data["bureau_id"]
    new_bureau = db.query(Bureau).filter(Bureau.id == new_bureau_id).first()
    if not new_bureau:
        raise errors.not_found("Bureau", str(new_bureau_id))

    if complaint.primary_bureau_id == new_bureau_id:
        raise errors.bad_request("Bureau is already primary")

    reason = data.get("reason", "").strip()
    if len(reason) < 5:
        raise errors.validation_error({"reason": "Transfer reason must be at least 5 characters"})

    now = datetime.now(timezone.utc)
    old_bureau_id = complaint.primary_bureau_id

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

    part_row = (
        db.query(CaseAssignment)
        .filter(
            CaseAssignment.complaint_id == complaint.id,
            CaseAssignment.bureau_id == new_bureau_id,
            CaseAssignment.role_in_case == "PARTICIPATING",
            CaseAssignment.is_active.is_(True),
        )
        .first()
    )
    if part_row:
        part_row.is_active = False
        part_row.ended_at = now
        part_row.ended_by = actor.id

    new_owner_id = data.get("owner_user_id")
    new_primary = CaseAssignment(
        complaint_id=complaint.id,
        bureau_id=new_bureau_id,
        role_in_case="PRIMARY",
        assigned_user_id=new_owner_id,
        assigned_by=actor.id,
        assigned_at=now,
        reason=reason,
        is_active=True,
    )
    db.add(new_primary)

    keep_old = data.get("keep_previous_as_participant", True)
    if keep_old and old_bureau_id:
        old_part = CaseAssignment(
            complaint_id=complaint.id,
            bureau_id=old_bureau_id,
            role_in_case="PARTICIPATING",
            assigned_by=actor.id,
            assigned_at=now,
            reason=f"Retained as participant following primary transfer: {reason}",
            is_active=True,
        )
        db.add(old_part)

    complaint.primary_bureau_id = new_bureau_id
    complaint.owner_user_id = new_owner_id
    complaint.updated_at = now
    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="ASSIGNMENT_PRIMARY_TRANSFERRED",
        entity_type="ASSIGNMENT",
        entity_id=str(new_bureau_id),
        complaint_id=complaint.id,
        institution_id=complaint.institution_id,
        before_state={"primary_bureau_id": str(old_bureau_id)},
        after_state={"primary_bureau_id": str(new_bureau_id), "reason": reason},
        ip=ip,
        request_id=request_id,
    )

    recipients: set[UUID] = set()
    if new_owner_id:
        recipients.add(new_owner_id)
    officials = (
        db.query(User.id)
        .filter(User.bureau_id == new_bureau_id, User.is_active.is_(True))
        .all()
    )
    for (u_id,) in officials:
        recipients.add(u_id)

    if recipients:
        notify_users(
            db,
            user_ids=list(recipients),
            type="COMPLAINT_ASSIGNED",
            title=f"Primary Bureau Transferred: {complaint.reference_number}",
            message=f"Case transferred to {new_bureau.code}. Reason: {reason}",
            complaint_id=complaint.id,
            institution_id=complaint.institution_id,
            exclude_actor_id=actor.id,
        )

    return complaint


def get_complaint_detail(
    db: Session,
    complaint_id: UUID,
    actor: User,
) -> dict[str, Any]:
    """GET /complaints/{id}"""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise errors.not_found("Complaint", str(complaint_id))

    access_level = permissions.get_complaint_access_level(complaint, actor)
    is_full = access_level == "FULL"

    today = datetime.now(timezone.utc).date()
    is_overdue = bool(
        complaint.target_date
        and complaint.target_date < today
        and complaint.status not in ("RESOLVED", "CLOSED")
    )
    days_overdue = (today - complaint.target_date).days if is_overdue else 0

    allowed = permissions.get_allowed_actions(complaint, actor)

    participating = []
    assignments = (
        db.query(CaseAssignment)
        .filter(
            CaseAssignment.complaint_id == complaint.id,
            CaseAssignment.role_in_case == "PARTICIPATING",
            CaseAssignment.is_active.is_(True),
        )
        .all()
    )
    for a in assignments:
        b = a.bureau
        if b:
            participating.append({"id": b.id, "code": b.code, "name": b.name})

    from app.services.delay_explainer import generate_delay_explanation
    from app.services.limbo_detector import detect_limbo_for_complaint_obj
    from app.services.waiting_on import get_waiting_on_summary
    from app.models import Handover

    delay_explanation = generate_delay_explanation(db, complaint)
    limbo_flags = detect_limbo_for_complaint_obj(db, complaint)
    waiting_summary = get_waiting_on_summary(db, complaint.id)

    pending_handover = None
    if complaint.handover_status == "IN_TRANSIT":
        ph = (
            db.query(Handover)
            .filter(Handover.complaint_id == complaint.id, Handover.status == "PENDING")
            .order_by(Handover.initiated_at.desc())
            .first()
        )
        if ph:
            pending_handover = {
                "id": ph.id,
                "from_bureau": {"id": ph.from_bureau.id, "code": ph.from_bureau.code, "name": ph.from_bureau.name} if ph.from_bureau else None,
                "to_bureau": {"id": ph.to_bureau.id, "code": ph.to_bureau.code, "name": ph.to_bureau.name} if ph.to_bureau else None,
                "initiated_by": {"id": ph.initiator.id, "full_name": ph.initiator.full_name} if ph.initiator else None,
                "initiated_at": ph.initiated_at,
                "context_summary": ph.context_summary,
                "key_findings": ph.key_findings,
                "status": ph.status,
            }

    return {
        "id": complaint.id,
        "reference_number": complaint.reference_number,
        "institution": {
            "id": complaint.institution.id,
            "code": complaint.institution.code,
            "name": complaint.institution.name,
        } if complaint.institution else None,
        "title": complaint.title if is_full else None,
        "description": complaint.description if is_full else None,
        "category": complaint.category,
        "priority": complaint.priority,
        "status": complaint.status,
        "source_channel": complaint.source_channel if is_full else None,
        "complainant_type": complaint.complainant_type if is_full else None,
        "complainant_name": complaint.complainant_name if is_full else None,
        "complainant_contact": complaint.complainant_contact if is_full else None,
        "incident_reference": complaint.incident_reference if is_full else None,
        "incident_date": complaint.incident_date if is_full else None,
        "received_date": complaint.received_date,
        "target_date": complaint.target_date,
        "is_overdue": is_overdue,
        "days_overdue": days_overdue,
        "escalation_level": complaint.escalation_level,
        "escalation_reason": complaint.escalation_reason if is_full else None,
        "primary_bureau": {
            "id": complaint.primary_bureau.id,
            "code": complaint.primary_bureau.code,
            "name": complaint.primary_bureau.name,
        } if complaint.primary_bureau else None,
        "owner": {
            "id": complaint.owner.id,
            "full_name": complaint.owner.full_name,
        } if complaint.owner else None,
        "participating_bureaus": participating,
        "resolution_summary": complaint.resolution_summary if is_full else None,
        "resolved_at": complaint.resolved_at,
        "closed_at": complaint.closed_at,
        "reopened_count": complaint.reopened_count,
        "created_by": {
            "id": complaint.creator.id,
            "full_name": complaint.creator.full_name,
        } if complaint.creator else None,
        "created_at": complaint.created_at,
        "updated_at": complaint.updated_at,
        "version": complaint.version,
        "access_level": access_level,
        "allowed_actions": allowed,
        "handover_status": complaint.handover_status,
        "delay_explanation": delay_explanation,
        "limbo_flags": limbo_flags,
        "waiting_on_summary": waiting_summary,
        "pending_handover": pending_handover,
    }


def list_complaints(
    db: Session,
    actor: User,
    *,
    q: str | None = None,
    institution_id: UUID | None = None,
    status: list[str] | None = None,
    category: str | None = None,
    priority: str | None = None,
    primary_bureau_id: UUID | None = None,
    participating_bureau_id: UUID | None = None,
    owner_user_id: UUID | None = None,
    unassigned_owner: bool | None = None,
    overdue: bool | None = None,
    escalated: bool | None = None,
    received_from: date | None = None,
    received_to: date | None = None,
    scope: str | None = None,
    sort_by: str = "received_date",
    order: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    """GET /complaints"""
    query = db.query(Complaint)
    today = datetime.now(timezone.utc).date()

    if scope is None:
        scope = "bureau" if actor.role in ("RB_OFFICIAL", "PGRC_OFFICIAL") else "all"

    if scope == "bureau" and actor.bureau_id:
        # complaints where official's bureau participates as primary or active participating
        participating_complaint_ids = (
            db.query(CaseAssignment.complaint_id)
            .filter(
                CaseAssignment.bureau_id == actor.bureau_id,
                CaseAssignment.is_active.is_(True),
            )
            .subquery()
        )
        query = query.filter(
            or_(
                Complaint.primary_bureau_id == actor.bureau_id,
                Complaint.id.in_(participating_complaint_ids),
            )
        )

    if institution_id:
        query = query.filter(Complaint.institution_id == institution_id)

    if status:
        query = query.filter(Complaint.status.in_(status))

    if category:
        query = query.filter(Complaint.category == category)

    if priority:
        query = query.filter(Complaint.priority == priority)

    if primary_bureau_id:
        query = query.filter(Complaint.primary_bureau_id == primary_bureau_id)

    if participating_bureau_id:
        part_ids = (
            db.query(CaseAssignment.complaint_id)
            .filter(
                CaseAssignment.bureau_id == participating_bureau_id,
                CaseAssignment.role_in_case == "PARTICIPATING",
                CaseAssignment.is_active.is_(True),
            )
            .subquery()
        )
        query = query.filter(Complaint.id.in_(part_ids))

    if owner_user_id:
        query = query.filter(Complaint.owner_user_id == owner_user_id)

    if unassigned_owner is True:
        query = query.filter(Complaint.owner_user_id.is_(None))

    if overdue is True:
        query = query.filter(
            Complaint.target_date < today,
            ~Complaint.status.in_(["RESOLVED", "CLOSED"]),
        )
    elif overdue is False:
        query = query.filter(
            or_(
                Complaint.target_date >= today,
                Complaint.status.in_(["RESOLVED", "CLOSED"]),
            )
        )

    if escalated is True:
        query = query.filter(Complaint.escalation_level > 0)
    elif escalated is False:
        query = query.filter(Complaint.escalation_level == 0)

    if received_from:
        query = query.filter(Complaint.received_date >= received_from)
    if received_to:
        query = query.filter(Complaint.received_date <= received_to)

    if q:
        q_clean = q.strip()
        query = query.filter(
            or_(
                Complaint.reference_number.ilike(f"%{q_clean}%"),
                Complaint.title.ilike(f"%{q_clean}%"),
            )
        )

    total = query.count()

    sort_column = Complaint.received_date
    if sort_by == "target_date":
        sort_column = Complaint.target_date
    elif sort_by == "updated_at":
        sort_column = Complaint.updated_at
    elif sort_by == "priority":
        sort_column = case(
            (Complaint.priority == "CRITICAL", 4),
            (Complaint.priority == "HIGH", 3),
            (Complaint.priority == "MEDIUM", 2),
            (Complaint.priority == "LOW", 1),
            else_=0,
        )

    if order.lower() == "asc":
        query = query.order_by(sort_column.asc(), Complaint.id.asc())
    else:
        query = query.order_by(sort_column.desc(), Complaint.id.desc())

    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    results = []
    for c in items:
        access_level = permissions.get_complaint_access_level(c, actor)
        is_full = access_level == "FULL"

        is_ov = bool(c.target_date and c.target_date < today and c.status not in ("RESOLVED", "CLOSED"))
        days_ov = (today - c.target_date).days if is_ov else 0

        from app.services.delay_explainer import generate_delay_explanation
        from app.services.limbo_detector import detect_limbo_for_complaint_obj
        from app.services.waiting_on import get_waiting_on_summary

        exp = generate_delay_explanation(db, c)
        flags = detect_limbo_for_complaint_obj(db, c)
        ws = get_waiting_on_summary(db, c.id)

        results.append({
            "id": c.id,
            "reference_number": c.reference_number,
            "institution": {
                "id": c.institution.id,
                "code": c.institution.code,
                "name": c.institution.name,
            } if c.institution else None,
            "title": c.title if is_full else None,
            "category": c.category,
            "priority": c.priority,
            "status": c.status,
            "primary_bureau": {
                "id": c.primary_bureau.id,
                "code": c.primary_bureau.code,
                "name": c.primary_bureau.name,
            } if c.primary_bureau else None,
            "owner": {
                "id": c.owner.id,
                "full_name": c.owner.full_name,
            } if c.owner else None,
            "received_date": c.received_date,
            "target_date": c.target_date,
            "is_overdue": is_ov,
            "days_overdue": days_ov,
            "escalation_level": c.escalation_level,
            "access_level": access_level,
            "handover_status": c.handover_status,
            "delay_explanation": exp,
            "limbo_flags": flags,
            "waiting_on_summary": ws,
        })

    return results, total
