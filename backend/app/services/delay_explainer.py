"""Deterministic Delay Explainer for human-readable complaint status sentences."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Complaint, Handover, StatusHistory, WaitingOnEntry


def generate_delay_explanation(
    db: Session,
    complaint: Complaint,
) -> dict[str, Any]:
    """
    Generate an explainable, deterministic status sentence.
    No generative AI hallucinations: explicitly states 'reason not recorded' when data is absent.
    """
    now = datetime.now(timezone.utc)
    today = now.date()

    # 1. Closed status
    if complaint.status == "CLOSED":
        closed_date_str = complaint.closed_at.strftime("%d %b %Y") if complaint.closed_at else "recently"
        return {
            "sentence": f"Case closed on {closed_date_str}.",
            "tone": "muted",
            "stage": "CLOSED",
            "key_factor": "Case Closed",
        }

    # 2. Resolved status
    if complaint.status == "RESOLVED":
        resolved_date_str = complaint.resolved_at.strftime("%d %b %Y") if complaint.resolved_at else "recently"
        return {
            "sentence": f"Case resolved on {resolved_date_str}. Resolution summary recorded.",
            "tone": "success",
            "stage": "RESOLVED",
            "key_factor": "Resolved",
        }

    # 3. In Transit (Handover pending)
    if complaint.handover_status == "IN_TRANSIT":
        latest_handover = (
            db.query(Handover)
            .filter(Handover.complaint_id == complaint.id, Handover.status == "PENDING")
            .order_by(Handover.initiated_at.desc())
            .first()
        )
        if latest_handover:
            to_code = latest_handover.to_bureau.code if latest_handover.to_bureau else "target bureau"
            days = max(0, (today - latest_handover.initiated_at.date()).days)
            date_str = latest_handover.initiated_at.strftime("%d %b")
            day_text = f"({days} days ago)" if days > 0 else "(today)"
            return {
                "sentence": f"In transit to {to_code} since {date_str} {day_text}, pending official acceptance or return.",
                "tone": "warning" if days < 2 else "danger",
                "stage": "IN_TRANSIT",
                "key_factor": "Handover Pending",
            }

    # 4. Check active Waiting-On entries
    active_waits = (
        db.query(WaitingOnEntry)
        .filter(
            WaitingOnEntry.complaint_id == complaint.id,
            WaitingOnEntry.is_resolved.is_(False),
        )
        .order_by(WaitingOnEntry.since.asc())
        .all()
    )

    if active_waits:
        primary_wait = active_waits[0]
        days_waiting = max(0, (today - primary_wait.since.date()).days)
        party = primary_wait.waiting_on_party
        chaser_name = primary_wait.chaser.full_name if primary_wait.chaser else None
        since_str = primary_wait.since.strftime("%d %b")

        type_label_map = {
            "INSTITUTION_REPLY": "institution reply",
            "BUREAU_OPINION": "bureau opinion",
            "DOCUMENT_SUBMISSION": "document submission",
            "COMMITTEE_REVIEW": "committee review",
            "SUPERVISOR_APPROVAL": "supervisor approval",
            "OTHER": "action",
        }
        type_str = type_label_map.get(primary_wait.waiting_on_type, "response")

        if chaser_name:
            sentence = f"Waiting on {type_str} from {party} since {since_str} ({days_waiting} days); designated chaser is {chaser_name}."
        else:
            sentence = f"Waiting on {type_str} from {party} since {since_str} ({days_waiting} days); no chaser assigned."

        tone = "danger" if days_waiting >= 15 else ("warning" if days_waiting >= 7 else "info")
        return {
            "sentence": sentence,
            "tone": tone,
            "stage": "WAITING",
            "key_factor": f"Waiting on {party}",
        }

    # 5. Overdue or stagnant open case with NO waiting-on entry
    last_status = (
        db.query(StatusHistory)
        .filter(StatusHistory.complaint_id == complaint.id)
        .order_by(StatusHistory.changed_at.desc())
        .first()
    )
    last_change_date = last_status.changed_at.date() if last_status else complaint.created_at.date()
    days_in_status = max(0, (today - last_change_date).days)
    status_label = complaint.status.replace("_", " ").title()

    is_overdue = bool(complaint.target_date and complaint.target_date < today)
    if is_overdue:
        days_overdue = (today - complaint.target_date).days
        return {
            "sentence": f"Case is {days_overdue} days overdue in status '{status_label}' with no active waiting item recorded — delay reason not recorded.",
            "tone": "danger",
            "stage": "OVERDUE",
            "key_factor": "Overdue - Reason Not Recorded",
        }

    if days_in_status >= 7:
        return {
            "sentence": f"In status '{status_label}' for {days_in_status} days without any recorded waiting item or action — delay reason not recorded.",
            "tone": "warning",
            "stage": "STALLED",
            "key_factor": "Idle - Reason Not Recorded",
        }

    # 6. Active and on track
    owner_name = complaint.owner.full_name if complaint.owner else "Unassigned owner"
    bureau_code = complaint.primary_bureau.code if complaint.primary_bureau else "Bureau"
    target_str = complaint.target_date.strftime("%d %b") if complaint.target_date else "None"
    return {
        "sentence": f"Under active processing by {bureau_code} ({owner_name}) for {days_in_status} days; target deadline {target_str}.",
        "tone": "info",
        "stage": "ON_TRACK",
        "key_factor": "On Track",
    }
