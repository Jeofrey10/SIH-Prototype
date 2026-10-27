"""Institution management service."""
from __future__ import annotations

import unicodedata
from uuid import UUID

from sqlalchemy import and_, case, distinct, func, literal_column, or_
from sqlalchemy.orm import Session

from app.core import errors, permissions
from app.models import (
    Bureau, CaseAssignment, Complaint, ComplaintRelation,
    Institution, StatusHistory, ComplaintNote, User
)
from app.services.audit import write_audit


def _normalize_name(name: str) -> str:
    """Normalize institution name for search."""
    name = unicodedata.normalize("NFKC", name)
    return name.strip().lower()


def create_institution(
    db: Session, data: dict, actor: User,
    ip: str | None = None, request_id: str | None = None,
) -> Institution:
    """Create a new institution."""
    code = data["code"].strip()
    name = data["name"].strip()

    existing = db.query(Institution).filter(Institution.code == code).first()
    if existing:
        raise errors.conflict(f"Institution with code {code} already exists")

    valid_types = {"ENGINEERING", "MANAGEMENT", "PHARMACY", "ARCHITECTURE", "POLYTECHNIC", "OTHER"}
    if data["institution_type"] not in valid_types:
        raise errors.validation_error({"institution_type": "Invalid institution type"})

    inst = Institution(
        code=code,
        name=name,
        name_normalized=_normalize_name(name),
        institution_type=data["institution_type"],
        state=data["state"].strip(),
        district=data.get("district"),
        city=data.get("city"),
        address=data.get("address"),
        email=data.get("email"),
        phone=data.get("phone"),
        is_active=True,
    )
    db.add(inst)
    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="INSTITUTION_CREATED",
        entity_type="INSTITUTION",
        entity_id=str(inst.id),
        institution_id=inst.id,
        after_data={"code": inst.code, "name": inst.name, "type": inst.institution_type, "state": inst.state},
        ip_address=ip,
        request_id=request_id,
    )

    return inst


def update_institution(
    db: Session, inst_id: UUID, data: dict, actor: User,
    ip: str | None = None, request_id: str | None = None,
) -> Institution:
    """Update institution fields."""
    inst = db.query(Institution).filter(Institution.id == inst_id).first()
    if not inst:
        raise errors.not_found("Institution")

    before = {"name": inst.name, "institution_type": inst.institution_type, "state": inst.state}

    if "name" in data and data["name"]:
        inst.name = data["name"].strip()
        inst.name_normalized = _normalize_name(inst.name)
    if "institution_type" in data and data["institution_type"]:
        inst.institution_type = data["institution_type"]
    if "state" in data and data["state"]:
        inst.state = data["state"].strip()
    for field in ("district", "city", "address", "email", "phone"):
        if field in data:
            setattr(inst, field, data[field])

    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="INSTITUTION_UPDATED",
        entity_type="INSTITUTION",
        entity_id=str(inst.id),
        institution_id=inst.id,
        before_data=before,
        after_data={"name": inst.name, "institution_type": inst.institution_type, "state": inst.state},
        ip_address=ip,
        request_id=request_id,
    )

    return inst


def deactivate_institution(
    db: Session, inst_id: UUID, actor: User,
    ip: str | None = None, request_id: str | None = None,
) -> Institution:
    """Deactivate an institution."""
    inst = db.query(Institution).filter(Institution.id == inst_id).first()
    if not inst:
        raise errors.not_found("Institution")
    if not inst.is_active:
        raise errors.conflict("Institution is already inactive")

    inst.is_active = False
    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="INSTITUTION_DEACTIVATED",
        entity_type="INSTITUTION",
        entity_id=str(inst.id),
        institution_id=inst.id,
        ip_address=ip,
        request_id=request_id,
    )

    return inst


