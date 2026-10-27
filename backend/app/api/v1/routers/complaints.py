"""Complaints router."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import AuditLog, CaseAssignment, StatusHistory, User
from app.schemas import (
    ClearEscalationRequest,
    ComplaintCreateRequest,
    ComplaintResponse,
    ComplaintUpdateRequest,
    EscalateRequest,
    NoteCreateRequest,
    OwnerChangeRequest,
    ParticipantAddRequest,
    ParticipantRemoveRequest,
    PrimaryTransferRequest,
    RelatedPreviewRequest,
    StatusChangeRequest,
)
from app.services import complaints as complaint_service
from app.services.relations import service as relation_service

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.get("", response_model=dict)
def list_complaints(
    q: str | None = Query(None),
    institution_id: UUID | None = Query(None),
    status: list[str] | None = Query(None),
    category: str | None = Query(None),
    priority: str | None = Query(None),
    primary_bureau_id: UUID | None = Query(None),
    participating_bureau_id: UUID | None = Query(None),
    owner_user_id: UUID | None = Query(None),
    unassigned_owner: bool | None = Query(None),
    overdue: bool | None = Query(None),
    escalated: bool | None = Query(None),
    received_from: date | None = Query(None),
    received_to: date | None = Query(None),
    scope: str | None = Query(None),
    sort_by: str = Query("received_date"),
    order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List complaints with filters and role-based scoping."""
    items, total = complaint_service.list_complaints(
        db,
        actor=current_user,
        q=q,
        institution_id=institution_id,
        status=status,
        category=category,
        priority=priority,
        primary_bureau_id=primary_bureau_id,
        participating_bureau_id=participating_bureau_id,
        owner_user_id=owner_user_id,
        unassigned_owner=unassigned_owner,
        overdue=overdue,
        escalated=escalated,
        received_from=received_from,
        received_to=received_to,
        scope=scope,
        sort_by=sort_by,
        order=order,
        page=page,
        page_size=page_size,
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", status_code=201)
def create_complaint(
    req: ComplaintCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register a new complaint."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    complaint, candidates = complaint_service.create_complaint(
        db,
        data=req.model_dump(),
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()

    detail = complaint_service.get_complaint_detail(db, complaint.id, current_user)
    detail["related_candidates"] = candidates
    return detail


@router.post("/related-preview")
def preview_related(
    req: RelatedPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Evaluate potential related complaints without persisting anything."""
    candidates = relation_service.preview_related_candidates(
        db, data=req.model_dump()
    )
    return {"candidates": candidates}


@router.get("/{complaint_id}")
def get_complaint(
    complaint_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full details and allowed actions for a complaint."""
    return complaint_service.get_complaint_detail(db, complaint_id, current_user)


@router.patch("/{complaint_id}")
def update_complaint(
    complaint_id: UUID,
    req: ComplaintUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update editable complaint fields with optimistic locking."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    complaint = complaint_service.update_complaint(
        db,
        complaint_id=complaint_id,
        data=req.model_dump(exclude_unset=True),
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return complaint_service.get_complaint_detail(db, complaint.id, current_user)


@router.post("/{complaint_id}/status")
def change_status(
    complaint_id: UUID,
    req: StatusChangeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Transition complaint status."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    complaint = complaint_service.change_status(
        db,
        complaint_id=complaint_id,
        data=req.model_dump(exclude_unset=True),
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return complaint_service.get_complaint_detail(db, complaint.id, current_user)


@router.post("/{complaint_id}/escalate")
def escalate(
    complaint_id: UUID,
    req: EscalateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Escalate complaint."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    complaint = complaint_service.escalate_complaint(
        db,
        complaint_id=complaint_id,
        data=req.model_dump(),
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return complaint_service.get_complaint_detail(db, complaint.id, current_user)


@router.post("/{complaint_id}/clear-escalation")
def clear_escalation(
    complaint_id: UUID,
    req: ClearEscalationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clear escalation (Supervisor only)."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    complaint = complaint_service.clear_escalation(
        db,
        complaint_id=complaint_id,
        data=req.model_dump(),
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return complaint_service.get_complaint_detail(db, complaint.id, current_user)


@router.get("/{complaint_id}/notes")
def get_notes(
    complaint_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List notes for a complaint."""
    notes = complaint_service.get_notes(db, complaint_id, current_user)
    return [
        {
            "id": n.id,
            "note_type": n.note_type,
            "body": n.body,
            "author": {
                "id": n.author.id,
                "full_name": n.author.full_name,
                "role": n.author.role,
            } if n.author else None,
            "created_at": n.created_at,
        }
        for n in notes
    ]


@router.post("/{complaint_id}/notes")
def add_note(
    complaint_id: UUID,
    req: NoteCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add an action or coordination note."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    note = complaint_service.add_note(
        db,
        complaint_id=complaint_id,
        data=req.model_dump(),
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return {
        "id": note.id,
        "note_type": note.note_type,
        "body": note.body,
        "created_at": note.created_at,
    }


@router.get("/{complaint_id}/history")
def get_status_history(
    complaint_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get status change history."""
    history = (
        db.query(StatusHistory)
        .filter(StatusHistory.complaint_id == complaint_id)
        .order_by(StatusHistory.changed_at.asc())
        .all()
    )
    return [
        {
            "id": h.id,
            "from_status": h.from_status,
            "to_status": h.to_status,
            "changed_by": {
                "id": h.user.id,
                "full_name": h.user.full_name,
            } if h.user else None,
            "changed_at": h.changed_at,
            "remark": h.remark,
        }
        for h in history
    ]


@router.get("/{complaint_id}/assignments")
def get_assignments(
    complaint_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get complete case assignment history."""
    assignments = (
        db.query(CaseAssignment)
        .filter(CaseAssignment.complaint_id == complaint_id)
        .order_by(CaseAssignment.assigned_at.asc())
        .all()
    )
    return [
        {
            "id": a.id,
            "bureau": {
                "id": a.bureau.id,
                "code": a.bureau.code,
                "name": a.bureau.name,
            } if a.bureau else None,
            "assignment_type": a.assignment_type,
            "assigned_user": {
                "id": a.assigned_user.id,
                "full_name": a.assigned_user.full_name,
            } if a.assigned_user else None,
            "assigned_by": {
                "id": a.assigned_by_user.id,
                "full_name": a.assigned_by_user.full_name,
            } if a.assigned_by_user else None,
            "assigned_at": a.assigned_at,
            "assignment_reason": a.assignment_reason,
            "is_active": a.is_active,
            "ended_at": a.ended_at,
        }
        for a in assignments
    ]


@router.post("/{complaint_id}/participants")
def add_participant(
    complaint_id: UUID,
    req: ParticipantAddRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a participating bureau."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    assignment = complaint_service.add_participant(
        db,
        complaint_id=complaint_id,
        data=req.model_dump(),
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return {"message": "Participant bureau added successfully"}


@router.delete("/{complaint_id}/participants/{bureau_id}")
def remove_participant(
    complaint_id: UUID,
    bureau_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a participating bureau."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    complaint_service.remove_participant(
        db,
        complaint_id=complaint_id,
        bureau_id=bureau_id,
        data=None,
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return {"message": "Participant bureau removed successfully"}


@router.post("/{complaint_id}/owner")
def change_owner(
    complaint_id: UUID,
    req: OwnerChangeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change owner within primary bureau."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    complaint = complaint_service.change_owner(
        db,
        complaint_id=complaint_id,
        data=req.model_dump(),
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return complaint_service.get_complaint_detail(db, complaint.id, current_user)


@router.post("/{complaint_id}/primary-transfer")
def transfer_primary(
    complaint_id: UUID,
    req: PrimaryTransferRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Transfer primary bureau ownership via Handover Contract (Supervisor only)."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    from app.services import handover as handover_service
    summary = (req.context_summary or req.reason).strip()
    if len(summary) < 20:
        summary = f"{summary} - Handover transfer initiated by supervisor."

    handover_service.initiate_handover(
        db,
        complaint_id=complaint_id,
        data={
            "to_bureau_id": req.bureau_id,
            "target_owner_id": req.owner_user_id,
            "context_summary": summary,
            "key_findings": req.key_findings,
        },
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return complaint_service.get_complaint_detail(db, complaint_id, current_user)


# --- Handover Contract Endpoints ---
@router.post("/{complaint_id}/handover/initiate")
def initiate_handover_endpoint(
    complaint_id: UUID,
    req: HandoverInitiateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Initiate an inter-bureau handover contract."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    from app.services import handover as handover_service
    handover = handover_service.initiate_handover(
        db,
        complaint_id=complaint_id,
        data=req.model_dump(),
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return complaint_service.get_complaint_detail(db, complaint_id, current_user)


@router.post("/{complaint_id}/handover/accept")
def accept_handover_endpoint(
    complaint_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Receiving bureau accepts the handover contract."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    from app.services import handover as handover_service
    handover_service.accept_handover(
        db,
        complaint_id=complaint_id,
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return complaint_service.get_complaint_detail(db, complaint_id, current_user)


@router.post("/{complaint_id}/handover/return")
def return_handover_endpoint(
    complaint_id: UUID,
    req: HandoverReturnRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Receiving bureau returns the handover contract with an explicit reason."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    from app.services import handover as handover_service
    handover_service.return_handover(
        db,
        complaint_id=complaint_id,
        return_reason=req.return_reason,
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return complaint_service.get_complaint_detail(db, complaint_id, current_user)


@router.get("/{complaint_id}/handover")
def get_complaint_handovers(
    complaint_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full handover history for this complaint."""
    from app.services import handover as handover_service
    return handover_service.get_handovers_for_complaint(db, complaint_id)


# --- Waiting-On Ledger Endpoints ---
@router.get("/{complaint_id}/waiting-on")
def get_waiting_on_entries_endpoint(
    complaint_id: UUID,
    active_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List waiting commitments on this case."""
    from app.services import waiting_on as waiting_service
    return waiting_service.get_waiting_entries(db, complaint_id, active_only=active_only)


@router.post("/{complaint_id}/waiting-on", status_code=201)
def add_waiting_on_entry_endpoint(
    complaint_id: UUID,
    req: WaitingOnCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record what the complaint is waiting on, from whom, and assign a chaser."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    from app.services import waiting_on as waiting_service
    entry = waiting_service.add_waiting_entry(
        db,
        complaint_id=complaint_id,
        data=req.model_dump(),
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return waiting_service.get_waiting_entries(db, complaint_id, active_only=False)


@router.post("/{complaint_id}/waiting-on/{entry_id}/resolve")
def resolve_waiting_on_entry_endpoint(
    complaint_id: UUID,
    entry_id: UUID,
    req: WaitingOnResolveRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a waiting entry as resolved."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    from app.services import waiting_on as waiting_service
    waiting_service.resolve_waiting_entry(
        db,
        complaint_id=complaint_id,
        entry_id=entry_id,
        notes=req.notes,
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return waiting_service.get_waiting_entries(db, complaint_id, active_only=False)


@router.patch("/{complaint_id}/waiting-on/{entry_id}")
def update_waiting_on_entry_endpoint(
    complaint_id: UUID,
    entry_id: UUID,
    req: WaitingOnUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update chaser or notes on an active waiting ledger entry."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    from app.services import waiting_on as waiting_service
    waiting_service.update_waiting_entry(
        db,
        complaint_id=complaint_id,
        entry_id=entry_id,
        data=req.model_dump(exclude_unset=True),
        actor=current_user,
        ip=client_ip,
        request_id=request_id,
    )
    db.commit()
    return waiting_service.get_waiting_entries(db, complaint_id, active_only=False)


# --- Limbo Flags Endpoint ---
@router.get("/{complaint_id}/limbo-flags")
def get_limbo_flags_endpoint(
    complaint_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Evaluate deterministic limbo and ping-pong rules for this complaint."""
    from app.services.limbo_detector import detect_limbo_flags
    return detect_limbo_flags(db, complaint_id)


@router.get("/{complaint_id}/relations")
def get_relations(
    complaint_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all relations involving this complaint."""
    return relation_service.get_complaint_relations(db, complaint_id, current_user)


@router.post("/{complaint_id}/detect-related")
def detect_related(
    complaint_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Re-run duplicate/related detection idempotently."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        from app.core import errors
        raise errors.not_found("Complaint", str(complaint_id))

    relations = relation_service.detect_and_persist_relations(
        db, complaint, actor=current_user, ip=client_ip, request_id=request_id
    )
    db.commit()
    return relation_service.get_complaint_relations(db, complaint_id, current_user)


@router.get("/{complaint_id}/audit")
def get_complaint_audit(
    complaint_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get audit trail for a complaint (requires FULL access)."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        from app.core import errors
        raise errors.not_found("Complaint", str(complaint_id))

    from app.core import permissions
    if permissions.get_complaint_access_level(complaint, current_user) != "FULL":
        from app.core import errors
        raise errors.forbidden("You do not have access to view audit records for this complaint")

    logs = (
        db.query(AuditLog)
        .filter(AuditLog.complaint_id == complaint_id)
        .order_by(AuditLog.timestamp.desc())
        .all()
    )
    return [
        {
            "id": l.id,
            "timestamp": l.timestamp,
            "actor_email": l.actor_email,
            "actor_role": l.actor_role,
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "before_state": l.before_state,
            "after_state": l.after_state,
            "outcome": l.outcome,
        }
        for l in logs
    ]
