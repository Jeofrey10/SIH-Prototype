"""Relations persistence and management service."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core import errors, permissions
from app.models import Bureau, CaseAssignment, Complaint, ComplaintRelation, User
from app.services.audit import write_audit
from app.services.notifications import notify_users
from app.services.relations.scorer import ALGORITHM_VERSION, calculate_relation_score


def _canonical_ids(id_1: UUID, id_2: UUID) -> tuple[UUID, UUID]:
    """Ensure complaint_a_id < complaint_b_id canonically."""
    if str(id_1) < str(id_2):
        return id_1, id_2
    return id_2, id_1


def _to_complaint_dict(c: Complaint) -> dict[str, Any]:
    """Convert complaint model to dict for scoring."""
    bureau_code = c.primary_bureau.code if c.primary_bureau else None
    return {
        "id": c.id,
        "title": c.title,
        "description": c.description,
        "category": c.category,
        "priority": c.priority,
        "status": c.status,
        "incident_reference": c.incident_reference,
        "incident_date": c.incident_date,
        "received_date": c.received_date,
        "primary_bureau_code": bureau_code,
    }


def preview_related_candidates(
    db: Session,
    data: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    POST /complaints/related-preview
    Evaluate potential relations without persisting anything.
    """
    institution_id = data["institution_id"]
    candidates = (
        db.query(Complaint)
        .filter(Complaint.institution_id == institution_id)
        .all()
    )

    complaint_dict = {
        "category": data.get("category"),
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "incident_reference": data.get("incident_reference"),
        "incident_date": data.get("incident_date"),
        "received_date": data.get("received_date"),
    }

    results: list[dict[str, Any]] = []
    for cand in candidates:
        cand_dict = _to_complaint_dict(cand)
        res = calculate_relation_score(complaint_dict, cand_dict)
        if res["is_suggested"]:
            results.append({
                "candidate_id": cand.id,
                "candidate_reference": cand.reference_number,
                "candidate_title": cand.title,
                "candidate_category": cand.category,
                "candidate_status": cand.status,
                "candidate_primary_bureau": cand.primary_bureau.code if cand.primary_bureau else None,
                "score": res["score"],
                "confidence": res["confidence"],
                "explanation": res,
                "received_date": cand.received_date,
            })

    # Order by score desc, received_date desc, id
    results.sort(
        key=lambda x: (
            -x["score"],
            x["received_date"] or datetime.min.date(),
            str(x["candidate_id"]),
        )
    )
    return results[:10]


def detect_and_persist_relations(
    db: Session,
    complaint: Complaint,
    actor: User | None = None,
    ip: str | None = None,
    request_id: str | None = None,
) -> list[ComplaintRelation]:
    """
    Run detection against other complaints for same institution and persist SUGGESTED relations.
    Skips pairs that already have ANY relation row.
    """
    candidates = (
        db.query(Complaint)
        .filter(
            Complaint.institution_id == complaint.institution_id,
            Complaint.id != complaint.id,
        )
        .all()
    )

    if not candidates:
        return []

    # Get all existing relation pairs involving this complaint
    existing_pairs = (
        db.query(ComplaintRelation.complaint_a_id, ComplaintRelation.complaint_b_id)
        .filter(
            or_(
                ComplaintRelation.complaint_a_id == complaint.id,
                ComplaintRelation.complaint_b_id == complaint.id,
            )
        )
        .all()
    )
    existing_set = set(existing_pairs)

    complaint_dict = _to_complaint_dict(complaint)
    suggested_relations: list[ComplaintRelation] = []

    scored_candidates = []
    for cand in candidates:
        a_id, b_id = _canonical_ids(complaint.id, cand.id)
        if (a_id, b_id) in existing_set:
            continue

        cand_dict = _to_complaint_dict(cand)
        res = calculate_relation_score(complaint_dict, cand_dict)
        if res["is_suggested"]:
            scored_candidates.append((cand, a_id, b_id, res))

    # Order by score desc, received_date desc, id
    scored_candidates.sort(
        key=lambda x: (
            -x[3]["score"],
            x[0].received_date or datetime.min.date(),
            str(x[0].id),
        )
    )

    top_candidates = scored_candidates[:10]

    for cand, a_id, b_id, res in top_candidates:
        rel = ComplaintRelation(
            complaint_a_id=a_id,
            complaint_b_id=b_id,
            status="SUGGESTED",
            relation_type=None,
            score=res["score"],
            confidence=res["confidence"],
            explanation=res,
            algorithm_version=ALGORITHM_VERSION,
            detected_from_complaint_id=complaint.id,
            detected_at=datetime.now(timezone.utc),
        )
        db.add(rel)
        db.flush()
        suggested_relations.append(rel)

        # Audit log
        write_audit(
            db,
            actor_user_id=actor.id if actor else None,
            actor_email=actor.email if actor else "system",
            actor_role=actor.role if actor else "SYSTEM",
            action="RELATION_SUGGESTED",
            entity_type="RELATION",
            entity_id=str(rel.id),
            complaint_id=complaint.id,
            institution_id=complaint.institution_id,
            after_state={
                "complaint_a_id": str(a_id),
                "complaint_b_id": str(b_id),
                "score": res["score"],
                "confidence": res["confidence"],
            },
            ip=ip,
            request_id=request_id,
        )

        # Notify owners (or primary bureau officials) of both complaints
        _notify_related_suggested(db, complaint, cand, actor)

    return suggested_relations


