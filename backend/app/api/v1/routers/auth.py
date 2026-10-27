"""Authentication router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas import ChangePasswordRequest, LoginRequest, LoginResponse, UserResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    req: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticate with email and password."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    token, user, expires_in = auth_service.login(
        db,
        email=req.email,
        password=req.password,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": user,
    }


@router.post("/logout")
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Log out current user."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    auth_service.logout(
        db,
        user=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get profile of current authenticated user."""
    return current_user


@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change current user's password."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    auth_service.change_password(
        db,
        user=current_user,
        current_password=req.current_password,
        new_password=req.new_password,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return {"message": "Password changed successfully"}
