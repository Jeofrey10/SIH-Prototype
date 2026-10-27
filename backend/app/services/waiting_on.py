"""Waiting-On Ledger service for transparent delay accountability."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core import errors, permissions
from app.models import Complaint, User, WaitingOnEntry
from app.services.audit import write_audit


VALID_WAITING_TYPES = {
    "INSTITUTION_REPLY": "Institution Reply",
    "BUREAU_OPINION": "Bureau Opinion",
    "DOCUMENT_SUBMISSION": "Document Submission",
    "COMMITTEE_REVIEW": "Committee Review",
    "SUPERVISOR_APPROVAL": "Supervisor Approval",
    "OTHER": "Other Action",
}


def add_waiting_entry(
    db: Session,
    complaint_id: UUID,
    data: dict[str, Any],
    actor: User,
    ip: str | None = None,
    request_id: str | None = None,
) -> WaitingOnEntry:
    """Add a new waiting commitment to the ledger."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise errors.not_found("Complaint", str(complaint_id))

    if complaint.status in ("RESOLVED", "CLOSED"):
        raise errors.bad_request("Cannot add waiting ledger entry for resolved or closed complaint")

    waiting_on_type = data.get("waiting_on_type") or "INSTITUTION_REPLY"
    if waiting_on_type not in VALID_WAITING_TYPES:
        raise errors.validation_error({
            "waiting_on_type": f"Must be one of: {', '.join(VALID_WAITING_TYPES.keys())}"
        })

    waiting_on_party = (data.get("waiting_on_party") or "").strip()
    if not waiting_on_party:
        raise errors.validation_error({
            "waiting_on_party": "Party being waited on is required (e.g., institution name or specific official)"
        })

    chaser_user_id = data.get("chaser_user_id")
    if chaser_user_id:
        if isinstance(chaser_user_id, str):
            chaser_user_id = UUID(chaser_user_id)
        chaser = db.query(User).filter(User.id == chaser_user_id).first()
        if not chaser:
            raise errors.not_found("Chaser User", str(chaser_user_id))

    since = data.get("since")
    now = datetime.now(timezone.utc)
    if since:
        if isinstance(since, str):
            since = datetime.fromisoformat(since)
    else:
        since = now

    notes = data.get("notes")
    if notes:
        notes = notes.strip()

    entry = WaitingOnEntry(
        complaint_id=complaint.id,
        waiting_on_type=waiting_on_type,
        waiting_on_party=waiting_on_party,
        since=since,
        chaser_user_id=chaser_user_id,
        is_resolved=False,
        notes=notes,
        created_by=actor.id,
        created_at=now,
    )
    db.add(entry)
    complaint.updated_at = now
    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="WAITING_ON_ENTRY_ADDED",
        entity_type="WAITING_ON_ENTRY",
        entity_id=str(entry.id),
        complaint_id=complaint.id,
        institution_id=complaint.institution_id,
        after_state={
            "type": waiting_on_type,
            "party": waiting_on_party,
            "chaser_id": str(chaser_user_id) if chaser_user_id else None,
        },
        ip=ip,
        request_id=request_id,
    )

    return entry


def resolve_waiting_entry(
    db: Session,
    complaint_id: UUID,
    entry_id: UUID,
    notes: str | None,
    actor: User,
    ip: str | None = None,
    request_id: str | None = None,
) -> WaitingOnEntry:
    """Mark a waiting entry as resolved."""
    entry = (
        db.query(WaitingOnEntry)
        .filter(
            WaitingOnEntry.id == entry_id,
            WaitingOnEntry.complaint_id == complaint_id,
        )
        .first()
    )
    if not entry:
        raise errors.not_found("WaitingOnEntry", str(entry_id))

    if entry.is_resolved:
        return entry

    now = datetime.now(timezone.utc)
    entry.is_resolved = True
    entry.resolved_at = now
    entry.resolved_by = actor.id

    if notes and notes.strip():
        existing_notes = entry.notes or ""
        entry.notes = f"{existing_notes}\n[Resolved: {notes.strip()}]".strip()

    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if complaint:
        complaint.updated_at = now

    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="WAITING_ON_ENTRY_RESOLVED",
        entity_type="WAITING_ON_ENTRY",
        entity_id=str(entry.id),
        complaint_id=complaint_id,
        institution_id=complaint.institution_id if complaint else None,
        after_state={"resolved_at": str(now), "resolved_by": str(actor.id)},
        ip=ip,
        request_id=request_id,
    )

    return entry


def update_waiting_entry(
    db: Session,
    complaint_id: UUID,
    entry_id: UUID,
    data: dict[str, Any],
    actor: User,
    ip: str | None = None,
    request_id: str | None = None,
) -> WaitingOnEntry:
    """Update chaser or notes on an active waiting entry."""
    entry = (
        db.query(WaitingOnEntry)
        .filter(
            WaitingOnEntry.id == entry_id,
            WaitingOnEntry.complaint_id == complaint_id,
        )
        .first()
    )
    if not entry:
        raise errors.not_found("WaitingOnEntry", str(entry_id))

    if "chaser_user_id" in data:
        cid = data["chaser_user_id"]
        if cid:
            if isinstance(cid, str):
                cid = UUID(cid)
            chaser = db.query(User).filter(User.id == cid).first()
            if not chaser:
                raise errors.not_found("Chaser User", str(cid))
            entry.chaser_user_id = cid
        else:
            entry.chaser_user_id = None

    if "notes" in data and data["notes"] is not None:
        entry.notes = data["notes"].strip()

    if "waiting_on_party" in data and data["waiting_on_party"]:
        entry.waiting_on_party = data["waiting_on_party"].strip()

    if "waiting_on_type" in data and data["waiting_on_type"] in VALID_WAITING_TYPES:
        entry.waiting_on_type = data["waiting_on_type"]

    db.flush()
    return entry


