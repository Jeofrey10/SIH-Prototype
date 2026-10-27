"""SQLAlchemy ORM models for the AICTE Complaint Dashboard."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _uuid():
    return uuid.uuid4()


class Bureau(Base):
    __tablename__ = "bureaus"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    users = relationship("User", back_populates="bureau")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    email = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(String(20), nullable=False)
    bureau_id = Column(UUID(as_uuid=True), ForeignKey("bureaus.id", ondelete="RESTRICT"), nullable=True)
    designation = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    failed_login_count = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    bureau = relationship("Bureau", back_populates="users")

    __table_args__ = (
        Index("ix_users_email_lower", text("lower(email)"), unique=True),
        CheckConstraint(
            "role IN ('SYSTEM_ADMIN', 'SUPERVISOR', 'RB_OFFICIAL', 'PGRC_OFFICIAL')",
            name="valid_role",
        ),
        CheckConstraint(
            "(role IN ('SYSTEM_ADMIN', 'SUPERVISOR') AND bureau_id IS NULL) OR "
            "(role IN ('RB_OFFICIAL', 'PGRC_OFFICIAL') AND bureau_id IS NOT NULL)",
            name="role_bureau_consistency",
        ),
    )


class Institution(Base):
    __tablename__ = "institutions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    code = Column(String(30), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    name_normalized = Column(String(255), nullable=False)
    institution_type = Column(String(40), nullable=False)
    state = Column(String(60), nullable=False)
    district = Column(String(80), nullable=True)
    city = Column(String(80), nullable=True)
    address = Column(Text, nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(30), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_institutions_state", "state"),
        Index("ix_institutions_name_normalized", "name_normalized"),
        Index("ix_institutions_is_active", "is_active"),
        CheckConstraint(
            "institution_type IN ('ENGINEERING', 'MANAGEMENT', 'PHARMACY', 'ARCHITECTURE', 'POLYTECHNIC', 'OTHER')",
            name="valid_institution_type",
        ),
    )


class ReferenceCounter(Base):
    __tablename__ = "reference_counters"

    year = Column(Integer, primary_key=True)
    last_value = Column(Integer, nullable=False, default=0)


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    reference_number = Column(String(30), unique=True, nullable=False)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(40), nullable=False)
    priority = Column(String(10), nullable=False)
    status = Column(String(25), nullable=False, default="REGISTERED")
    source_channel = Column(String(20), nullable=False)
    complainant_type = Column(String(20), nullable=False)
    complainant_name = Column(String(150), nullable=True)
    complainant_contact = Column(String(150), nullable=True)
    incident_reference = Column(String(100), nullable=True)
    incident_date = Column(Date, nullable=True)
    received_date = Column(Date, nullable=False)
    target_date = Column(Date, nullable=False)
    primary_bureau_id = Column(UUID(as_uuid=True), ForeignKey("bureaus.id", ondelete="RESTRICT"), nullable=False)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    resolution_summary = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    reopened_count = Column(Integer, nullable=False, default=0)
    escalation_level = Column(SmallInteger, nullable=False, default=0)
    escalated_at = Column(DateTime(timezone=True), nullable=True)
    escalated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    escalation_reason = Column(Text, nullable=True)
    escalation_recommended = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    handover_status = Column(String(20), nullable=True)
    keywords = Column(ARRAY(Text), nullable=False, server_default=text("'{}'::text[]"))
    participating_bureau_codes = Column(ARRAY(Text), nullable=False, server_default=text("'{}'::text[]"))
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    institution = relationship("Institution")
    primary_bureau = relationship("Bureau", foreign_keys=[primary_bureau_id])
    owner = relationship("User", foreign_keys=[owner_user_id])
    creator = relationship("User", foreign_keys=[created_by])
    handovers = relationship("Handover", back_populates="complaint", foreign_keys="Handover.complaint_id")
    waiting_on_entries = relationship("WaitingOnEntry", back_populates="complaint", foreign_keys="WaitingOnEntry.complaint_id")

    __table_args__ = (
        Index("ix_complaints_institution_status", "institution_id", "status"),
        Index("ix_complaints_primary_bureau_status", "primary_bureau_id", "status"),
        Index("ix_complaints_owner_user_id", "owner_user_id"),
        Index("ix_complaints_received_date", "received_date"),
        Index("ix_complaints_category_institution", "category", "institution_id"),
        Index(
            "ix_complaints_target_date_open",
            "target_date",
            postgresql_where=text("status NOT IN ('RESOLVED', 'CLOSED')"),
        ),
        CheckConstraint(
            "category IN ('AFFILIATION_APPROVAL', 'FEES_REFUND', 'FACULTY_ISSUES', "
            "'INFRASTRUCTURE', 'ACADEMIC_MISCONDUCT', 'ADMISSION_IRREGULARITY', "
            "'FRAUD_FALSE_CLAIMS', 'STUDENT_WELFARE', 'OTHER')",
            name="valid_category",
        ),
        CheckConstraint(
            "priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="valid_priority",
        ),
        CheckConstraint(
            "status IN ('REGISTERED', 'UNDER_REVIEW', 'ACTION_INITIATED', "
            "'PENDING_INFORMATION', 'RESOLVED', 'CLOSED', 'REOPENED')",
            name="valid_status",
        ),
        CheckConstraint(
            "source_channel IN ('PORTAL', 'EMAIL', 'LETTER', 'PHONE', 'OTHER')",
            name="valid_source_channel",
        ),
        CheckConstraint(
            "complainant_type IN ('STUDENT', 'FACULTY', 'PARENT', 'STAKEHOLDER', 'ANONYMOUS', 'OTHER')",
            name="valid_complainant_type",
        ),
        CheckConstraint("target_date >= received_date", name="target_after_received"),
        CheckConstraint("escalation_level IN (0, 1)", name="valid_escalation_level"),
    )


class CaseAssignment(Base):
    __tablename__ = "case_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    complaint_id = Column(UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=False)
    bureau_id = Column(UUID(as_uuid=True), ForeignKey("bureaus.id", ondelete="RESTRICT"), nullable=False)
    assigned_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    role_in_case = Column(String(15), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    ended_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    reason = Column(Text, nullable=True)

    complaint = relationship("Complaint")
    bureau = relationship("Bureau")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])

    __table_args__ = (
        Index(
            "ix_case_assignments_active_primary",
            "complaint_id",
            unique=True,
            postgresql_where=text("is_active AND role_in_case = 'PRIMARY'"),
        ),
        Index(
            "ix_case_assignments_active_bureau",
            "complaint_id",
            "bureau_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
        CheckConstraint(
            "role_in_case IN ('PRIMARY', 'PARTICIPATING')",
            name="valid_role_in_case",
        ),
        CheckConstraint(
            "is_active OR ended_at IS NOT NULL",
            name="ended_has_timestamp",
        ),
    )


class StatusHistory(Base):
    __tablename__ = "status_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    complaint_id = Column(UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=False)
    from_status = Column(String(25), nullable=True)
    to_status = Column(String(25), nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    changed_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    remark = Column(Text, nullable=True)

    complaint = relationship("Complaint")
    changer = relationship("User")

    __table_args__ = (
        Index("ix_status_history_complaint_changed_at", "complaint_id", "changed_at"),
    )


class ComplaintNote(Base):
    __tablename__ = "complaint_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    complaint_id = Column(UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    bureau_id = Column(UUID(as_uuid=True), ForeignKey("bureaus.id", ondelete="RESTRICT"), nullable=True)
    note_type = Column(String(20), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    complaint = relationship("Complaint")
    author = relationship("User")
    bureau = relationship("Bureau")

    __table_args__ = (
        CheckConstraint(
            "note_type IN ('ACTION_NOTE', 'COORDINATION_NOTE', 'ESCALATION_NOTE')",
            name="valid_note_type",
        ),
        CheckConstraint("length(body) >= 3 AND length(body) <= 2000", name="note_body_length"),
    )


class ComplaintRelation(Base):
    __tablename__ = "complaint_relations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    complaint_a_id = Column(UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=False)
    complaint_b_id = Column(UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(15), nullable=False, default="SUGGESTED")
    relation_type = Column(String(20), nullable=True)
    score = Column(SmallInteger, nullable=False)
    confidence = Column(String(10), nullable=False)
    explanation = Column(JSONB, nullable=False)
    algorithm_version = Column(String(10), nullable=False)
    detected_from_complaint_id = Column(UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=False)
    detected_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_note = Column(Text, nullable=True)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("issue_threads.id", ondelete="SET NULL"), nullable=True)

    complaint_a = relationship("Complaint", foreign_keys=[complaint_a_id])
    complaint_b = relationship("Complaint", foreign_keys=[complaint_b_id])
    thread = relationship("IssueThread", back_populates="relations")

    __table_args__ = (
        CheckConstraint("complaint_a_id < complaint_b_id", name="canonical_order"),
        UniqueConstraint("complaint_a_id", "complaint_b_id", name="uq_complaint_pair"),
        CheckConstraint(
            "status IN ('SUGGESTED', 'CONFIRMED', 'DISMISSED')",
            name="valid_relation_status",
        ),
        CheckConstraint(
            "relation_type IS NULL OR relation_type IN ('SAME_ISSUE', 'RELATED_ISSUE')",
            name="valid_relation_type",
        ),
        CheckConstraint("score >= 0 AND score <= 100", name="valid_score"),
        CheckConstraint(
            "confidence IN ('HIGH', 'MEDIUM')",
            name="valid_confidence",
        ),
        Index("ix_complaint_relations_status", "status"),
        Index("ix_complaint_relations_a", "complaint_a_id"),
        Index("ix_complaint_relations_b", "complaint_b_id"),
    )


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    type = Column(String(30), nullable=False)
    title = Column(String(200), nullable=True)
    message = Column(Text, nullable=True)
    complaint_id = Column(UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=True)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    dedupe_key = Column(String(200), nullable=True, unique=True)

    user = relationship("User")

    __table_args__ = (
        Index("ix_notifications_user_read_created", "user_id", "is_read", created_at.desc()),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    actor_user_id = Column(UUID(as_uuid=True), nullable=True)
    actor_email = Column(String(255), nullable=True)
    actor_role = Column(String(20), nullable=True)
    action = Column(String(50), nullable=False)
    entity_type = Column(String(40), nullable=False)
    entity_id = Column(String(64), nullable=True)
    institution_id = Column(UUID(as_uuid=True), nullable=True)
    complaint_id = Column(UUID(as_uuid=True), nullable=True)
    outcome = Column(String(10), nullable=False)
    before_data = Column(JSONB, nullable=True)
    after_data = Column(JSONB, nullable=True)
    details = Column(JSONB, nullable=True)
    ip_address = Column(String(64), nullable=True)
    request_id = Column(String(64), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "outcome IN ('SUCCESS', 'DENIED', 'FAILED')",
            name="valid_outcome",
        ),
        Index("ix_audit_logs_occurred_at", occurred_at.desc()),
        Index("ix_audit_logs_complaint_id", "complaint_id"),
        Index("ix_audit_logs_institution_id", "institution_id"),
        Index("ix_audit_logs_actor_user_id", "actor_user_id"),
        Index("ix_audit_logs_action", "action"),
    )


class Handover(Base):
    __tablename__ = "handovers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    complaint_id = Column(UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=False)
    from_bureau_id = Column(UUID(as_uuid=True), ForeignKey("bureaus.id", ondelete="RESTRICT"), nullable=False)
    to_bureau_id = Column(UUID(as_uuid=True), ForeignKey("bureaus.id", ondelete="RESTRICT"), nullable=False)
    target_owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    initiated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    initiated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    status = Column(String(20), nullable=False, default="PENDING")
    context_summary = Column(Text, nullable=False)
    key_findings = Column(Text, nullable=True)
    responded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    return_reason = Column(Text, nullable=True)

    complaint = relationship("Complaint", back_populates="handovers", foreign_keys=[complaint_id])
    from_bureau = relationship("Bureau", foreign_keys=[from_bureau_id])
    to_bureau = relationship("Bureau", foreign_keys=[to_bureau_id])
    target_owner = relationship("User", foreign_keys=[target_owner_id])
    initiator = relationship("User", foreign_keys=[initiated_by])
    responder = relationship("User", foreign_keys=[responded_by])

    __table_args__ = (
        Index("ix_handovers_complaint_id", "complaint_id"),
        Index("ix_handovers_status", "status"),
        CheckConstraint("status IN ('PENDING', 'ACCEPTED', 'RETURNED')", name="valid_handover_status"),
    )


class WaitingOnEntry(Base):
    __tablename__ = "waiting_on_ledger"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    complaint_id = Column(UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=False)
    waiting_on_type = Column(String(40), nullable=False)
    waiting_on_party = Column(String(255), nullable=False)
    since = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    chaser_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    is_resolved = Column(Boolean, nullable=False, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    complaint = relationship("Complaint", back_populates="waiting_on_entries", foreign_keys=[complaint_id])
    chaser = relationship("User", foreign_keys=[chaser_user_id])
    resolver = relationship("User", foreign_keys=[resolved_by])
    creator = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        Index("ix_waiting_on_ledger_complaint_id", "complaint_id"),
        Index("ix_waiting_on_ledger_is_resolved", "is_resolved"),
    )


class IssueThread(Base):
    __tablename__ = "issue_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    title = Column(String(255), nullable=False)
    brief = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    relations = relationship("ComplaintRelation", back_populates="thread")

