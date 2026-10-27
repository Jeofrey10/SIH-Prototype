"""Analytics router."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.services import analytics as analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def get_summary(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    bureau_id: UUID | None = Query(None),
    institution_id: UUID | None = Query(None),
    category: str | None = Query(None),
    priority: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregate dashboard summary numbers."""
    return analytics_service.get_analytics_summary(
        db,
        date_from=date_from,
        date_to=date_to,
        bureau_id=bureau_id,
        institution_id=institution_id,
        category=category,
        priority=priority,
    )


@router.get("/status-distribution")
def get_status_distribution(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    bureau_id: UUID | None = Query(None),
    institution_id: UUID | None = Query(None),
    category: str | None = Query(None),
    priority: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Zero-filled counts across all 7 statuses."""
    return analytics_service.get_status_distribution(
        db,
        date_from=date_from,
        date_to=date_to,
        bureau_id=bureau_id,
        institution_id=institution_id,
        category=category,
        priority=priority,
    )


@router.get("/bureau-workload")
def get_bureau_workload(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bureau breakdown of workload and resolution metrics."""
    return analytics_service.get_bureau_workload(
        db, date_from=date_from, date_to=date_to
    )


@router.get("/aging-buckets")
@router.get("/aging")
def get_aging(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    bureau_id: UUID | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aging distribution buckets."""
    buckets = analytics_service.get_aging_distribution(
        db, date_from=date_from, date_to=date_to, bureau_id=bureau_id
    )
    return [
        {"bucket": f"{k}d" if not k.endswith("d") else k, "count": v}
        for k, v in buckets.items()
    ]


@router.get("/trend")
def get_trend(
    granularity: str = Query("day"),
    months: int = Query(12, ge=1, le=24),
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Received vs resolved complaint trend."""
    return analytics_service.get_trend(db, granularity=granularity, months=months, days=days)


@router.get("/top-institutions")
def get_top_institutions(
    limit: int = Query(10, ge=1, le=50),
    metric: str = Query("open"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Top institutions by open or overdue complaint count."""
    return analytics_service.get_top_institutions(db, limit=limit, metric=metric)


@router.get("/limbo-summary")
def get_limbo_summary_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Scan all open cases and summarize silently stuck and ping-pong complaints."""
    from app.services.limbo_detector import get_limbo_summary
    return get_limbo_summary(db)
