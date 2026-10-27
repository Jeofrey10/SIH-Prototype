"""Add handover, waiting_on_ledger, and issue_threads.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-27 22:45:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add handover_status to complaints
    op.add_column(
        "complaints",
        sa.Column("handover_status", sa.String(20), nullable=True),
    )

    # 2. Create handovers table
    op.create_table(
        "handovers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("complaint_id", UUID(as_uuid=True), sa.ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("from_bureau_id", UUID(as_uuid=True), sa.ForeignKey("bureaus.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("to_bureau_id", UUID(as_uuid=True), sa.ForeignKey("bureaus.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("target_owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("initiated_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("initiated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("context_summary", sa.Text(), nullable=False),
        sa.Column("key_findings", sa.Text(), nullable=True),
        sa.Column("responded_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("return_reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_handovers_complaint_id", "handovers", ["complaint_id"])
    op.create_index("ix_handovers_status", "handovers", ["status"])

    # 3. Create waiting_on_ledger table
    op.create_table(
        "waiting_on_ledger",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("complaint_id", UUID(as_uuid=True), sa.ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("waiting_on_type", sa.String(40), nullable=False),
        sa.Column("waiting_on_party", sa.String(255), nullable=False),
        sa.Column("since", sa.DateTime(timezone=True), nullable=False),
        sa.Column("chaser_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_waiting_on_ledger_complaint_id", "waiting_on_ledger", ["complaint_id"])
    op.create_index("ix_waiting_on_ledger_is_resolved", "waiting_on_ledger", ["is_resolved"])

    # 4. Create issue_threads table
    op.create_table(
        "issue_threads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("brief", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 5. Add thread_id to complaint_relations
    op.add_column(
        "complaint_relations",
        sa.Column("thread_id", UUID(as_uuid=True), sa.ForeignKey("issue_threads.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_complaint_relations_thread_id", "complaint_relations", ["thread_id"])


def downgrade() -> None:
    op.drop_index("ix_complaint_relations_thread_id", table_name="complaint_relations")
    op.drop_column("complaint_relations", "thread_id")
    op.drop_table("issue_threads")
    op.drop_index("ix_waiting_on_ledger_is_resolved", table_name="waiting_on_ledger")
    op.drop_index("ix_waiting_on_ledger_complaint_id", table_name="waiting_on_ledger")
    op.drop_table("waiting_on_ledger")
    op.drop_index("ix_handovers_status", table_name="handovers")
    op.drop_index("ix_handovers_complaint_id", table_name="handovers")
    op.drop_table("handovers")
    op.drop_column("complaints", "handover_status")
