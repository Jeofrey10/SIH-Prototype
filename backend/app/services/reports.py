"""Reporting service with JSON and CSV exports."""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models import Bureau, Complaint, Institution, User
from app.services.analytics import OPEN_STATUSES
from app.services.audit import write_audit


def _sanitize_csv_cell(value: Any) -> str:
    """Guard against CSV / spreadsheet formula injection."""
    if value is None:
        return ""
    val_str = str(value)
    if val_str and val_str[0] in ("=", "+", "-", "@"):
        return f"'{val_str}"
    return val_str


def _apply_role_scope(query, actor: User):
    """Filter complaints for officials to only cases where their bureau participates."""
    if actor.role in ("RB_OFFICIAL", "PGRC_OFFICIAL") and actor.bureau_id:
        bureau = actor.bureau
        b_code = bureau.code if bureau else ""
        return query.filter(
            or_(
                Complaint.primary_bureau_id == actor.bureau_id,
                Complaint.participating_bureau_codes.any(b_code),
            )
        )
    return query


def get_overdue_report(
    db: Session,
    actor: User,
    date_from: date | None = None,
    date_to: date | None = None,
    bureau_id: UUID | None = None,
    institution_id: UUID | None = None,
) -> list[dict[str, Any]]:
    """GET /reports/overdue"""
    today = datetime.now(timezone.utc).date()
    query = db.query(Complaint).filter(
        Complaint.status.in_(OPEN_STATUSES),
        Complaint.target_date < today,
    )
    query = _apply_role_scope(query, actor)

    if date_from:
        query = query.filter(Complaint.received_date >= date_from)
    if date_to:
        query = query.filter(Complaint.received_date <= date_to)
    if bureau_id:
        query = query.filter(Complaint.primary_bureau_id == bureau_id)
    if institution_id:
        query = query.filter(Complaint.institution_id == institution_id)

    complaints = query.order_by(Complaint.target_date.asc()).all()

    results = []
    for c in complaints:
        days_ov = (today - c.target_date).days if c.target_date else 0
        results.append({
            "reference_number": c.reference_number,
            "institution_code": c.institution.code if c.institution else "",
            "institution_name": c.institution.name if c.institution else "",
            "category": c.category,
            "priority": c.priority,
            "status": c.status,
            "primary_bureau": c.primary_bureau.code if c.primary_bureau else "",
            "owner": c.owner.full_name if c.owner else "Unassigned",
            "received_date": str(c.received_date) if c.received_date else "",
            "target_date": str(c.target_date) if c.target_date else "",
            "days_overdue": days_ov,
            "escalation_level": c.escalation_level,
            "escalation_recommended": c.escalation_recommended,
        })

    return results


def export_overdue_csv(
    db: Session,
    actor: User,
    filters: dict[str, Any],
    ip: str | None = None,
    request_id: str | None = None,
) -> tuple[str, str]:
    """Export overdue report as CSV string and filename."""
    rows = get_overdue_report(
        db,
        actor,
        date_from=filters.get("date_from"),
        date_to=filters.get("date_to"),
        bureau_id=filters.get("bureau_id"),
        institution_id=filters.get("institution_id"),
    )

    fieldnames = [
        "reference_number",
        "institution_code",
        "institution_name",
        "category",
        "priority",
        "status",
        "primary_bureau",
        "owner",
        "received_date",
        "target_date",
        "days_overdue",
        "escalation_level",
        "escalation_recommended",
    ]

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(fieldnames)

    for r in rows:
        writer.writerow([_sanitize_csv_cell(r.get(f)) for f in fieldnames])

    csv_data = output.getvalue()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"overdue_complaints_{timestamp}.csv"

    # Write audit log REPORT_EXPORTED
    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="REPORT_EXPORTED",
        entity_type="REPORT",
        entity_id="overdue",
        after_state={
            "report_name": "overdue",
            "row_count": len(rows),
            "filters": {k: str(v) for k, v in filters.items() if v is not None},
        },
        ip=ip,
        request_id=request_id,
    )

    return csv_data, filename


def get_complaints_report(
    db: Session,
    actor: User,
    filters: dict[str, Any],
) -> list[dict[str, Any]]:
    """GET /reports/complaints"""
    today = datetime.now(timezone.utc).date()
    query = db.query(Complaint)
    query = _apply_role_scope(query, actor)

    if filters.get("date_from"):
        query = query.filter(Complaint.received_date >= filters["date_from"])
    if filters.get("date_to"):
        query = query.filter(Complaint.received_date <= filters["date_to"])
    if filters.get("bureau_id"):
        query = query.filter(Complaint.primary_bureau_id == filters["bureau_id"])
    if filters.get("institution_id"):
        query = query.filter(Complaint.institution_id == filters["institution_id"])
    if filters.get("status"):
        query = query.filter(Complaint.status == filters["status"])

    complaints = query.order_by(Complaint.received_date.desc()).all()
    results = []
    for c in complaints:
        is_ov = bool(c.target_date and c.target_date < today and c.status in OPEN_STATUSES)
        days_ov = (today - c.target_date).days if is_ov else 0
        results.append({
            "reference_number": c.reference_number,
            "institution_code": c.institution.code if c.institution else "",
            "institution_name": c.institution.name if c.institution else "",
            "category": c.category,
            "priority": c.priority,
            "status": c.status,
            "primary_bureau": c.primary_bureau.code if c.primary_bureau else "",
            "owner": c.owner.full_name if c.owner else "Unassigned",
            "received_date": str(c.received_date) if c.received_date else "",
            "target_date": str(c.target_date) if c.target_date else "",
            "days_overdue": days_ov,
            "escalation_level": c.escalation_level,
        })
    return results


def export_complaints_csv(
    db: Session,
    actor: User,
    filters: dict[str, Any],
    ip: str | None = None,
    request_id: str | None = None,
) -> tuple[str, str]:
    """Export complaints report as CSV."""
    rows = get_complaints_report(db, actor, filters)
    fieldnames = [
        "reference_number",
        "institution_code",
        "institution_name",
        "category",
        "priority",
        "status",
        "primary_bureau",
        "owner",
        "received_date",
        "target_date",
        "days_overdue",
        "escalation_level",
    ]

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(fieldnames)
    for r in rows:
        writer.writerow([_sanitize_csv_cell(r.get(f)) for f in fieldnames])

    csv_data = output.getvalue()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"complaints_report_{timestamp}.csv"

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="REPORT_EXPORTED",
        entity_type="REPORT",
        entity_id="complaints",
        after_state={
            "report_name": "complaints",
            "row_count": len(rows),
            "filters": {k: str(v) for k, v in filters.items() if v is not None},
        },
        ip=ip,
        request_id=request_id,
    )
    return csv_data, filename