def activate_institution(
    db: Session, inst_id: UUID, actor: User,
    ip: str | None = None, request_id: str | None = None,
) -> Institution:
    """Reactivate an institution."""
    inst = db.query(Institution).filter(Institution.id == inst_id).first()
    if not inst:
        raise errors.not_found("Institution")
    if inst.is_active:
        raise errors.conflict("Institution is already active")

    inst.is_active = True
    db.flush()

    write_audit(
        db,
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="INSTITUTION_ACTIVATED",
        entity_type="INSTITUTION",
        entity_id=str(inst.id),
        institution_id=inst.id,
        ip_address=ip,
        request_id=request_id,
    )

    return inst


def get_institution(db: Session, inst_id: UUID) -> Institution:
    """Get institution by ID."""
    inst = db.query(Institution).filter(Institution.id == inst_id).first()
    if not inst:
        raise errors.not_found("Institution")
    return inst


def get_institution_detail(db: Session, inst_id: UUID, today=None) -> dict:
    """Get institution with KPI summary."""
    from app.core.clock import get_clock
    inst = get_institution(db, inst_id)
    if today is None:
        today = get_clock().today_local()

    complaints = db.query(Complaint).filter(Complaint.institution_id == inst_id).all()

    total = len(complaints)
    open_count = sum(1 for c in complaints if permissions.is_open(c.status))
    overdue_count = sum(
        1 for c in complaints
        if permissions.is_open(c.status) and c.target_date < today
    )
    resolved_count = sum(1 for c in complaints if c.status == "RESOLVED")

    bureaus_involved = set()
    for c in complaints:
        assignments = db.query(CaseAssignment).filter(
            CaseAssignment.complaint_id == c.id,
            CaseAssignment.is_active == True,
        ).all()
        for a in assignments:
            bureau = db.query(Bureau).filter(Bureau.id == a.bureau_id).first()
            if bureau:
                bureaus_involved.add(bureau.code)

    pending_reviews = db.query(ComplaintRelation).filter(
        ComplaintRelation.status == "SUGGESTED",
        or_(
            ComplaintRelation.complaint_a_id.in_([c.id for c in complaints]),
            ComplaintRelation.complaint_b_id.in_([c.id for c in complaints]),
        ),
    ).count() if complaints else 0

    return {
        "institution": inst,
        "total_complaints": total,
        "open_count": open_count,
        "overdue_count": overdue_count,
        "resolved_count": resolved_count,
        "bureaus_involved": sorted(bureaus_involved),
        "pending_relation_reviews": pending_reviews,
    }


def list_institutions(db: Session, filters: dict, today=None) -> tuple[list[dict], int]:
    """List institutions with filters and aggregated counts."""
    from app.core.clock import get_clock
    if today is None:
        today = get_clock().today_local()

    query = db.query(Institution)

    if "q" in filters and filters["q"]:
        q = f"%{filters['q']}%"
        query = query.filter(
            or_(Institution.name.ilike(q), Institution.code.ilike(q))
        )
    if "state" in filters and filters["state"]:
        query = query.filter(Institution.state == filters["state"])
    if "type" in filters and filters["type"]:
        query = query.filter(Institution.institution_type == filters["type"])
    if "active" in filters and filters["active"] is not None:
        query = query.filter(Institution.is_active == filters["active"])

    # Get total before pagination
    total = query.count()
    page = filters.get("page", 1)
    page_size = min(filters.get("page_size", 20), 100)
    query = query.order_by(Institution.name).offset((page - 1) * page_size).limit(page_size)

    institutions = query.all()
    results = []
    for inst in institutions:
        complaints = db.query(Complaint).filter(Complaint.institution_id == inst.id).all()
        open_count = sum(1 for c in complaints if permissions.is_open(c.status))
        overdue_count = sum(
            1 for c in complaints
            if permissions.is_open(c.status) and c.target_date < today
        )

        # Get active bureau codes
        active_bureau_ids = set()
        for c in complaints:
            if permissions.is_open(c.status):
                assigns = db.query(CaseAssignment).filter(
                    CaseAssignment.complaint_id == c.id,
                    CaseAssignment.is_active == True,
                ).all()
                for a in assigns:
                    active_bureau_ids.add(a.bureau_id)

        bureau_codes = []
        for bid in active_bureau_ids:
            bureau = db.query(Bureau).filter(Bureau.id == bid).first()
            if bureau:
                bureau_codes.append(bureau.code)

        # Last activity
        last_activity = None
        if complaints:
            latest = max((c.updated_at for c in complaints), default=None)
            last_activity = latest

        results.append({
            "id": str(inst.id),
            "code": inst.code,
            "aicte_id": inst.code,
            "name": inst.name,
            "institution_type": inst.institution_type,
            "category": inst.institution_type,
            "state": inst.state,
            "district": inst.district,
            "city": inst.city,
            "address": inst.address,
            "email": inst.email,
            "phone": inst.phone,
            "is_active": inst.is_active,
            "open_count": open_count,
            "active_complaints_count": open_count,
            "total_complaints_count": len(complaints),
            "overdue_count": overdue_count,
            "active_bureau_codes": sorted(bureau_codes),
            "last_activity_at": last_activity.isoformat() if last_activity else None,
            "created_at": inst.created_at.isoformat() if inst.created_at else None,
            "updated_at": inst.updated_at.isoformat() if inst.updated_at else None,
        })

    return results, total