def _notify_related_suggested(
    db: Session,
    c1: Complaint,
    c2: Complaint,
    actor: User | None,
) -> None:
    """Notify owners or primary bureau officials of both complaints."""
    recipients: set[UUID] = set()

    for c in (c1, c2):
        if c.owner_user_id:
            recipients.add(c.owner_user_id)
        elif c.primary_bureau_id:
            officials = (
                db.query(User.id)
                .filter(
                    User.bureau_id == c.primary_bureau_id,
                    User.is_active.is_(True),
                )
                .all()
            )
            for u in officials:
                recipients.add(u.id)

    if recipients:
        notify_users(
            db,
            user_ids=list(recipients),
            type="RELATED_SUGGESTED",
            title=f"Potential duplicate/related complaint detected ({c1.reference_number} & {c2.reference_number})",
            message=f"A related complaint was detected at {c1.institution.name if c1.institution else 'institution'}.",
            complaint_id=c1.id,
            institution_id=c1.institution_id,
            exclude_actor_id=actor.id if actor else None,
        )


def confirm_relation(
    db: Session,
    relation_id: UUID,
    data: dict[str, Any],
    actor: User,
    ip: str | None = None,
    request_id: str | None = None,
) -> ComplaintRelation:
    """
    POST /relations/{id}/confirm
    Confirm relation and optionally add participating bureaus.
    """
    rel = db.query(ComplaintRelation).filter(ComplaintRelation.id == relation_id).first()
    if not rel:
        raise errors.not_found("ComplaintRelation", str(relation_id))

    if rel.status != "SUGGESTED":
        raise errors.conflict(f"Cannot confirm relation in status {rel.status}; must be SUGGESTED")

    relation_type = data.get("relation_type", "RELATED_ISSUE")
    if relation_type not in ("SAME_ISSUE", "RELATED_ISSUE"):
        raise errors.validation_error({"relation_type": "Must be SAME_ISSUE or RELATED_ISSUE"})

    now = datetime.now(timezone.utc)
    rel.status = "CONFIRMED"
    rel.relation_type = relation_type
    rel.reviewed_by = actor.id
    rel.reviewed_at = now
    rel.review_note = data.get("note")

    add_participants = data.get("add_participating_bureaus", True)
    if add_participants:
        # Cross-participate primary bureaus
        c_a = db.query(Complaint).filter(Complaint.id == rel.complaint_a_id).first()
        c_b = db.query(Complaint).filter(Complaint.id == rel.complaint_b_id).first()
        if c_a and c_b:
            _add_mutual_participation(db, c_a, c_b, rel.id, actor, ip, request_id)

    # Automatically group into Issue Thread
    from app.services.threads import get_or_create_thread_for_relation
    get_or_create_thread_for_relation(db, rel)

    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="RELATION_CONFIRMED",
        entity_type="RELATION",
        entity_id=str(rel.id),
        complaint_id=rel.complaint_a_id,
        after_state={
            "status": "CONFIRMED",
            "relation_type": rel.relation_type,
            "reviewed_by": str(actor.id),
            "review_note": rel.review_note,
        },
        ip=ip,
        request_id=request_id,
    )

    # Notify owners of both complaints
    c_a = db.query(Complaint).filter(Complaint.id == rel.complaint_a_id).first()
    c_b = db.query(Complaint).filter(Complaint.id == rel.complaint_b_id).first()
    recipients = []
    if c_a and c_a.owner_user_id:
        recipients.append(c_a.owner_user_id)
    if c_b and c_b.owner_user_id:
        recipients.append(c_b.owner_user_id)

    if recipients:
        notify_users(
            db,
            user_ids=recipients,
            type="RELATION_CONFIRMED",
            title="Related complaint confirmed",
            message=f"Relation between {c_a.reference_number if c_a else ''} and {c_b.reference_number if c_b else ''} confirmed as {relation_type}.",
            complaint_id=rel.complaint_a_id,
            institution_id=c_a.institution_id if c_a else None,
            exclude_actor_id=actor.id,
        )

    return rel


