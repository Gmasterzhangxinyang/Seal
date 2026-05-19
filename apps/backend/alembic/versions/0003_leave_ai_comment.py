"""add ai_comment to leave_applications

Revision ID: 0003_leave_ai_comment
Revises: 0002_user_email
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_leave_ai_comment"
down_revision = "0002_user_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leave_applications",
        sa.Column("ai_comment", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("leave_applications", "ai_comment")