def get_coordination(db: Session, inst_id: UUID, user=None, today=None) -> dict:
    """Get bureau coordination view for an institution."""
    from app.core.clock import get_clock
    inst = get_institution(db, inst_id)
    if today is None:
        today = get_clock().today_local()

    complaints = db.query(Complaint).filter(Complaint.institution_id == inst_id).all()
    bureaus = db.query(Bureau).filter(Bureau.is_active == True).all()

    result = {"institution_id": inst_id, "multi_bureau_open": False, "bureaus": []}
    primary_bureaus_with_open = set()

    for bureau in bureaus:
        open_as_primary = 0
        open_as_participating = 0
        complaint_list = []

        for c in complaints:
            if not permissions.is_open(c.status):
                continue

            is_primary = str(c.primary_bureau_id) == str(bureau.id)
            has_active = db.query(CaseAssignment).filter(
                CaseAssignment.complaint_id == c.id,
                CaseAssignment.bureau_id == bureau.id,
                CaseAssignment.is_active == True,
            ).first()

            if is_primary:
                open_as_primary += 1
                primary_bureaus_with_open.add(str(bureau.id))
                complaint_list.append({
                    "id": str(c.id),
                    "reference_number": c.reference_number,
                    "category": c.category,
                    "status": c.status,
                    "role_in_case": "PRIMARY",
                })
            elif has_active:
                open_as_participating += 1
                complaint_list.append({
                    "id": str(c.id),
                    "reference_number": c.reference_number,
                    "category": c.category,
                    "status": c.status,
                    "role_in_case": "PARTICIPATING",
                })

        if open_as_primary > 0 or open_as_participating > 0:
            result["bureaus"].append({
                "bureau_id": bureau.id,
                "bureau_code": bureau.code,
                "bureau_name": bureau.name,
                "open_as_primary": open_as_primary,
                "open_as_participating": open_as_participating,
                "complaints": complaint_list,
            })

    result["multi_bureau_open"] = len(primary_bureaus_with_open) >= 2
    return result


