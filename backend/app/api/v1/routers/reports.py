"""Reports router."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.services import reports as report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/overdue")
def get_overdue_report(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    bureau_id: UUID | None = Query(None),
    institution_id: UUID | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Overdue complaints report."""
    return report_service.get_overdue_report(
        db,
        actor=current_user,
        date_from=date_from,
        date_to=date_to,
        bureau_id=bureau_id,
        institution_id=institution_id,
    )


@router.get("/overdue/export.csv")
def export_overdue_csv(
    request: Request,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    bureau_id: UUID | None = Query(None),
    institution_id: UUID | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export overdue complaints as CSV."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    filters = {
        "date_from": date_from,
        "date_to": date_to,
        "bureau_id": bureau_id,
        "institution_id": institution_id,
    }
    csv_content, filename = report_service.export_overdue_csv(
        db,
        actor=current_user,
        filters=filters,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv; charset=utf-8",
        },
    )


@router.get("/complaints")
def get_complaints_report(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    bureau_id: UUID | None = Query(None),
    institution_id: UUID | None = Query(None),
    status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Complaints list report."""
    filters = {
        "date_from": date_from,
        "date_to": date_to,
        "bureau_id": bureau_id,
        "institution_id": institution_id,
        "status": status,
    }
    return report_service.get_complaints_report(db, current_user, filters)


@router.get("/complaints/export.csv")
def export_complaints_csv(
    request: Request,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    bureau_id: UUID | None = Query(None),
    institution_id: UUID | None = Query(None),
    status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export complaints report as CSV."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    filters = {
        "date_from": date_from,
        "date_to": date_to,
        "bureau_id": bureau_id,
        "institution_id": institution_id,
        "status": status,
    }
    csv_content, filename = report_service.export_complaints_csv(
        db,
        actor=current_user,
        filters=filters,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv; charset=utf-8",
        },
    )
