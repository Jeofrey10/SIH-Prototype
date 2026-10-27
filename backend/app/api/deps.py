"""FastAPI route dependencies."""
from __future__ import annotations

from typing import Generator
from uuid import UUID

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import errors, security
from app.db.session import SessionLocal
from app.models import User
from app.services.audit import write_audit

security_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate Bearer JWT and return current user."""
    if not credentials or not credentials.credentials:
        raise errors.unauthorized("Authentication required")

    try:
        payload = security.decode_token(credentials.credentials)
    except Exception:
        raise errors.unauthorized("Invalid or expired authentication token")
    if not payload:
        raise errors.unauthorized("Invalid or expired authentication token")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise errors.unauthorized("Malformed authentication token")

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise errors.unauthorized("Malformed user ID in token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise errors.unauthorized("User not found")

    if not user.is_active:
        # A deactivated user's valid token -> 401 Unauthorized
        raise errors.unauthorized("Account has been deactivated")

    # Store user on request state
    request.state.user = user
    return user


def require_roles(*allowed_roles: str):
    """Dependency factory checking that current user has one of allowed roles."""
    def _role_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if current_user.role not in allowed_roles:
            request_id = getattr(request.state, "request_id", None)
            client_ip = request.client.host if request.client else None

            # Audit ACCESS_DENIED
            write_audit(
                db,
                actor_user_id=current_user.id,
                actor_email=current_user.email,
                actor_role=current_user.role,
                action="ACCESS_DENIED",
                entity_type="SYSTEM",
                entity_id="ENDPOINT",
                outcome="DENIED",
                before_state={"allowed_roles": list(allowed_roles), "path": request.url.path},
                ip=client_ip,
                request_id=request_id,
            )
            db.commit()

            raise errors.forbidden("You do not have permission to perform this action")
        return current_user

    return _role_checker
