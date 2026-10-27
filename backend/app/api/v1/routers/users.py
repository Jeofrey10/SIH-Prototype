"""User management router."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.models import User
from app.schemas import (
    AssignableUserResponse,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.services import users as user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/assignable", response_model=list[AssignableUserResponse])
def get_assignable_users(
    bureau_id: UUID | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List assignable users for a bureau."""
    target_bureau = bureau_id or current_user.bureau_id
    users = user_service.get_assignable_users(db, bureau_id=target_bureau)
    return users


@router.get("", response_model=dict)
def list_users(
    role: str | None = Query(None),
    bureau_id: UUID | None = Query(None),
    is_active: bool | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles("SYSTEM_ADMIN")),
    db: Session = Depends(get_db),
):
    """List users with filters (Admin only)."""
    items, total = user_service.list_users(
        db,
        role=role,
        bureau_id=bureau_id,
        is_active=is_active,
        q=q,
        page=page,
        page_size=page_size,
    )
    return {
        "items": [UserResponse.model_validate(u) for u in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", response_model=UserResponse, status_code=201)
def create_user(
    req: UserCreateRequest,
    request: Request,
    current_user: User = Depends(require_roles("SYSTEM_ADMIN")),
    db: Session = Depends(get_db),
):
    """Create a new user (Admin only)."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    user = user_service.create_user(
        db,
        data=req.model_dump(),
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    current_user: User = Depends(require_roles("SYSTEM_ADMIN")),
    db: Session = Depends(get_db),
):
    """Get user by ID (Admin only)."""
    return user_service.get_user_by_id(db, user_id)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    req: UserUpdateRequest,
    request: Request,
    current_user: User = Depends(require_roles("SYSTEM_ADMIN")),
    db: Session = Depends(get_db),
):
    """Update user (Admin only)."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    user = user_service.update_user(
        db,
        user_id=user_id,
        data=req.model_dump(exclude_unset=True),
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return user


@router.post("/{user_id}/activate", response_model=UserResponse)
def activate_user(
    user_id: UUID,
    request: Request,
    current_user: User = Depends(require_roles("SYSTEM_ADMIN")),
    db: Session = Depends(get_db),
):
    """Activate user (Admin only)."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    user = user_service.activate_user(
        db,
        user_id=user_id,
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return user


@router.post("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: UUID,
    request: Request,
    current_user: User = Depends(require_roles("SYSTEM_ADMIN")),
    db: Session = Depends(get_db),
):
    """Deactivate user (Admin only)."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    user = user_service.deactivate_user(
        db,
        user_id=user_id,
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return user


@router.post("/{user_id}/reset-password")
def reset_password(
    user_id: UUID,
    request: Request,
    current_user: User = Depends(require_roles("SYSTEM_ADMIN")),
    db: Session = Depends(get_db),
):
    """Reset user password to a random string (Admin only)."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    temp_password = user_service.reset_user_password(
        db,
        user_id=user_id,
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return {"temporary_password": temp_password}