def get_timeline(db: Session, inst_id: UUID, user=None, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
    """Get consolidated timeline for an institution."""
    from app.core.permissions import AccessContext, ComplaintContext, get_access_level
    inst = get_institution(db, inst_id)

    complaints = db.query(Complaint).filter(Complaint.institution_id == inst_id).all()
    events = []

    for c in complaints:
        # Determine access level for this complaint
        access_level = "FULL"
        if user and user.role in permissions.OFFICIAL_ROLES:
            active_assignments = db.query(CaseAssignment).filter(
                CaseAssignment.complaint_id == c.id,
                CaseAssignment.is_active == True,
            ).all()
            participating_ids = [str(a.bureau_id) for a in active_assignments]
            access_ctx = AccessContext(
                user_id=str(user.id),
                user_role=user.role,
                user_bureau_id=str(user.bureau_id) if user.bureau_id else None,
            )
            complaint_ctx = ComplaintContext(
                complaint_id=str(c.id),
                status=c.status,
                primary_bureau_id=str(c.primary_bureau_id),
                owner_user_id=str(c.owner_user_id) if c.owner_user_id else None,
                participating_bureau_ids=[
                    bid for bid in participating_ids if bid != str(c.primary_bureau_id)
                ],
            )
            access_level = get_access_level(access_ctx, complaint_ctx)

        # Registration event
        creator = db.query(User).filter(User.id == c.created_by).first()
        bureau = db.query(Bureau).filter(Bureau.id == c.primary_bureau_id).first()
        events.append({
            "timestamp": c.created_at,
            "type": "COMPLAINT_REGISTERED",
            "complaint_reference": c.reference_number,
            "bureau": bureau.code if bureau else None,
            "actor_name": creator.full_name if creator and access_level == "FULL" else None,
            "summary": f"Complaint {c.reference_number} registered"
                if access_level == "FULL"
                else f"A complaint was registered ({c.reference_number})",
        })

        # Status changes
        statuses = db.query(StatusHistory).filter(
            StatusHistory.complaint_id == c.id
        ).all()
        for sh in statuses:
            if sh.from_status is None:
                continue  # skip initial registration
            changer = db.query(User).filter(User.id == sh.changed_by).first()
            events.append({
                "timestamp": sh.changed_at,
                "type": "STATUS_CHANGED",
                "complaint_reference": c.reference_number,
                "bureau": bureau.code if bureau else None,
                "actor_name": changer.full_name if changer and access_level == "FULL" else None,
                "summary": f"Status changed from {sh.from_status} to {sh.to_status}"
                    if access_level == "FULL"
                    else f"Status changed to {sh.to_status}",
            })

        # Assignments
        assignments = db.query(CaseAssignment).filter(
            CaseAssignment.complaint_id == c.id
        ).all()
        for a in assignments:
            a_bureau = db.query(Bureau).filter(Bureau.id == a.bureau_id).first()
            assigner = db.query(User).filter(User.id == a.assigned_by).first()
            evt_type = "PRIMARY_ASSIGNED" if a.role_in_case == "PRIMARY" else "PARTICIPANT_ADDED"
            events.append({
                "timestamp": a.assigned_at,
                "type": evt_type,
                "complaint_reference": c.reference_number,
                "bureau": a_bureau.code if a_bureau else None,
                "actor_name": assigner.full_name if assigner and access_level == "FULL" else None,
                "summary": f"{a_bureau.code if a_bureau else 'Bureau'} assigned as {a.role_in_case.lower()}",
            })

        # Notes
        notes = db.query(ComplaintNote).filter(ComplaintNote.complaint_id == c.id).all()
        for n in notes:
            n_bureau = db.query(Bureau).filter(Bureau.id == n.bureau_id).first() if n.bureau_id else None
            events.append({
                "timestamp": n.created_at,
                "type": "NOTE_ADDED",
                "complaint_reference": c.reference_number,
                "bureau": n_bureau.code if n_bureau else None,
                "actor_name": None if access_level != "FULL" else None,
                "summary": f"A note was added"
                    + (f" by {n_bureau.code}" if n_bureau and access_level == "SUMMARY" else ""),
            })

    # Sort by timestamp descending
    events.sort(key=lambda e: e["timestamp"], reverse=True)

    total = len(events)
    start = (page - 1) * page_size
    end = start + page_size
    return events[start:end], total
