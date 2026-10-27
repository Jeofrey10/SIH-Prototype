"""Add escalation_recommended to complaints.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-24 22:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column(
        "complaints",
        sa.Column(
            "escalation_recommended",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

def downgrade() -> None:
    op.drop_column("complaints", "escalation_recommended")
