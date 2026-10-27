"""Initial schema migration with reference data and append-only triggers.

Revision ID: 0001
Revises: 
Create Date: 2026-10-24 18:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. bureaus
    op.create_table(
        "bureaus",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # Insert reference rows
    op.execute(
        sa.text(
            "INSERT INTO bureaus (id, code, name, description, is_active, created_at) VALUES "
            "(gen_random_uuid(), 'RB', 'Regulation Bureau', 'Regulatory compliance and standards', true, now()), "
            "(gen_random_uuid(), 'PGRC', 'Public Grievance Redressal Cell', 'Student and faculty grievance redressal', true, now())"
        )
    )

    # 2. users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("bureau_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bureaus.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("designation", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("failed_login_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "role IN ('SYSTEM_ADMIN', 'SUPERVISOR', 'RB_OFFICIAL', 'PGRC_OFFICIAL')",
            name="valid_role",
        ),
        sa.CheckConstraint(
            "(role IN ('SYSTEM_ADMIN', 'SUPERVISOR') AND bureau_id IS NULL) OR "
            "(role IN ('RB_OFFICIAL', 'PGRC_OFFICIAL') AND bureau_id IS NOT NULL)",
            name="role_bureau_consistency",
        ),
    )
    op.execute("CREATE UNIQUE INDEX ix_users_email_lower ON users (lower(email))")

    # 3. institutions
    op.create_table(
        "institutions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(30), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("name_normalized", sa.String(255), nullable=False),
        sa.Column("institution_type", sa.String(40), nullable=False),
        sa.Column("state", sa.String(60), nullable=False),
        sa.Column("district", sa.String(80), nullable=True),
        sa.Column("city", sa.String(80), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "institution_type IN ('ENGINEERING', 'MANAGEMENT', 'PHARMACY', 'ARCHITECTURE', 'POLYTECHNIC', 'OTHER')",
            name="valid_institution_type",
        ),
    )
    op.create_index("ix_institutions_state", "institutions", ["state"])
    op.create_index("ix_institutions_name_normalized", "institutions", ["name_normalized"])
    op.create_index("ix_institutions_is_active", "institutions", ["is_active"])

    # 4. reference_counters
    op.create_table(
        "reference_counters",
        sa.Column("year", sa.Integer(), primary_key=True),
        sa.Column("last_value", sa.Integer(), server_default="0", nullable=False),
    )

    # 5. complaints
    op.create_table(
        "complaints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reference_number", sa.String(30), unique=True, nullable=False),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("priority", sa.String(10), nullable=False),
        sa.Column("status", sa.String(25), server_default="REGISTERED", nullable=False),
        sa.Column("source_channel", sa.String(20), nullable=False),
        sa.Column("complainant_type", sa.String(20), nullable=False),
        sa.Column("complainant_name", sa.String(150), nullable=True),
        sa.Column("complainant_contact", sa.String(150), nullable=True),
        sa.Column("incident_reference", sa.String(100), nullable=True),
        sa.Column("incident_date", sa.Date(), nullable=True),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("primary_bureau_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bureaus.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("resolution_summary", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reopened_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("escalation_level", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("escalation_reason", sa.Text(), nullable=True),
        sa.Column("keywords", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "category IN ('AFFILIATION_APPROVAL', 'FEES_REFUND', 'FACULTY_ISSUES', 'INFRASTRUCTURE', "
            "'ACADEMIC_MISCONDUCT', 'ADMISSION_IRREGULARITY', 'FRAUD_FALSE_CLAIMS', 'STUDENT_WELFARE', 'OTHER')",
            name="valid_category",
        ),
        sa.CheckConstraint("priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name="valid_priority"),
        sa.CheckConstraint(
            "status IN ('REGISTERED', 'UNDER_REVIEW', 'ACTION_INITIATED', 'PENDING_INFORMATION', 'RESOLVED', 'CLOSED', 'REOPENED')",
            name="valid_status",
        ),
        sa.CheckConstraint("source_channel IN ('PORTAL', 'EMAIL', 'LETTER', 'PHONE', 'OTHER')", name="valid_source_channel"),
        sa.CheckConstraint("complainant_type IN ('STUDENT', 'FACULTY', 'PARENT', 'STAKEHOLDER', 'ANONYMOUS', 'OTHER')", name="valid_complainant_type"),
        sa.CheckConstraint("target_date >= received_date", name="target_after_received"),
        sa.CheckConstraint("escalation_level IN (0, 1)", name="valid_escalation_level"),
    )
    op.create_index("ix_complaints_institution_status", "complaints", ["institution_id", "status"])
    op.create_index("ix_complaints_primary_bureau_status", "complaints", ["primary_bureau_id", "status"])
    op.create_index("ix_complaints_owner_user_id", "complaints", ["owner_user_id"])
    op.create_index("ix_complaints_received_date", "complaints", ["received_date"])
    op.create_index("ix_complaints_category_institution", "complaints", ["category", "institution_id"])
    op.execute(
        "CREATE INDEX ix_complaints_target_date_open ON complaints (target_date) "
        "WHERE status NOT IN ('RESOLVED', 'CLOSED')"
    )

    # 6. case_assignments
    op.create_table(
        "case_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("complaint_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("bureau_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bureaus.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("role_in_case", sa.String(15), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.CheckConstraint("role_in_case IN ('PRIMARY', 'PARTICIPATING')", name="valid_role_in_case"),
        sa.CheckConstraint("is_active OR ended_at IS NOT NULL", name="ended_has_timestamp"),
    )
    op.execute(
        "CREATE UNIQUE INDEX ix_case_assignments_active_primary ON case_assignments (complaint_id) "
        "WHERE is_active AND role_in_case = 'PRIMARY'"
    )
    op.execute(
        "CREATE UNIQUE INDEX ix_case_assignments_active_bureau ON case_assignments (complaint_id, bureau_id) "
        "WHERE is_active"
    )

    # 7. status_history
    op.create_table(
        "status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("complaint_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("from_status", sa.String(25), nullable=True),
        sa.Column("to_status", sa.String(25), nullable=False),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
    )
    op.create_index("ix_status_history_complaint_changed_at", "status_history", ["complaint_id", "changed_at"])

    # 8. complaint_notes
    op.create_table(
        "complaint_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("complaint_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("bureau_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bureaus.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("note_type", sa.String(20), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("note_type IN ('ACTION_NOTE', 'COORDINATION_NOTE', 'ESCALATION_NOTE')", name="valid_note_type"),
        sa.CheckConstraint("length(body) >= 3 AND length(body) <= 2000", name="note_body_length"),
    )

    # 9. complaint_relations
    op.create_table(
        "complaint_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("complaint_a_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("complaint_b_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(15), server_default="SUGGESTED", nullable=False),
        sa.Column("relation_type", sa.String(20), nullable=True),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column("confidence", sa.String(10), nullable=False),
        sa.Column("explanation", postgresql.JSONB(), nullable=False),
        sa.Column("algorithm_version", sa.String(10), nullable=False),
        sa.Column("detected_from_complaint_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.CheckConstraint("complaint_a_id < complaint_b_id", name="canonical_order"),
        sa.UniqueConstraint("complaint_a_id", "complaint_b_id", name="uq_complaint_pair"),
        sa.CheckConstraint("status IN ('SUGGESTED', 'CONFIRMED', 'DISMISSED')", name="valid_relation_status"),
        sa.CheckConstraint("relation_type IS NULL OR relation_type IN ('SAME_ISSUE', 'RELATED_ISSUE')", name="valid_relation_type"),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="valid_score"),
        sa.CheckConstraint("confidence IN ('HIGH', 'MEDIUM')", name="valid_confidence"),
    )
    op.create_index("ix_complaint_relations_status", "complaint_relations", ["status"])
    op.create_index("ix_complaint_relations_a", "complaint_relations", ["complaint_a_id"])
    op.create_index("ix_complaint_relations_b", "complaint_relations", ["complaint_b_id"])

    # 10. notifications
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("complaint_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("dedupe_key", sa.String(200), unique=True, nullable=True),
    )
    op.create_index("ix_notifications_user_read_created", "notifications", ["user_id", "is_read", "created_at"])

    # 11. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("actor_role", sa.String(20), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("complaint_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outcome", sa.String(10), nullable=False),
        sa.Column("before_data", postgresql.JSONB(), nullable=True),
        sa.Column("after_data", postgresql.JSONB(), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.CheckConstraint("outcome IN ('SUCCESS', 'DENIED', 'FAILED')", name="valid_outcome"),
    )
    op.create_index("ix_audit_logs_occurred_at", "audit_logs", ["occurred_at"])
    op.create_index("ix_audit_logs_complaint_id", "audit_logs", ["complaint_id"])
    op.create_index("ix_audit_logs_institution_id", "audit_logs", ["institution_id"])
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    # 12. Append-only triggers on status_history and audit_logs
    op.execute("""
    CREATE OR REPLACE FUNCTION prevent_modifications_on_append_only()
    RETURNS TRIGGER AS $$
    BEGIN
        IF current_setting('app.allow_truncate', true) = 'on' THEN
            RETURN OLD;
        END IF;
        RAISE EXCEPTION 'Table % is append-only; UPDATE and DELETE operations are forbidden.', TG_TABLE_NAME;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_prevent_modify_status_history
    BEFORE UPDATE OR DELETE ON status_history
    FOR EACH ROW EXECUTE FUNCTION prevent_modifications_on_append_only();
    """)

    op.execute("""
    CREATE TRIGGER trg_prevent_modify_audit_logs
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION prevent_modifications_on_append_only();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_modify_audit_logs ON audit_logs")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_modify_status_history ON status_history")
    op.execute("DROP FUNCTION IF EXISTS prevent_modifications_on_append_only")

    op.drop_table("audit_logs")
    op.drop_table("notifications")
    op.drop_table("complaint_relations")
    op.drop_table("complaint_notes")
    op.drop_table("status_history")
    op.drop_table("case_assignments")
    op.drop_table("complaints")
    op.drop_table("reference_counters")
    op.drop_table("institutions")
    op.drop_table("users")
    op.drop_table("bureaus")