def _add_mutual_participation(
    db: Session,
    c_a: Complaint,
    c_b: Complaint,
    relation_id: UUID,
    actor: User,
    ip: str | None,
    request_id: str | None,
) -> None:
    """Add each complaint's primary bureau as PARTICIPATING on the other complaint."""
    now = datetime.now(timezone.utc)
    reason = f"Added on confirmation of related complaint relation {relation_id}"

    # Add B's primary bureau to A
    if c_b.primary_bureau_id and c_b.primary_bureau_id != c_a.primary_bureau_id:
        existing_on_a = (
            db.query(CaseAssignment)
            .filter(
                CaseAssignment.complaint_id == c_a.id,
                CaseAssignment.bureau_id == c_b.primary_bureau_id,
                CaseAssignment.is_active.is_(True),
            )
            .first()
        )
        if not existing_on_a:
            assign_a = CaseAssignment(
                complaint_id=c_a.id,
                bureau_id=c_b.primary_bureau_id,
                role_in_case="PARTICIPATING",
                assigned_by=actor.id,
                assigned_at=now,
                reason=reason,
                is_active=True,
            )
            db.add(assign_a)
            # Update denormalized list on c_a
            b_bureau = db.query(Bureau).filter(Bureau.id == c_b.primary_bureau_id).first()
            if b_bureau and b_bureau.code not in (c_a.participating_bureau_codes or []):
                new_codes = list(c_a.participating_bureau_codes or [])
                new_codes.append(b_bureau.code)
                c_a.participating_bureau_codes = new_codes

            write_audit(
                db,
                actor_user_id=actor.id,
                actor_email=actor.email,
                actor_role=actor.role,
                action="ASSIGNMENT_PARTICIPANT_ADDED",
                entity_type="ASSIGNMENT",
                entity_id=str(c_b.primary_bureau_id),
                complaint_id=c_a.id,
                institution_id=c_a.institution_id,
                after_state={"bureau_code": b_bureau.code if b_bureau else None, "reason": reason},
                ip=ip,
                request_id=request_id,
            )

    # Add A's primary bureau to B
    if c_a.primary_bureau_id and c_a.primary_bureau_id != c_b.primary_bureau_id:
        existing_on_b = (
            db.query(CaseAssignment)
            .filter(
                CaseAssignment.complaint_id == c_b.id,
                CaseAssignment.bureau_id == c_a.primary_bureau_id,
                CaseAssignment.is_active.is_(True),
            )
            .first()
        )
        if not existing_on_b:
            assign_b = CaseAssignment(
                complaint_id=c_b.id,
                bureau_id=c_a.primary_bureau_id,
                role_in_case="PARTICIPATING",
                assigned_by=actor.id,
                assigned_at=now,
                reason=reason,
                is_active=True,
            )
            db.add(assign_b)
            # Update denormalized list on c_b
            a_bureau = db.query(Bureau).filter(Bureau.id == c_a.primary_bureau_id).first()
            if a_bureau and a_bureau.code not in (c_b.participating_bureau_codes or []):
                new_codes = list(c_b.participating_bureau_codes or [])
                new_codes.append(a_bureau.code)
                c_b.participating_bureau_codes = new_codes

            write_audit(
                db,
                actor_user_id=actor.id,
                actor_email=actor.email,
                actor_role=actor.role,
                action="ASSIGNMENT_PARTICIPANT_ADDED",
                entity_type="ASSIGNMENT",
                entity_id=str(c_a.primary_bureau_id),
                complaint_id=c_b.id,
                institution_id=c_b.institution_id,
                after_state={"bureau_code": a_bureau.code if a_bureau else None, "reason": reason},
                ip=ip,
                request_id=request_id,
            )


