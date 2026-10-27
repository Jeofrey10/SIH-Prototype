"""Limbo & Ping-Pong detector for finding silently stalled complaints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import (
    CaseAssignment, Complaint, ComplaintNote,
    Handover, StatusHistory, WaitingOnEntry
)


def detect_limbo_for_complaint_obj(
    db: Session,
    complaint: Complaint,
) -> list[dict[str, Any]]:
    """Evaluate deterministic limbo and ping-pong rules for an open complaint."""
    if complaint.status in ("RESOLVED", "CLOSED"):
        return []

    flags: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    # Rule 1: UNACCEPTED_HANDOVER
    if complaint.handover_status == "IN_TRANSIT":
        latest_handover = (
            db.query(Handover)
            .filter(Handover.complaint_id == complaint.id, Handover.status == "PENDING")
            .order_by(Handover.initiated_at.desc())
            .first()
        )
        if latest_handover:
            hours_in_transit = (now - latest_handover.initiated_at).total_seconds() / 3600.0
            to_code = latest_handover.to_bureau.code if latest_handover.to_bureau else "Receiving Bureau"
            if hours_in_transit >= 48:
                flags.append({
                    "code": "UNACCEPTED_HANDOVER",
                    "severity": "CRITICAL",
                    "title": "Unaccepted Handover (>48h)",
                    "description": f"Transferred to {to_code} {int(hours_in_transit // 24)}d {int(hours_in_transit % 24)}h ago, still waiting for acceptance.",
                    "since": latest_handover.initiated_at.isoformat(),
                })
            elif hours_in_transit >= 24:
                flags.append({
                    "code": "UNACCEPTED_HANDOVER",
                    "severity": "WARNING",
                    "title": "Pending Bureau Handover",
                    "description": f"Transferred to {to_code} {int(hours_in_transit)}h ago, awaiting receipt.",
                    "since": latest_handover.initiated_at.isoformat(),
                })

    # Rule 2: NO_COMMITMENT (Open case with no active waiting entry and inactive for 7+ days)
    active_wait_count = (
        db.query(WaitingOnEntry)
        .filter(
            WaitingOnEntry.complaint_id == complaint.id,
            WaitingOnEntry.is_resolved.is_(False),
        )
        .count()
    )

    last_status = (
        db.query(StatusHistory)
        .filter(StatusHistory.complaint_id == complaint.id)
        .order_by(StatusHistory.changed_at.desc())
        .first()
    )
    last_action_date = last_status.changed_at if last_status else complaint.created_at

    # Also check if recent notes exist
    last_note = (
        db.query(ComplaintNote)
        .filter(ComplaintNote.complaint_id == complaint.id)
        .order_by(ComplaintNote.created_at.desc())
        .first()
    )
    if last_note and last_note.created_at > last_action_date:
        last_action_date = last_note.created_at

    days_stagnant = max(0, (now.date() - last_action_date.date()).days)

    if active_wait_count == 0 and days_stagnant >= 7:
        severity = "CRITICAL" if days_stagnant >= 14 else "WARNING"
        flags.append({
            "code": "NO_COMMITMENT",
            "severity": severity,
            "title": f"No Active Commitment ({days_stagnant}d idle)",
            "description": f"Case has had no recorded waiting item or activity for {days_stagnant} days. Action responsibility is unassigned.",
            "since": last_action_date.isoformat(),
        })

    # Rule 3: PING_PONG (Inter-bureau transfers >= 2 OR flip-flopping statuses >= 3)
    bureau_assignments_count = (
        db.query(CaseAssignment)
        .filter(
            CaseAssignment.complaint_id == complaint.id,
            CaseAssignment.role_in_case == "PRIMARY",
        )
        .count()
    )
    # If 2 or more distinct primary assignments were created, it's transferred multiple times
    if bureau_assignments_count >= 3:
        flags.append({
            "code": "PING_PONG",
            "severity": "CRITICAL",
            "title": "Bureau Ping-Pong",
            "description": f"Case has experienced {bureau_assignments_count - 1} inter-bureau primary transfers, indicating unclear jurisdiction.",
            "since": complaint.created_at.isoformat(),
        })
    elif bureau_assignments_count == 2:
        flags.append({
            "code": "PING_PONG",
            "severity": "WARNING",
            "title": "Inter-Bureau Transfer",
            "description": "Case was previously transferred between bureaus.",
            "since": complaint.created_at.isoformat(),
        })

    status_changes = (
        db.query(StatusHistory.to_status)
        .filter(StatusHistory.complaint_id == complaint.id)
        .order_by(StatusHistory.changed_at.asc())
        .all()
    )
    if len(status_changes) >= 4:
        # Check for oscillating transitions (e.g. A -> B -> A -> B)
        statuses = [s[0] for s in status_changes]
        reversals = 0
        for i in range(2, len(statuses)):
            if statuses[i] == statuses[i - 2] and statuses[i] != statuses[i - 1]:
                reversals += 1
        if reversals >= 2:
            flags.append({
                "code": "STATUS_FLIP_FLOP",
                "severity": "WARNING",
                "title": "Status Oscillation",
                "description": f"Complaint status has reversed {reversals} times (e.g., between review and pending information).",
                "since": last_action_date.isoformat(),
            })

    # Rule 4: NO_CHASER
    unassigned_chasers = (
        db.query(WaitingOnEntry)
        .filter(
            WaitingOnEntry.complaint_id == complaint.id,
            WaitingOnEntry.is_resolved.is_(False),
            WaitingOnEntry.chaser_user_id.is_(None),
        )
        .all()
    )
    for u in unassigned_chasers:
        wait_days = max(0, (now.date() - u.since.date()).days)
        if wait_days >= 3:
            flags.append({
                "code": "UNASSIGNED_CHASER",
                "severity": "WARNING",
                "title": f"No Chaser Assigned ({wait_days}d)",
                "description": f"Waiting on {u.waiting_on_party} for {wait_days} days without a designated follow-up official.",
                "since": u.since.isoformat(),
            })
            break  # one flag is enough

    return flags


def detect_limbo_flags(db: Session, complaint_id: UUID) -> list[dict[str, Any]]:
    """Public helper to get limbo flags for a single complaint."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        return []
    return detect_limbo_for_complaint_obj(db, complaint)


