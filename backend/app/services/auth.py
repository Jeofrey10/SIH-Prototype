"""Authentication service."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.core import errors
from app.models import User
from app.services.audit import write_audit, write_denied_audit

logger = logging.getLogger(__name__)

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def authenticate(db: Session, email: str, password: str, ip_address: str | None = None) -> dict:
    """Authenticate a user and return token + user data."""
    email = email.strip().lower()

    user = db.query(User).filter(func.lower(User.email) == email).first()

    if user is None:
        write_denied_audit(
            db,
            actor_email=email,
            action="AUTH_LOGIN_FAILED",
            entity_type="AUTH",
            details={"reason": "user_not_found"},
            ip_address=ip_address,
        )
        raise errors.invalid_credentials()

    # Check lockout
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        write_denied_audit(
            db,
            actor_user_id=user.id,
            actor_email=user.email,
            actor_role=user.role,
            action="AUTH_LOGIN_FAILED",
            entity_type="AUTH",
            details={"reason": "account_locked"},
            ip_address=ip_address,
        )
        raise errors.account_locked()

    if not user.is_active:
        write_denied_audit(
            db,
            actor_user_id=user.id,
            actor_email=user.email,
            actor_role=user.role,
            action="AUTH_LOGIN_FAILED",
            entity_type="AUTH",
            details={"reason": "account_deactivated"},
            ip_address=ip_address,
        )
        raise errors.invalid_credentials()

    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
        db.flush()

        write_denied_audit(
            db,
            actor_user_id=user.id,
            actor_email=user.email,
            actor_role=user.role,
            action="AUTH_LOGIN_FAILED",
            entity_type="AUTH",
            details={"reason": "invalid_password", "failed_count": user.failed_login_count},
            ip_address=ip_address,
        )
        raise errors.invalid_credentials()

    # Successful login
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    db.flush()

    token, expires_in = create_access_token(user.id, user.role)

    write_audit(
        db,
        actor_user_id=user.id,
        actor_email=user.email,
        actor_role=user.role,
        action="AUTH_LOGIN_SUCCESS",
        entity_type="AUTH",
        entity_id=str(user.id),
        ip_address=ip_address,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": user,
    }


def login(
    db: Session,
    email: str,
    password: str,
    ip: str | None = None,
    ip_address: str | None = None,
    request_id: str | None = None,
) -> tuple[str, User, int]:
    """Authenticate user and return (token, user, expires_in) tuple."""
    client_ip = ip or ip_address
    result = authenticate(db, email=email, password=password, ip_address=client_ip)
    return result["access_token"], result["user"], result["expires_in"]


def logout(
    db: Session,
    user: User,
    ip: str | None = None,
    ip_address: str | None = None,
    request_id: str | None = None,
) -> None:
    """Log out a user and record audit log."""
    client_ip = ip or ip_address
    write_audit(
        db,
        actor_user_id=user.id,
        actor_email=user.email,
        actor_role=user.role,
        action="AUTH_LOGOUT",
        entity_type="AUTH",
        entity_id=str(user.id),
        ip_address=client_ip,
        request_id=request_id,
    )


def get_current_user(db: Session, token: str) -> User:
    """Decode token and load user; reject deactivated users."""
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise errors.unauthenticated()

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise errors.unauthenticated("User account is deactivated or not found")

    return user


def change_password(
    db: Session, user: User, current_password: str, new_password: str,
    ip_address: str | None = None, request_id: str | None = None,
) -> None:
    """Change a user's password."""
    if not verify_password(current_password, user.password_hash):
        raise errors.AppError(400, "INVALID_CREDENTIALS", "Current password is incorrect")

    if len(new_password) < 10:
        raise errors.validation_error({"new_password": "Password must be at least 10 characters"})

    user.password_hash = hash_password(new_password)
    db.flush()

    write_audit(
        db,
        actor_user_id=user.id,
        actor_email=user.email,
        actor_role=user.role,
        action="AUTH_PASSWORD_CHANGED",
        entity_type="USER",
        entity_id=str(user.id),
        ip_address=ip_address,
        request_id=request_id,
    )