def dismiss_relation(
    db: Session,
    relation_id: UUID,
    data: dict[str, Any],
    actor: User,
    ip: str | None = None,
    request_id: str | None = None,
) -> ComplaintRelation:
    """
    POST /relations/{id}/dismiss
    Dismiss suggested relation.
    """
    rel = db.query(ComplaintRelation).filter(ComplaintRelation.id == relation_id).first()
    if not rel:
        raise errors.not_found("ComplaintRelation", str(relation_id))

    if rel.status != "SUGGESTED":
        raise errors.conflict(f"Cannot dismiss relation in status {rel.status}; must be SUGGESTED")

    note = data.get("note", "").strip()
    if not note:
        raise errors.validation_error({"note": "Note is required to dismiss a relation"})

    now = datetime.now(timezone.utc)
    rel.status = "DISMISSED"
    rel.reviewed_by = actor.id
    rel.reviewed_at = now
    rel.review_note = note

    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="RELATION_DISMISSED",
        entity_type="RELATION",
        entity_id=str(rel.id),
        complaint_id=rel.complaint_a_id,
        after_state={
            "status": "DISMISSED",
            "reviewed_by": str(actor.id),
            "review_note": note,
        },
        ip=ip,
        request_id=request_id,
    )

    c_a = db.query(Complaint).filter(Complaint.id == rel.complaint_a_id).first()
    c_b = db.query(Complaint).filter(Complaint.id == rel.complaint_b_id).first()
    recipients = []
    if c_a and c_a.owner_user_id:
        recipients.append(c_a.owner_user_id)
    if c_b and c_b.owner_user_id:
        recipients.append(c_b.owner_user_id)

    if recipients:
        notify_users(
            db,
            user_ids=recipients,
            type="RELATION_DISMISSED",
            title="Suggested relation dismissed",
            message=f"Relation between {c_a.reference_number if c_a else ''} and {c_b.reference_number if c_b else ''} dismissed.",
            complaint_id=rel.complaint_a_id,
            institution_id=c_a.institution_id if c_a else None,
            exclude_actor_id=actor.id,
        )

    return rel


def revert_relation(
    db: Session,
    relation_id: UUID,
    data: dict[str, Any],
    actor: User,
    ip: str | None = None,
    request_id: str | None = None,
) -> ComplaintRelation:
    """
    POST /relations/{id}/revert (Supervisor only)
    Reverts a reviewed relation (flips status between CONFIRMED and DISMISSED).
    """
    if actor.role != "SUPERVISOR":
        raise errors.forbidden("Only supervisors can revert a relation review")

    rel = db.query(ComplaintRelation).filter(ComplaintRelation.id == relation_id).first()
    if not rel:
        raise errors.not_found("ComplaintRelation", str(relation_id))

    note = data.get("note", "").strip()
    if not note:
        raise errors.validation_error({"note": "Note is required to revert a relation"})

    target_status = data.get("status")
    if target_status:
        if target_status not in ("CONFIRMED", "DISMISSED"):
            raise errors.validation_error({"status": "Must be CONFIRMED or DISMISSED"})
    else:
        # Flip current
        target_status = "DISMISSED" if rel.status == "CONFIRMED" else "CONFIRMED"

    old_status = rel.status
    now = datetime.now(timezone.utc)
    rel.status = target_status
    rel.reviewed_by = actor.id
    rel.reviewed_at = now
    rel.review_note = f"[REVERTED from {old_status}] {note}"

    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="RELATION_REVERTED",
        entity_type="RELATION",
        entity_id=str(rel.id),
        complaint_id=rel.complaint_a_id,
        before_state={"status": old_status},
        after_state={"status": target_status, "note": note},
        ip=ip,
        request_id=request_id,
    )

    return rel


