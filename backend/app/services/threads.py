"""Issue Threads service for grouping confirmed complaint relations and combined briefs."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core import errors
from app.models import (
    Bureau, Complaint, ComplaintRelation,
    Institution, IssueThread, User
)


def get_or_create_thread_for_relation(
    db: Session,
    rel: ComplaintRelation,
) -> IssueThread:
    """Assign confirmed relation to an existing thread or initialize a new IssueThread."""
    c_a = db.query(Complaint).filter(Complaint.id == rel.complaint_a_id).first()
    c_b = db.query(Complaint).filter(Complaint.id == rel.complaint_b_id).first()
    now = datetime.now(timezone.utc)

    # Check if either complaint is already part of a confirmed relation with a thread_id
    existing_rel_a = (
        db.query(ComplaintRelation)
        .filter(
            ComplaintRelation.status == "CONFIRMED",
            ComplaintRelation.thread_id.isnot(None),
            (ComplaintRelation.complaint_a_id == rel.complaint_a_id) |
            (ComplaintRelation.complaint_b_id == rel.complaint_a_id),
        )
        .first()
    )

    existing_rel_b = (
        db.query(ComplaintRelation)
        .filter(
            ComplaintRelation.status == "CONFIRMED",
            ComplaintRelation.thread_id.isnot(None),
            (ComplaintRelation.complaint_a_id == rel.complaint_b_id) |
            (ComplaintRelation.complaint_b_id == rel.complaint_b_id),
        )
        .first()
    )

    thread: IssueThread | None = None

    if existing_rel_a and existing_rel_a.thread_id:
        thread = db.query(IssueThread).filter(IssueThread.id == existing_rel_a.thread_id).first()
    elif existing_rel_b and existing_rel_b.thread_id:
        thread = db.query(IssueThread).filter(IssueThread.id == existing_rel_b.thread_id).first()

    if not thread:
        category_name = (c_a.category if c_a else "Related").replace("_", " ").title()
        inst_name = c_a.institution.name if c_a and c_a.institution else "Institution"
        title = f"Thread: {category_name} - {inst_name[:40]}"

        # Deterministic combined brief
        brief_lines = [
            f"Consolidated issue thread tracking related cases regarding {category_name}.",
            f"Primary institution: {inst_name}.",
            f"Initial linked complaints: {c_a.reference_number if c_a else ''} & {c_b.reference_number if c_b else ''}.",
        ]
        if rel.explanation and isinstance(rel.explanation, dict):
            shared_terms = rel.explanation.get("shared_domain_terms") or []
            if shared_terms:
                brief_lines.append(f"Key overlapping themes: {', '.join(shared_terms)}.")

        thread = IssueThread(
            title=title,
            brief="\n".join(brief_lines),
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )
        db.add(thread)
        db.flush()

    rel.thread_id = thread.id
    db.flush()
    return thread


def list_threads(
    db: Session,
    status: str | None = "ACTIVE",
) -> list[dict[str, Any]]:
    """List all threads with complaint counts and member details."""
    query = db.query(IssueThread)
    if status:
        query = query.filter(IssueThread.status == status)

    threads = query.order_by(IssueThread.updated_at.desc()).all()
    results = []

    for t in threads:
        # Find all confirmed relations for this thread
        rels = (
            db.query(ComplaintRelation)
            .filter(ComplaintRelation.thread_id == t.id)
            .all()
        )
        complaint_ids: set[UUID] = set()
        for r in rels:
            complaint_ids.add(r.complaint_a_id)
            complaint_ids.add(r.complaint_b_id)

        complaints = (
            db.query(Complaint)
            .filter(Complaint.id.in_(complaint_ids))
            .all()
            if complaint_ids else []
        )

        institutions = {c.institution.name for c in complaints if c.institution}
        bureaus = {c.primary_bureau.code for c in complaints if c.primary_bureau}
        open_count = sum(1 for c in complaints if c.status not in ("RESOLVED", "CLOSED"))

        results.append({
            "id": t.id,
            "title": t.title,
            "brief": t.brief,
            "status": t.status,
            "complaint_count": len(complaints),
            "open_complaint_count": open_count,
            "institutions": list(institutions),
            "bureaus": list(bureaus),
            "complaint_references": [c.reference_number for c in complaints],
            "created_at": t.created_at,
            "updated_at": t.updated_at,
        })

    return results


def get_thread_detail(
    db: Session,
    thread_id: UUID,
) -> dict[str, Any]:
    """Get complete graph view of an issue thread: member complaints and explainable links."""
    thread = db.query(IssueThread).filter(IssueThread.id == thread_id).first()
    if not thread:
        raise errors.not_found("IssueThread", str(thread_id))

    rels = (
        db.query(ComplaintRelation)
        .filter(ComplaintRelation.thread_id == thread.id)
        .all()
    )

    complaint_ids: set[UUID] = set()
    for r in rels:
        complaint_ids.add(r.complaint_a_id)
        complaint_ids.add(r.complaint_b_id)

    complaints = (
        db.query(Complaint)
        .filter(Complaint.id.in_(complaint_ids))
        .all()
        if complaint_ids else []
    )

    complaint_map = {c.id: c for c in complaints}

    links = []
    for r in rels:
        c_a = complaint_map.get(r.complaint_a_id)
        c_b = complaint_map.get(r.complaint_b_id)
        links.append({
            "relation_id": r.id,
            "source_id": r.complaint_a_id,
            "source_reference": c_a.reference_number if c_a else None,
            "target_id": r.complaint_b_id,
            "target_reference": c_b.reference_number if c_b else None,
            "relation_type": r.relation_type,
            "score": r.score,
            "confidence": r.confidence,
            "explanation": r.explanation,
            "detected_at": r.detected_at,
            "reviewed_at": r.reviewed_at,
        })

    member_nodes = []
    for c in complaints:
        member_nodes.append({
            "id": c.id,
            "reference_number": c.reference_number,
            "title": c.title,
            "category": c.category,
            "status": c.status,
            "priority": c.priority,
            "institution": {
                "id": c.institution.id,
                "name": c.institution.name,
                "code": c.institution.code,
            } if c.institution else None,
            "primary_bureau": {
                "id": c.primary_bureau.id,
                "code": c.primary_bureau.code,
            } if c.primary_bureau else None,
            "owner": {
                "id": c.owner.id,
                "full_name": c.owner.full_name,
            } if c.owner else None,
            "received_date": c.received_date,
            "target_date": c.target_date,
        })

    return {
        "id": thread.id,
        "title": thread.title,
        "brief": thread.brief,
        "status": thread.status,
        "created_at": thread.created_at,
        "updated_at": thread.updated_at,
        "members": member_nodes,
        "links": links,
    }


def update_thread_brief(
    db: Session,
    thread_id: UUID,
    brief: str,
    title: str | None = None,
) -> IssueThread:
    """Update editable consolidated brief for an issue thread."""
    thread = db.query(IssueThread).filter(IssueThread.id == thread_id).first()
    if not thread:
        raise errors.not_found("IssueThread", str(thread_id))

    thread.brief = brief.strip()
    if title and title.strip():
        thread.title = title.strip()
    thread.updated_at = datetime.now(timezone.utc)
    db.flush()
    return thread
