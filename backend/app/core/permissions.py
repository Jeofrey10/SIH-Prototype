"""Centralized permission matrix and authorization logic."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# --- Role Constants ---
SYSTEM_ADMIN = "SYSTEM_ADMIN"
SUPERVISOR = "SUPERVISOR"
RB_OFFICIAL = "RB_OFFICIAL"
PGRC_OFFICIAL = "PGRC_OFFICIAL"

ALL_ROLES = {SYSTEM_ADMIN, SUPERVISOR, RB_OFFICIAL, PGRC_OFFICIAL}
OFFICIAL_ROLES = {RB_OFFICIAL, PGRC_OFFICIAL}
MANAGEMENT_ROLES = {SYSTEM_ADMIN, SUPERVISOR}

# --- Status Constants ---
TERMINAL_STATUSES = {"RESOLVED", "CLOSED"}
OPEN_STATUSES = {"REGISTERED", "UNDER_REVIEW", "ACTION_INITIATED", "PENDING_INFORMATION", "REOPENED"}
ALL_STATUSES = OPEN_STATUSES | TERMINAL_STATUSES

# Valid status transitions
STATUS_TRANSITIONS: dict[str, set[str]] = {
    "REGISTERED": {"UNDER_REVIEW"},
    "UNDER_REVIEW": {"ACTION_INITIATED", "PENDING_INFORMATION", "RESOLVED"},
    "ACTION_INITIATED": {"UNDER_REVIEW", "PENDING_INFORMATION", "RESOLVED"},
    "PENDING_INFORMATION": {"UNDER_REVIEW", "ACTION_INITIATED"},
    "RESOLVED": {"CLOSED", "REOPENED"},
    "CLOSED": {"REOPENED"},
    "REOPENED": {"UNDER_REVIEW", "ACTION_INITIATED", "PENDING_INFORMATION", "RESOLVED"},
}

# Default target date offsets by priority
TARGET_DATE_OFFSETS = {
    "CRITICAL": 7,
    "HIGH": 15,
    "MEDIUM": 30,
    "LOW": 45,
}


@dataclass
class AccessContext:
    """Context for authorization decisions."""
    user_id: str
    user_role: str
    user_bureau_id: str | None
    is_active: bool = True


@dataclass
class ComplaintContext:
    """Complaint-level context for authorization."""
    complaint_id: str
    status: str
    primary_bureau_id: str
    owner_user_id: str | None
    participating_bureau_ids: list[str] = field(default_factory=list)


def is_open(status: str) -> bool:
    """Check if a complaint status is open (non-terminal)."""
    return status in OPEN_STATUSES


def user_participates(access: AccessContext, complaint: ComplaintContext) -> bool:
    """Check if the user's bureau has an active assignment (primary or participating)."""
    if access.user_bureau_id is None:
        return False
    all_bureau_ids = [complaint.primary_bureau_id] + complaint.participating_bureau_ids
    return access.user_bureau_id in all_bureau_ids


def is_primary_bureau(access: AccessContext, complaint: ComplaintContext) -> bool:
    """Check if user's bureau is the primary bureau."""
    return access.user_bureau_id is not None and access.user_bureau_id == complaint.primary_bureau_id


def get_access_level(access: AccessContext, complaint: ComplaintContext) -> str:
    """Determine access level: FULL or SUMMARY."""
    if access.user_role in (SYSTEM_ADMIN, SUPERVISOR):
        return "FULL"
    if user_participates(access, complaint):
        return "FULL"
    return "SUMMARY"


def compute_allowed_actions(
    access: AccessContext,
    complaint: ComplaintContext,
) -> dict[str, Any]:
    """Compute all allowed actions for user on complaint."""
    role = access.user_role
    access_level = get_access_level(access, complaint)
    status = complaint.status
    participates = user_participates(access, complaint)
    is_primary = is_primary_bureau(access, complaint)
    is_sup = role == SUPERVISOR
    is_admin = role == SYSTEM_ADMIN
    is_official = role in OFFICIAL_ROLES

    # Compute allowed status transitions
    all_transitions = STATUS_TRANSITIONS.get(status, set())
    allowed_transitions: list[str] = []

    if is_sup:
        allowed_transitions = sorted(all_transitions)
    elif is_official and is_primary:
        # Officials can't close or reopen from closed
        transitions = set(all_transitions)
        if status == "RESOLVED":
            transitions.discard("CLOSED")
        if status == "CLOSED":
            transitions.discard("REOPENED")
        allowed_transitions = sorted(transitions)

    is_open_complaint = is_open(status)

    return {
        "can_edit": (is_sup or (is_official and is_primary)) and is_open_complaint,
        "can_add_note": (is_sup or (is_official and participates)) and access_level == "FULL",
        "can_manage_participants": (is_sup or (is_official and is_primary)) and is_open_complaint,
        "can_change_owner": (is_sup or (is_official and is_primary)) and is_open_complaint,
        "can_transfer_primary": is_sup and is_open_complaint,
        "allowed_status_transitions": allowed_transitions,
        "can_escalate": (
            (is_sup or (is_official and is_primary))
            and is_open_complaint
            and complaint.__dict__.get("escalation_level", 0) == 0
        ),
        "can_review_relations": (
            is_sup or is_admin or (is_official and participates)
        ),
    }


