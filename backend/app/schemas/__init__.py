"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


# --- Auth ---
class LoginRequest(BaseModel):
    email: str | None = None
    username: str | None = None
    password: str = Field(..., min_length=1)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str | None) -> str | None:
        if v is not None and isinstance(v, str):
            return v.strip().lower()
        return v

    @model_validator(mode="after")
    def validate_identifier(self) -> LoginRequest:
        identifier = self.email or self.username
        if not identifier:
            raise ValueError("Either email or username must be provided")
        self.email = identifier.strip().lower()
        return self



class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=10)


# --- Bureau ---
class BureauResponse(BaseModel):
    id: UUID
    code: str
    name: str

    model_config = {"from_attributes": True}


class BureauDetailResponse(BureauResponse):
    description: str | None = None
    is_active: bool
    created_at: datetime


# --- User ---
class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    bureau_id: UUID | None = None
    bureau: BureauResponse | None = None
    designation: str | None = None
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreateRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    full_name: str = Field(..., min_length=2, max_length=150)
    password: str = Field(..., min_length=10)
    role: str
    bureau_id: UUID | None = None
    designation: str | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=150)
    role: str | None = None
    bureau_id: UUID | None = None
    designation: str | None = None


class AssignableUserResponse(BaseModel):
    id: UUID
    full_name: str
    bureau_id: UUID | None = None

    model_config = {"from_attributes": True}


# --- Institution ---
class InstitutionCreateRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=30)
    name: str = Field(..., min_length=1, max_length=255)
    institution_type: str
    state: str = Field(..., min_length=1, max_length=60)
    district: str | None = Field(None, max_length=80)
    city: str | None = Field(None, max_length=80)
    address: str | None = None
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=30)

    @field_validator("code", "name", "state")
    @classmethod
    def strip_strings(cls, v: str) -> str:
        return v.strip()


class InstitutionUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    institution_type: str | None = None
    state: str | None = Field(None, min_length=1, max_length=60)
    district: str | None = Field(None, max_length=80)
    city: str | None = Field(None, max_length=80)
    address: str | None = None
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=30)


class InstitutionResponse(BaseModel):
    id: UUID
    code: str
    name: str
    institution_type: str
    state: str
    district: str | None = None
    city: str | None = None
    is_active: bool
    open_count: int = 0
    overdue_count: int = 0
    active_bureau_codes: list[str] = []
    last_activity_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InstitutionDetailResponse(InstitutionResponse):
    address: str | None = None
    email: str | None = None
    phone: str | None = None
    total_complaints: int = 0
    resolved_count: int = 0
    bureaus_involved: list[str] = []
    pending_relation_reviews: int = 0


class CoordinationBureauInfo(BaseModel):
    bureau_id: UUID
    bureau_code: str
    bureau_name: str
    open_as_primary: int = 0
    open_as_participating: int = 0
    complaints: list[dict[str, Any]] = []


class CoordinationResponse(BaseModel):
    institution_id: UUID
    multi_bureau_open: bool = False
    bureaus: list[CoordinationBureauInfo] = []


# --- Complaint ---
class ComplaintCreateRequest(BaseModel):
    institution_id: UUID
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=20, max_length=5000)
    category: str
    priority: str
    source_channel: str
    complainant_type: str
    complainant_name: str | None = Field(None, max_length=150)
    complainant_contact: str | None = Field(None, max_length=150)
    incident_reference: str | None = Field(None, max_length=100)
    incident_date: date | None = None
    received_date: date | None = None
    target_date: date | None = None
    primary_bureau_id: UUID | None = None
    owner_user_id: UUID | None = None

    @field_validator("title", "description")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()


class ComplaintUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=5, max_length=200)
    description: str | None = Field(None, min_length=20, max_length=5000)
    category: str | None = None
    priority: str | None = None
    source_channel: str | None = None
    complainant_type: str | None = None
    complainant_name: str | None = Field(None, max_length=150)
    complainant_contact: str | None = Field(None, max_length=150)
    incident_reference: str | None = Field(None, max_length=100)
    incident_date: date | None = None
    target_date: date | None = None
    target_date_change_reason: str | None = None
    version: int


class StatusChangeRequest(BaseModel):
    to_status: str
    remark: str | None = None
    resolution_summary: str | None = None
    expected_status: str | None = None
    version: int | None = None
    target_date: date | None = None  # for REOPENED when target is past