def get_waiting_entries(
    db: Session,
    complaint_id: UUID,
    active_only: bool = False,
) -> list[dict[str, Any]]:
    """Get waiting entries for a complaint with duration metrics."""
    query = db.query(WaitingOnEntry).filter(WaitingOnEntry.complaint_id == complaint_id)
    if active_only:
        query = query.filter(WaitingOnEntry.is_resolved.is_(False))

    records = query.order_by(WaitingOnEntry.since.desc()).all()
    now = datetime.now(timezone.utc)
    results = []

    for r in records:
        end_time = r.resolved_at if r.is_resolved and r.resolved_at else now
        days_waiting = max(0, (end_time.date() - r.since.date()).days)

        results.append({
            "id": r.id,
            "complaint_id": r.complaint_id,
            "waiting_on_type": r.waiting_on_type,
            "waiting_on_type_label": VALID_WAITING_TYPES.get(r.waiting_on_type, r.waiting_on_type),
            "waiting_on_party": r.waiting_on_party,
            "since": r.since,
            "days_waiting": days_waiting,
            "is_resolved": r.is_resolved,
            "resolved_at": r.resolved_at,
            "notes": r.notes,
            "chaser": {
                "id": r.chaser.id,
                "full_name": r.chaser.full_name,
            } if r.chaser else None,
            "resolver": {
                "id": r.resolver.id,
                "full_name": r.resolver.full_name,
            } if r.resolver else None,
            "creator": {
                "id": r.creator.id,
                "full_name": r.creator.full_name,
            } if r.creator else None,
            "created_at": r.created_at,
        })

    return results


def get_waiting_on_summary(
    db: Session,
    complaint_id: UUID,
) -> dict[str, Any]:
    """Return compact waiting summary for list view and dashboard cards."""
    entries = get_waiting_entries(db, complaint_id, active_only=True)
    if not entries:
        return {
            "is_waiting": False,
            "active_count": 0,
            "primary_entry": None,
            "summary_text": "No pending commitments logged",
        }

    # Primary entry is the one with the longest duration (oldest since)
    oldest = max(entries, key=lambda e: e["days_waiting"])
    type_label = oldest["waiting_on_type_label"]
    party = oldest["waiting_on_party"]
    days = oldest["days_waiting"]
    chaser_name = oldest["chaser"]["full_name"] if oldest["chaser"] else "Unassigned"

    summary_text = f"Waiting on {type_label} ({party}) since {oldest['since'].strftime('%d %b')}, {days}d"
    if oldest["chaser"]:
        summary_text += f", chaser: {chaser_name}"
    else:
        summary_text += ", no chaser assigned"

    return {
        "is_waiting": True,
        "active_count": len(entries),
        "primary_entry": oldest,
        "summary_text": summary_text,
    }


def auto_sync_on_status_change(
    db: Session,
    complaint: Complaint,
    from_status: str,
    to_status: str,
    actor: User,
) -> None:
    """Rules-based hook for automated ledger updates during lifecycle transitions."""
    now = datetime.now(timezone.utc)

    # If transitioning to PENDING_INFORMATION and no active entry exists, auto-create one
    if to_status == "PENDING_INFORMATION":
        active_count = (
            db.query(WaitingOnEntry)
            .filter(
                WaitingOnEntry.complaint_id == complaint.id,
                WaitingOnEntry.is_resolved.is_(False),
            )
            .count()
        )
        if active_count == 0:
            inst_name = complaint.institution.name if complaint.institution else "Institution"
            entry = WaitingOnEntry(
                complaint_id=complaint.id,
                waiting_on_type="INSTITUTION_REPLY",
                waiting_on_party=inst_name,
                since=now,
                chaser_user_id=complaint.owner_user_id,
                is_resolved=False,
                notes="Automatically generated when status transitioned to Pending Information",
                created_by=actor.id,
                created_at=now,
            )
            db.add(entry)
            db.flush()

    # If transitioning to RESOLVED or CLOSED, resolve all active entries
    elif to_status in ("RESOLVED", "CLOSED"):
        active_entries = (
            db.query(WaitingOnEntry)
            .filter(
                WaitingOnEntry.complaint_id == complaint.id,
                WaitingOnEntry.is_resolved.is_(False),
            )
            .all()
        )
        for e in active_entries:
            e.is_resolved = True
            e.resolved_at = now
            e.resolved_by = actor.id
            e.notes = ((e.notes or "") + f"\n[Auto-resolved on complaint {to_status.lower()}]").strip()
        db.flush()