def can_create_complaint(role: str) -> bool:
    """Check if a role can create complaints."""
    return role in {SUPERVISOR, RB_OFFICIAL, PGRC_OFFICIAL}


def can_manage_users(role: str) -> bool:
    """Check if a role can manage users."""
    return role == SYSTEM_ADMIN


def can_manage_institutions(role: str) -> bool:
    """Check if a role can manage institutions."""
    return role in {SYSTEM_ADMIN, SUPERVISOR}


def can_view_audit_logs(role: str) -> bool:
    """Check if a role can view global audit logs."""
    return role in {SYSTEM_ADMIN, SUPERVISOR}


def can_trigger_overdue_scan(role: str) -> bool:
    """Check if a role can trigger overdue scan."""
    return role in {SYSTEM_ADMIN, SUPERVISOR}


def can_export_all_scope(role: str) -> bool:
    """Check if a role can export reports with all scope."""
    return role in {SYSTEM_ADMIN, SUPERVISOR}


# --- ORM Model Helper Bridges ---
def _build_contexts(complaint: Any, user: Any) -> tuple[AccessContext, ComplaintContext]:
    """Helper to construct AccessContext and ComplaintContext from ORM objects."""
    access = AccessContext(
        user_id=str(user.id),
        user_role=user.role,
        user_bureau_id=str(user.bureau_id) if user.bureau_id else None,
        is_active=user.is_active,
    )
    # Get active participating bureau ids
    part_bureau_ids = []
    if hasattr(complaint, "assignments"):
        for a in complaint.assignments or []:
            if getattr(a, "is_active", False) and getattr(a, "role_in_case", "") == "PARTICIPATING":
                part_bureau_ids.append(str(a.bureau_id))

    complaint_ctx = ComplaintContext(
        complaint_id=str(complaint.id),
        status=complaint.status,
        primary_bureau_id=str(complaint.primary_bureau_id),
        owner_user_id=str(complaint.owner_user_id) if complaint.owner_user_id else None,
        participating_bureau_ids=part_bureau_ids,
    )
    return access, complaint_ctx


def get_complaint_access_level(complaint: Any, user: Any) -> str:
    """Determine whether user has FULL or SUMMARY access to complaint."""
    access, ctx = _build_contexts(complaint, user)
    return get_access_level(access, ctx)


def get_allowed_actions(complaint: Any, user: Any) -> dict[str, Any]:
    """Compute allowed actions map for complaint and user."""
    access, ctx = _build_contexts(complaint, user)
    return compute_allowed_actions(access, ctx)


def can_edit_complaint(complaint: Any, user: Any) -> bool:
    """Check if user can edit complaint."""
    actions = get_allowed_actions(complaint, user)
    return actions.get("can_edit", False)


def can_change_status(complaint: Any, user: Any) -> bool:
    """Check if user can change complaint status."""
    if user.role == SYSTEM_ADMIN:
        return False
    access, ctx = _build_contexts(complaint, user)
    if access.user_role == SUPERVISOR:
        return True
    return user_participates(access, ctx)


def can_add_note(complaint: Any, user: Any) -> bool:
    """Check if user can add notes."""
    actions = get_allowed_actions(complaint, user)
    return actions.get("can_add_note", False)


def can_manage_participants(complaint: Any, user: Any) -> bool:
    """Check if user can manage participating bureaus."""
    actions = get_allowed_actions(complaint, user)
    return actions.get("can_manage_participants", False)


def can_change_owner(complaint: Any, user: Any) -> bool:
    """Check if user can change case owner."""
    actions = get_allowed_actions(complaint, user)
    return actions.get("can_change_owner", False)