class EscalateRequest(BaseModel):
    reason: str = Field(..., min_length=5)


class ClearEscalationRequest(BaseModel):
    note: str = Field(..., min_length=5)


class NoteCreateRequest(BaseModel):
    note_type: str = Field(default="ACTION_NOTE")
    body: str = Field(..., min_length=3, max_length=2000)


class OwnerChangeRequest(BaseModel):
    user_id: UUID | None = None
    reason: str | None = None


class PrimaryTransferRequest(BaseModel):
    bureau_id: UUID
    owner_user_id: UUID | None = None
    reason: str = Field(..., min_length=5)
    context_summary: str | None = None
    key_findings: str | None = None
    keep_previous_as_participant: bool = True


# --- Handover Contract Schemas ---
class HandoverInitiateRequest(BaseModel):
    to_bureau_id: UUID
    target_owner_id: UUID | None = None
    context_summary: str = Field(..., min_length=20)
    key_findings: str | None = None


class HandoverReturnRequest(BaseModel):
    return_reason: str = Field(..., min_length=10)


class HandoverResponse(BaseModel):
    id: UUID
    complaint_id: UUID
    status: str
    context_summary: str
    key_findings: str | None = None
    from_bureau: dict[str, Any] | None = None
    to_bureau: dict[str, Any] | None = None
    initiated_by: dict[str, Any] | None = None
    initiated_at: datetime
    responded_by: dict[str, Any] | None = None
    responded_at: datetime | None = None
    return_reason: str | None = None
    target_owner: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


# --- Waiting-On Ledger Schemas ---
class WaitingOnCreateRequest(BaseModel):
    waiting_on_type: str = "INSTITUTION_REPLY"
    waiting_on_party: str = Field(..., min_length=2, max_length=255)
    since: datetime | None = None
    chaser_user_id: UUID | None = None
    notes: str | None = None


class WaitingOnResolveRequest(BaseModel):
    notes: str | None = None


class WaitingOnUpdateRequest(BaseModel):
    waiting_on_type: str | None = None
    waiting_on_party: str | None = None
    chaser_user_id: UUID | None = None
    notes: str | None = None


class WaitingOnResponse(BaseModel):
    id: UUID
    complaint_id: UUID
    waiting_on_type: str
    waiting_on_type_label: str | None = None
    waiting_on_party: str
    since: datetime
    days_waiting: int = 0
    is_resolved: bool = False
    resolved_at: datetime | None = None
    notes: str | None = None
    chaser: dict[str, Any] | None = None
    resolver: dict[str, Any] | None = None
    creator: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Issue Threads Schemas ---
class ThreadBriefUpdateRequest(BaseModel):
    brief: str = Field(..., min_length=5)
    title: str | None = None


class IssueThreadResponse(BaseModel):
    id: UUID
    title: str
    brief: str | None = None
    status: str = "ACTIVE"
    complaint_count: int = 0
    open_complaint_count: int = 0
    institutions: list[str] = []
    bureaus: list[str] = []
    complaint_references: list[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ParticipantAddRequest(BaseModel):
    bureau_id: UUID
    reason: str | None = None


class ParticipantRemoveRequest(BaseModel):
    reason: str | None = None


class RelatedPreviewRequest(BaseModel):
    institution_id: UUID
    category: str
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=20, max_length=5000)
    incident_reference: str | None = None
    incident_date: date | None = None
    received_date: date | None = None


class RelationConfirmRequest(BaseModel):
    relation_type: str  # SAME_ISSUE or RELATED_ISSUE
    note: str | None = None
    add_participating_bureaus: bool = True


class RelationDismissRequest(BaseModel):
    note: str = Field(..., min_length=1)


class RelationRevertRequest(BaseModel):
    note: str = Field(..., min_length=1)


# --- Responses ---
class AllowedActions(BaseModel):
    can_edit: bool = False
    can_add_note: bool = False
    can_manage_participants: bool = False
    can_change_owner: bool = False
    can_transfer_primary: bool = False
    allowed_status_transitions: list[str] = []
    can_escalate: bool = False
    can_review_relations: bool = False


