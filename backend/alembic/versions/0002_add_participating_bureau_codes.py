"""Add participating_bureau_codes to complaints.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-24 21:40:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column(
        "complaints",
        sa.Column(
            "participating_bureau_codes",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
    )

def downgrade() -> None:
    op.drop_column("complaints", "participating_bureau_codes")