def get_limbo_summary(db: Session) -> dict[str, Any]:
    """Scan all open complaints and compute summary statistics for stuck cases."""
    open_complaints = (
        db.query(Complaint)
        .filter(Complaint.status.notin_(("RESOLVED", "CLOSED")))
        .all()
    )

    stuck_cases: list[dict[str, Any]] = []
    category_counts = {
        "UNACCEPTED_HANDOVER": 0,
        "NO_COMMITMENT": 0,
        "PING_PONG": 0,
        "STATUS_FLIP_FLOP": 0,
        "UNASSIGNED_CHASER": 0,
    }
    critical_count = 0
    warning_count = 0

    for c in open_complaints:
        flags = detect_limbo_for_complaint_obj(db, c)
        if flags:
            has_crit = any(f["severity"] == "CRITICAL" for f in flags)
            if has_crit:
                critical_count += 1
            else:
                warning_count += 1

            for f in flags:
                code = f.get("code")
                if code in category_counts:
                    category_counts[code] += 1

            stuck_cases.append({
                "complaint_id": c.id,
                "reference_number": c.reference_number,
                "institution_name": c.institution.name if c.institution else None,
                "primary_bureau": c.primary_bureau.code if c.primary_bureau else None,
                "status": c.status,
                "target_date": c.target_date,
                "flags": flags,
                "highest_severity": "CRITICAL" if has_crit else "WARNING",
            })

    # Sort stuck cases by CRITICAL first, then number of flags
    stuck_cases.sort(
        key=lambda x: (1 if x["highest_severity"] == "CRITICAL" else 0, len(x["flags"])),
        reverse=True,
    )

    return {
        "total_stuck_count": len(stuck_cases),
        "critical_count": critical_count,
        "warning_count": warning_count,
        "breakdown": category_counts,
        "cases": stuck_cases[:25],
    }