class ComplaintResponse(BaseModel):
    id: UUID
    reference_number: str
    institution: dict[str, Any] | None = None
    title: str | None = None
    description: str | None = None
    category: str
    priority: str
    status: str
    source_channel: str | None = None
    complainant_type: str | None = None
    complainant_name: str | None = None
    complainant_contact: str | None = None
    incident_reference: str | None = None
    incident_date: date | None = None
    received_date: date
    target_date: date
    is_overdue: bool = False
    days_overdue: int = 0
    escalation_recommended: bool = False
    escalation_level: int = 0
    escalation_reason: str | None = None
    primary_bureau: dict[str, Any] | None = None
    owner: dict[str, Any] | None = None
    participating_bureaus: list[dict[str, Any]] = []
    resolution_summary: str | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    reopened_count: int = 0
    created_by: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1
    access_level: str = "FULL"
    allowed_actions: AllowedActions | None = None
    handover_status: str | None = None
    delay_explanation: dict[str, Any] | None = None
    limbo_flags: list[dict[str, Any]] = []
    waiting_on_summary: dict[str, Any] | None = None
    pending_handover: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class StatusHistoryResponse(BaseModel):
    id: UUID
    from_status: str | None = None
    to_status: str
    changed_by: dict[str, Any] | None = None
    changed_at: datetime
    remark: str | None = None

    model_config = {"from_attributes": True}


class NoteResponse(BaseModel):
    id: UUID
    note_type: str
    body: str
    author: dict[str, Any] | None = None
    bureau: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AssignmentResponse(BaseModel):
    id: UUID
    bureau: dict[str, Any] | None = None
    assigned_user: dict[str, Any] | None = None
    role_in_case: str
    is_active: bool
    assigned_by: dict[str, Any] | None = None
    assigned_at: datetime
    ended_at: datetime | None = None
    reason: str | None = None

    model_config = {"from_attributes": True}


class RelationResponse(BaseModel):
    id: UUID
    complaint_a: dict[str, Any] | None = None
    complaint_b: dict[str, Any] | None = None
    other_complaint: dict[str, Any] | None = None
    status: str
    relation_type: str | None = None
    score: int
    confidence: str
    explanation: dict[str, Any] | None = None
    detected_at: datetime
    reviewed_by: dict[str, Any] | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None

    model_config = {"from_attributes": True}


class NotificationResponse(BaseModel):
    id: UUID
    type: str
    title: str | None = None
    message: str | None = None
    complaint_id: UUID | None = None
    institution_id: UUID | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogResponse(BaseModel):
    id: int
    occurred_at: datetime
    actor_user_id: UUID | None = None
    actor_email: str | None = None
    actor_role: str | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    institution_id: UUID | None = None
    complaint_id: UUID | None = None
    outcome: str
    before_data: dict[str, Any] | None = None
    after_data: dict[str, Any] | None = None
    details: dict[str, Any] | None = None
    ip_address: str | None = None
    request_id: str | None = None

    model_config = {"from_attributes": True}


class TimelineEventResponse(BaseModel):
    timestamp: datetime
    type: str
    complaint_reference: str | None = None
    bureau: str | None = None
    actor_name: str | None = None
    summary: str


# --- Pagination ---
class PaginatedResponse(BaseModel):
    items: list[Any] = []
    total: int = 0
    page: int = 1
    page_size: int = 20


# --- Analytics ---
class AnalyticsSummary(BaseModel):
    total: int = 0
    open: int = 0
    resolved: int = 0
    closed: int = 0
    overdue_open: int = 0
    escalated_open: int = 0
    escalation_recommended_open: int = 0
    received_last_7_days: int = 0
    institutions_with_open_cases: int = 0
    institutions_with_multi_bureau_open_cases: int = 0
    confirmed_relations: int = 0
    pending_relation_reviews: int = 0
    unassigned_owner_open: int = 0


class StatusDistribution(BaseModel):
    status: str
    count: int = 0


class BureauWorkload(BaseModel):
    bureau_id: UUID
    bureau_code: str
    bureau_name: str
    open_as_primary: int = 0
    open_as_participating: int = 0
    overdue_as_primary: int = 0
    resolved_in_range: int = 0
    avg_open_age_days: float = 0.0


class AgingBucket(BaseModel):
    bucket: str
    count: int = 0


class TrendPoint(BaseModel):
    period: str
    received: int = 0
    resolved: int = 0


class TopInstitution(BaseModel):
    institution_id: UUID
    institution_code: str
    institution_name: str
    count: int = 0
