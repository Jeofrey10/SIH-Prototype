"""System health and maintenance jobs router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.jobs.overdue_scan import run_overdue_scan
from app.models import User

router = APIRouter(tags=["system"])


@router.get("/health")
def health_check():
    """Liveness probe (no auth required)."""
    return {"status": "ok"}


@router.get("/health/ready")
def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe checking DB connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as exc:
        return {"status": "not_ready", "error": str(exc)}


@router.post("/system/jobs/overdue-scan")
def trigger_overdue_scan(
    request: Request,
    current_user: User = Depends(require_roles("SYSTEM_ADMIN", "SUPERVISOR")),
    db: Session = Depends(get_db),
):
    """Trigger manual overdue complaints scan (Admin or Supervisor only)."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    result = run_overdue_scan(
        db,
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return result
