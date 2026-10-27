"""Dashboard analytics services."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, distinct, func, or_
from sqlalchemy.orm import Session

from app.models import Bureau, CaseAssignment, Complaint, ComplaintRelation, Institution


ALL_STATUSES = [
    "REGISTERED",
    "UNDER_REVIEW",
    "ACTION_INITIATED",
    "PENDING_INFORMATION",
    "RESOLVED",
    "CLOSED",
    "REOPENED",
]

OPEN_STATUSES = [
    "REGISTERED",
    "UNDER_REVIEW",
    "ACTION_INITIATED",
    "PENDING_INFORMATION",
    "REOPENED",
]


def get_analytics_summary(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    bureau_id: UUID | None = None,
    institution_id: UUID | None = None,
    category: str | None = None,
    priority: str | None = None,
) -> dict[str, Any]:
    """GET /analytics/summary"""
    today = datetime.now(timezone.utc).date()
    query = db.query(Complaint)

    if date_from:
        query = query.filter(Complaint.received_date >= date_from)
    if date_to:
        query = query.filter(Complaint.received_date <= date_to)
    if bureau_id:
        query = query.filter(Complaint.primary_bureau_id == bureau_id)
    if institution_id:
        query = query.filter(Complaint.institution_id == institution_id)
    if category:
        query = query.filter(Complaint.category == category)
    if priority:
        query = query.filter(Complaint.priority == priority)

    total = query.count()
    open_count = query.filter(Complaint.status.in_(OPEN_STATUSES)).count()
    resolved_count = query.filter(Complaint.status == "RESOLVED").count()
    closed_count = query.filter(Complaint.status == "CLOSED").count()

    overdue_open = query.filter(
        Complaint.status.in_(OPEN_STATUSES),
        Complaint.target_date < today,
    ).count()

    escalated_open = query.filter(
        Complaint.status.in_(OPEN_STATUSES),
        Complaint.escalation_level > 0,
    ).count()

    escalation_recommended_open = query.filter(
        Complaint.status.in_(OPEN_STATUSES),
        Complaint.escalation_recommended.is_(True),
    ).count()

    seven_days_ago = today - timedelta(days=7)
    received_last_7_days = query.filter(Complaint.received_date >= seven_days_ago).count()

    # Institutions with open cases
    institutions_with_open = (
        query.filter(Complaint.status.in_(OPEN_STATUSES))
        .with_entities(func.count(distinct(Complaint.institution_id)))
        .scalar()
        or 0
    )

    # Institutions with multi-bureau open cases
    # Query institutions having open complaints with >1 distinct primary or participating bureau
    multi_bureau_inst_ids = (
        db.query(Complaint.institution_id)
        .filter(Complaint.status.in_(OPEN_STATUSES))
        .group_by(Complaint.institution_id)
        .having(
            or_(
                func.count(distinct(Complaint.primary_bureau_id)) > 1,
                func.bool_or(func.cardinality(Complaint.participating_bureau_codes) > 0),
            )
        )
        .all()
    )
    institutions_with_multi_bureau_open = len(multi_bureau_inst_ids)

    # Relations counts
    confirmed_relations = (
        db.query(func.count(ComplaintRelation.id))
        .filter(ComplaintRelation.status == "CONFIRMED")
        .scalar()
        or 0
    )

    pending_relation_reviews = (
        db.query(func.count(ComplaintRelation.id))
        .filter(ComplaintRelation.status == "SUGGESTED")
        .scalar()
        or 0
    )

    unassigned_owner_open = query.filter(
        Complaint.status.in_(OPEN_STATUSES),
        Complaint.owner_user_id.is_(None),
    ).count()

    return {
        "total": total,
        "open": open_count,
        "resolved": resolved_count,
        "closed": closed_count,
        "overdue_open": overdue_open,
        "escalated_open": escalated_open,
        "escalation_recommended_open": escalation_recommended_open,
        "received_last_7_days": received_last_7_days,
        "institutions_with_open_cases": institutions_with_open,
        "institutions_with_multi_bureau_open_cases": institutions_with_multi_bureau_open,
        "confirmed_relations": confirmed_relations,
        "pending_relation_reviews": pending_relation_reviews,
        "unassigned_owner_open": unassigned_owner_open,
    }


def get_status_distribution(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    bureau_id: UUID | None = None,
    institution_id: UUID | None = None,
    category: str | None = None,
    priority: str | None = None,
) -> dict[str, int]:
    """GET /analytics/status-distribution (zero-filled for all 7 statuses)"""
    query = db.query(Complaint.status, func.count(Complaint.id)).group_by(Complaint.status)

    if date_from:
        query = query.filter(Complaint.received_date >= date_from)
    if date_to:
        query = query.filter(Complaint.received_date <= date_to)
    if bureau_id:
        query = query.filter(Complaint.primary_bureau_id == bureau_id)
    if institution_id:
        query = query.filter(Complaint.institution_id == institution_id)
    if category:
        query = query.filter(Complaint.category == category)
    if priority:
        query = query.filter(Complaint.priority == priority)

    counts = dict(query.all())
    # Zero fill all 7
    return {status: counts.get(status, 0) for status in ALL_STATUSES}


def get_bureau_workload(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict[str, Any]]:
    """GET /analytics/bureau-workload"""
    today = datetime.now(timezone.utc).date()
    bureaus = db.query(Bureau).filter(Bureau.is_active.is_(True)).all()
    results = []

    for b in bureaus:
        base = db.query(Complaint)
        if date_from:
            base = base.filter(Complaint.received_date >= date_from)
        if date_to:
            base = base.filter(Complaint.received_date <= date_to)

        open_primary = base.filter(
            Complaint.primary_bureau_id == b.id,
            Complaint.status.in_(OPEN_STATUSES),
        ).count()

        open_part = base.filter(
            Complaint.primary_bureau_id != b.id,
            Complaint.status.in_(OPEN_STATUSES),
            Complaint.participating_bureau_codes.any(b.code),
        ).count()

        overdue_primary = base.filter(
            Complaint.primary_bureau_id == b.id,
            Complaint.status.in_(OPEN_STATUSES),
            Complaint.target_date < today,
        ).count()

        resolved = base.filter(
            Complaint.primary_bureau_id == b.id,
            Complaint.status == "RESOLVED",
        ).count()

        # Avg open age in days
        open_cases = base.filter(
            Complaint.primary_bureau_id == b.id,
            Complaint.status.in_(OPEN_STATUSES),
        ).all()

        if open_cases:
            total_days = sum((today - c.received_date).days for c in open_cases if c.received_date)
            avg_age = round(total_days / len(open_cases), 1)
        else:
            avg_age = 0.0

        results.append({
            "bureau_id": b.id,
            "bureau_code": b.code,
            "bureau_name": b.name,
            "open_as_primary": open_primary,
            "open_as_participating": open_part,
            "overdue_as_primary": overdue_primary,
            "resolved_in_range": resolved,
            "avg_open_age_days": avg_age,
        })

    return results


def get_aging_distribution(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    bureau_id: UUID | None = None,
) -> dict[str, int]:
    """GET /analytics/aging (buckets: 0-7, 8-15, 16-30, 31-60, 61+)"""
    today = datetime.now(timezone.utc).date()
    query = db.query(Complaint).filter(Complaint.status.in_(OPEN_STATUSES))

    if date_from:
        query = query.filter(Complaint.received_date >= date_from)
    if date_to:
        query = query.filter(Complaint.received_date <= date_to)
    if bureau_id:
        query = query.filter(Complaint.primary_bureau_id == bureau_id)

    complaints = query.all()
    buckets = {
        "0-7": 0,
        "8-15": 0,
        "16-30": 0,
        "31-60": 0,
        "61+": 0,
    }

    for c in complaints:
        if not c.received_date:
            continue
        age = (today - c.received_date).days
        if age <= 7:
            buckets["0-7"] += 1
        elif age <= 15:
            buckets["8-15"] += 1
        elif age <= 30:
            buckets["16-30"] += 1
        elif age <= 60:
            buckets["31-60"] += 1
        else:
            buckets["61+"] += 1

    return buckets


def get_trend(
    db: Session,
    granularity: str = "day",
    months: int = 12,
    days: int = 30,
) -> list[dict[str, Any]]:
    """GET /analytics/trend"""
    today = datetime.now(timezone.utc).date()
    results = []

    if days and days > 0:
        for i in range(days - 1, -1, -1):
            d = today - timedelta(days=i)
            d_str = d.isoformat()
            rec_count = db.query(func.count(Complaint.id)).filter(Complaint.received_date == d).scalar() or 0
            res_count = db.query(func.count(Complaint.id)).filter(
                Complaint.resolved_at.isnot(None),
                func.date(Complaint.resolved_at) == d,
            ).scalar() or 0
            results.append({
                "period": d_str,
                "date": d_str,
                "received": rec_count,
                "registered": rec_count,
                "resolved": res_count,
            })
        return results

    for i in range(months - 1, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        month_str = f"{year:04d}-{month:02d}"
        rec_count = (
            db.query(func.count(Complaint.id))
            .filter(func.to_char(Complaint.received_date, "YYYY-MM") == month_str)
            .scalar()
            or 0
        )
        res_count = (
            db.query(func.count(Complaint.id))
            .filter(
                Complaint.resolved_at.isnot(None),
                func.to_char(Complaint.resolved_at, "YYYY-MM") == month_str,
            )
            .scalar()
            or 0
        )
        results.append({
            "period": month_str,
            "date": month_str,
            "received": rec_count,
            "registered": rec_count,
            "resolved": res_count,
        })
    return results


def get_top_institutions(
    db: Session,
    limit: int = 10,
    metric: str = "open",
) -> list[dict[str, Any]]:
    """GET /analytics/top-institutions?limit=10&metric=open|overdue"""
    today = datetime.now(timezone.utc).date()

    if metric == "overdue":
        query = (
            db.query(
                Institution.id,
                Institution.code,
                Institution.name,
                Institution.state,
                func.count(Complaint.id).label("metric_count"),
            )
            .join(Complaint, Complaint.institution_id == Institution.id)
            .filter(
                Complaint.status.in_(OPEN_STATUSES),
                Complaint.target_date < today,
            )
            .group_by(Institution.id, Institution.code, Institution.name, Institution.state)
            .order_by(func.count(Complaint.id).desc())
            .limit(limit)
        )
    else:
        query = (
            db.query(
                Institution.id,
                Institution.code,
                Institution.name,
                Institution.state,
                func.count(Complaint.id).label("metric_count"),
            )
            .join(Complaint, Complaint.institution_id == Institution.id)
            .filter(Complaint.status.in_(OPEN_STATUSES))
            .group_by(Institution.id, Institution.code, Institution.name, Institution.state)
            .order_by(func.count(Complaint.id).desc())
            .limit(limit)
        )

    rows = query.all()
    return [
        {
            "id": str(r.id),
            "institution_id": str(r.id),
            "code": r.code,
            "aicte_id": r.code,
            "name": r.name,
            "institution_name": r.name,
            "state": r.state,
            "count": r.metric_count,
            "active_count": r.metric_count,
        }
        for r in rows
    ]
