"""Institutions router."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.models import User
from app.schemas import (
    CoordinationResponse,
    InstitutionCreateRequest,
    InstitutionDetailResponse,
    InstitutionResponse,
    InstitutionUpdateRequest,
)
from app.services import institutions as inst_service

router = APIRouter(prefix="/institutions", tags=["institutions"])


@router.get("", response_model=dict)
def list_institutions(
    q: str | None = Query(None),
    state: str | None = Query(None),
    institution_type: str | None = Query(None),
    is_active: bool | None = Query(None),
    has_open_cases: bool | None = Query(None),
    has_overdue_cases: bool | None = Query(None),
    multi_bureau_open: bool | None = Query(None),
    sort_by: str = Query("name"),
    order: str = Query("asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List institutions with filters and KPIs."""
    filters = {
        "q": q,
        "state": state,
        "institution_type": institution_type,
        "is_active": is_active,
        "has_open_cases": has_open_cases,
        "has_overdue_cases": has_overdue_cases,
        "multi_bureau_open": multi_bureau_open,
        "sort_by": sort_by,
        "order": order,
        "page": page,
        "page_size": page_size,
    }
    items, total = inst_service.list_institutions(db, filters)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", response_model=InstitutionResponse, status_code=201)
def create_institution(
    req: InstitutionCreateRequest,
    request: Request,
    current_user: User = Depends(require_roles("SYSTEM_ADMIN", "SUPERVISOR")),
    db: Session = Depends(get_db),
):
    """Register new institution."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    inst = inst_service.create_institution(
        db,
        data=req.model_dump(),
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return inst_service.get_institution_detail(db, inst.id)


@router.get("/{institution_id}", response_model=InstitutionDetailResponse)
def get_institution(
    institution_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full profile and KPIs of an institution."""
    return inst_service.get_institution_detail(db, institution_id)


@router.patch("/{institution_id}", response_model=InstitutionDetailResponse)
def update_institution(
    institution_id: UUID,
    req: InstitutionUpdateRequest,
    request: Request,
    current_user: User = Depends(require_roles("SYSTEM_ADMIN", "SUPERVISOR")),
    db: Session = Depends(get_db),
):
    """Update institution details."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    inst = inst_service.update_institution(
        db,
        inst_id=institution_id,
        data=req.model_dump(exclude_unset=True),
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return inst_service.get_institution_detail(db, inst.id)


@router.post("/{institution_id}/deactivate")
def deactivate_institution(
    institution_id: UUID,
    request: Request,
    current_user: User = Depends(require_roles("SYSTEM_ADMIN", "SUPERVISOR")),
    db: Session = Depends(get_db),
):
    """Deactivate institution."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    inst = inst_service.deactivate_institution(
        db,
        inst_id=institution_id,
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return {"message": "Institution deactivated successfully"}


@router.post("/{institution_id}/activate")
def activate_institution(
    institution_id: UUID,
    request: Request,
    current_user: User = Depends(require_roles("SYSTEM_ADMIN", "SUPERVISOR")),
    db: Session = Depends(get_db),
):
    """Activate institution."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    inst = inst_service.activate_institution(
        db,
        inst_id=institution_id,
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return {"message": "Institution activated successfully"}


@router.get("/{institution_id}/coordination", response_model=CoordinationResponse)
def get_institution_coordination(
    institution_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get multi-bureau coordination summary for an institution."""
    return inst_service.get_coordination(db, institution_id, user=current_user)


@router.get("/{institution_id}/timeline")
def get_institution_timeline(
    institution_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Consolidated chronological audit and complaint events for an institution."""
    events, total = inst_service.get_timeline(
        db, institution_id, user=current_user, page=page, page_size=page_size
    )
    return {
        "items": events,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
