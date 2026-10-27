"""Bureaus router."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import Bureau, User
from app.schemas import BureauDetailResponse

router = APIRouter(prefix="/bureaus", tags=["bureaus"])


@router.get("", response_model=list[BureauDetailResponse])
def list_bureaus(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all bureaus."""
    return db.query(Bureau).order_by(Bureau.code.asc()).all()
