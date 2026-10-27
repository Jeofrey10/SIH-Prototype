"""Relations review router."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas import (
    RelationConfirmRequest,
    RelationDismissRequest,
    RelationRevertRequest,
)
from app.services.relations import service as relation_service

router = APIRouter(prefix="/relations", tags=["relations"])


@router.get("", response_model=dict)
def list_relations(
    status: str | None = Query(None),
    institution_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Review queue of duplicate/related complaint pairs."""
    items, total = relation_service.list_relations(
        db,
        status=status,
        institution_id=institution_id,
        actor=current_user,
        page=page,
        page_size=page_size,
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/{relation_id}/confirm")
def confirm_relation(
    relation_id: UUID,
    req: RelationConfirmRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirm a suggested relation as SAME_ISSUE or RELATED_ISSUE."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    rel = relation_service.confirm_relation(
        db,
        relation_id=relation_id,
        data=req.model_dump(),
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return {
        "id": rel.id,
        "status": rel.status,
        "relation_type": rel.relation_type,
        "reviewed_by": rel.reviewed_by,
        "reviewed_at": rel.reviewed_at,
        "review_note": rel.review_note,
    }


@router.post("/{relation_id}/dismiss")
def dismiss_relation(
    relation_id: UUID,
    req: RelationDismissRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dismiss a suggested relation."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    rel = relation_service.dismiss_relation(
        db,
        relation_id=relation_id,
        data=req.model_dump(),
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return {
        "id": rel.id,
        "status": rel.status,
        "reviewed_by": rel.reviewed_by,
        "reviewed_at": rel.reviewed_at,
        "review_note": rel.review_note,
    }


@router.post("/{relation_id}/revert")
def revert_relation(
    relation_id: UUID,
    req: RelationRevertRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revert a reviewed relation (Supervisor only)."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    rel = relation_service.revert_relation(
        db,
        relation_id=relation_id,
        data=req.model_dump(),
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return {
        "id": rel.id,
        "status": rel.status,
        "reviewed_by": rel.reviewed_by,
        "reviewed_at": rel.reviewed_at,
        "review_note": rel.review_note,
    }