def get_complaint_relations(
    db: Session,
    complaint_id: UUID,
    actor: User,
) -> list[dict[str, Any]]:
    """GET /complaints/{id}/relations"""
    relations = (
        db.query(ComplaintRelation)
        .filter(
            or_(
                ComplaintRelation.complaint_a_id == complaint_id,
                ComplaintRelation.complaint_b_id == complaint_id,
            )
        )
        .order_by(ComplaintRelation.score.desc())
        .all()
    )

    results = []
    for r in relations:
        other_id = r.complaint_b_id if r.complaint_a_id == complaint_id else r.complaint_a_id
        other_complaint = db.query(Complaint).filter(Complaint.id == other_id).first()
        if not other_complaint:
            continue

        access_level = permissions.get_complaint_access_level(other_complaint, actor)
        is_full = access_level == "FULL"

        results.append({
            "id": r.id,
            "status": r.status,
            "relation_type": r.relation_type,
            "score": r.score,
            "confidence": r.confidence,
            "explanation": r.explanation,
            "algorithm_version": r.algorithm_version,
            "detected_at": r.detected_at,
            "reviewed_by": r.reviewed_by,
            "reviewed_at": r.reviewed_at,
            "review_note": r.review_note,
            "other_complaint": {
                "id": other_complaint.id,
                "reference_number": other_complaint.reference_number,
                "title": other_complaint.title if is_full else None,
                "category": other_complaint.category,
                "priority": other_complaint.priority,
                "status": other_complaint.status,
                "received_date": other_complaint.received_date,
                "primary_bureau": other_complaint.primary_bureau.code if other_complaint.primary_bureau else None,
                "access_level": access_level,
            },
        })

    return results


def list_relations(
    db: Session,
    status: str | None = None,
    institution_id: UUID | None = None,
    actor: User | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    """GET /relations with filters and pagination."""
    query = db.query(ComplaintRelation)
    if status:
        query = query.filter(ComplaintRelation.status == status)

    if institution_id:
        query = query.join(
            Complaint, ComplaintRelation.complaint_a_id == Complaint.id
        ).filter(Complaint.institution_id == institution_id)

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(ComplaintRelation.detected_at.desc()).offset(offset).limit(page_size).all()

    out = []
    for r in items:
        c_a = db.query(Complaint).filter(Complaint.id == r.complaint_a_id).first()
        c_b = db.query(Complaint).filter(Complaint.id == r.complaint_b_id).first()
        out.append({
            "id": r.id,
            "status": r.status,
            "relation_type": r.relation_type,
            "score": r.score,
            "confidence": r.confidence,
            "explanation": r.explanation,
            "algorithm_version": r.algorithm_version,
            "detected_at": r.detected_at,
            "reviewed_by": r.reviewed_by,
            "reviewed_at": r.reviewed_at,
            "review_note": r.review_note,
            "complaint_a": {
                "id": c_a.id,
                "reference_number": c_a.reference_number,
                "title": c_a.title,
                "category": c_a.category,
                "status": c_a.status,
            } if c_a else None,
            "complaint_b": {
                "id": c_b.id,
                "reference_number": c_b.reference_number,
                "title": c_b.title,
                "category": c_b.category,
                "status": c_b.status,
            } if c_b else None,
        })

    return out, total
