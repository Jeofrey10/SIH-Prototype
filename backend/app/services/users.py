"""User management service."""
from __future__ import annotations

import secrets
import string
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import errors, permissions
from app.core.security import hash_password
from app.models import Bureau, Complaint, User
from app.services.audit import write_audit


def create_user(db: Session, data: dict, actor: User, ip: str | None = None, request_id: str | None = None) -> User:
    """Create a new user."""
    email = data["email"].strip().lower()

    # Check uniqueness
    existing = db.query(User).filter(func.lower(User.email) == email).first()
    if existing:
        raise errors.conflict(f"User with email {email} already exists")

    role = data["role"]
    if role not in permissions.ALL_ROLES:
        raise errors.validation_error({"role": f"Invalid role: {role}"})

    bureau_id = data.get("bureau_id")
    # Validate role-bureau consistency
    if role in permissions.OFFICIAL_ROLES:
        if not bureau_id:
            raise errors.validation_error({"bureau_id": "Bureau is required for officials"})
        bureau = db.query(Bureau).filter(Bureau.id == bureau_id).first()
        if not bureau:
            raise errors.not_found("Bureau")
        # RB_OFFICIAL must be in RB bureau, PGRC_OFFICIAL in PGRC
        if role == "RB_OFFICIAL" and bureau.code != "RB":
            raise errors.validation_error({"bureau_id": "RB_OFFICIAL must belong to RB bureau"})
        if role == "PGRC_OFFICIAL" and bureau.code != "PGRC":
            raise errors.validation_error({"bureau_id": "PGRC_OFFICIAL must belong to PGRC bureau"})
    elif role in permissions.MANAGEMENT_ROLES:
        bureau_id = None  # Force null for admin/supervisor

    user = User(
        email=email,
        full_name=data["full_name"].strip(),
        password_hash=hash_password(data["password"]),
        role=role,
        bureau_id=bureau_id,
        designation=data.get("designation"),
        is_active=True,
    )
    db.add(user)
    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="USER_CREATED",
        entity_type="USER",
        entity_id=str(user.id),
        after_data={"email": user.email, "role": user.role, "full_name": user.full_name},
        ip_address=ip,
        request_id=request_id,
    )

    return user


def update_user(db: Session, user_id: UUID, data: dict, actor: User, ip: str | None = None, request_id: str | None = None) -> User:
    """Update user fields."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise errors.not_found("User")

    before = {"full_name": user.full_name, "role": user.role, "designation": user.designation}

    if "full_name" in data and data["full_name"]:
        user.full_name = data["full_name"].strip()
    if "designation" in data:
        user.designation = data.get("designation")
    if "role" in data and data["role"]:
        role = data["role"]
        if role not in permissions.ALL_ROLES:
            raise errors.validation_error({"role": f"Invalid role: {role}"})
        user.role = role
    if "bureau_id" in data:
        user.bureau_id = data.get("bureau_id")

    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="USER_UPDATED",
        entity_type="USER",
        entity_id=str(user.id),
        before_data=before,
        after_data={"full_name": user.full_name, "role": user.role, "designation": user.designation},
        ip_address=ip,
        request_id=request_id,
    )
    return user


def deactivate_user(db: Session, user_id: UUID, actor: User, ip: str | None = None, request_id: str | None = None) -> User:
    """Deactivate a user. Clears owner from open complaints."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise errors.not_found("User")
    if not user.is_active:
        raise errors.conflict("User is already deactivated")

    user.is_active = False
    db.flush()

    # Clear owner on open complaints
    open_complaints = db.query(Complaint).filter(
        Complaint.owner_user_id == user_id,
        Complaint.status.notin_(list(permissions.TERMINAL_STATUSES)),
    ).all()

    for c in open_complaints:
        c.owner_user_id = None
        write_audit(
            db,
            actor_user_id=actor.id,
            actor_email=actor.email,
            actor_role=actor.role,
            action="ASSIGNMENT_OWNER_CHANGED",
            entity_type="COMPLAINT",
            entity_id=str(c.id),
            complaint_id=c.id,
            before_data={"owner_user_id": str(user_id)},
            after_data={"owner_user_id": None},
            details={"reason": f"User {user.email} deactivated"},
            ip_address=ip,
            request_id=request_id,
        )

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="USER_DEACTIVATED",
        entity_type="USER",
        entity_id=str(user.id),
        details={"affected_complaints": len(open_complaints)},
        ip_address=ip,
        request_id=request_id,
    )

    return user


def activate_user(db: Session, user_id: UUID, actor: User, ip: str | None = None, request_id: str | None = None) -> User:
    """Reactivate a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise errors.not_found("User")
    if user.is_active:
        raise errors.conflict("User is already active")

    user.is_active = True
    user.failed_login_count = 0
    user.locked_until = None
    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="USER_ACTIVATED",
        entity_type="USER",
        entity_id=str(user.id),
        ip_address=ip,
        request_id=request_id,
    )

    return user


def reset_password(db: Session, user_id: UUID, actor: User, ip: str | None = None, request_id: str | None = None) -> str:
    """Reset a user's password to a random temporary one."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise errors.not_found("User")

    temp_password = "Temp" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10)) + "!"
    user.password_hash = hash_password(temp_password)
    user.failed_login_count = 0
    user.locked_until = None
    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="USER_PASSWORD_RESET",
        entity_type="USER",
        entity_id=str(user.id),
        ip_address=ip,
        request_id=request_id,
    )

    return temp_password


def list_users(db: Session, filters: dict) -> tuple[list[User], int]:
    """List users with filters."""
    query = db.query(User)

    if "role" in filters and filters["role"]:
        query = query.filter(User.role == filters["role"])
    if "bureau_id" in filters and filters["bureau_id"]:
        query = query.filter(User.bureau_id == filters["bureau_id"])
    if "active" in filters and filters["active"] is not None:
        query = query.filter(User.is_active == filters["active"])
    if "q" in filters and filters["q"]:
        q = f"%{filters['q']}%"
        query = query.filter(
            (User.full_name.ilike(q)) | (User.email.ilike(q))
        )

    total = query.count()
    page = filters.get("page", 1)
    page_size = min(filters.get("page_size", 20), 100)
    query = query.order_by(User.full_name).offset((page - 1) * page_size).limit(page_size)

    return query.all(), total


def get_assignable_users(db: Session, bureau_id: UUID) -> list[User]:
    """Get active users in a bureau who can be assigned as owner."""
    return db.query(User).filter(
        User.bureau_id == bureau_id,
        User.is_active == True,
    ).order_by(User.full_name).all()
