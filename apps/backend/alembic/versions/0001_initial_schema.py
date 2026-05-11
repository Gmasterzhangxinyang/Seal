"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-08
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "personnel",
        sa.Column("id_number", sa.String(20), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("dept", sa.String(100)),
        sa.Column("role", sa.String(50)),
    )

    op.create_table(
        "users",
        sa.Column("username", sa.String(50), primary_key=True),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="operator"),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.String(30), nullable=False),
        sa.Column("operator_id", sa.String(50), nullable=False),
        sa.Column("doc_type", sa.String(50)),
        sa.Column("qr_content", sa.String(500)),
        sa.Column("doc_fields", sa.Text),
        sa.Column("ocr_text", sa.Text),
        sa.Column("result", sa.String(30), nullable=False),
        sa.Column("errors", sa.Text),
        sa.Column("before_img", sa.String(500)),
        sa.Column("after_img", sa.String(500)),
        sa.Column("dms_doc_id", sa.String(100)),
    )

    op.create_table(
        "review_queue",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.String(30), nullable=False),
        sa.Column("operator_id", sa.String(50), nullable=False),
        sa.Column("doc_type", sa.String(50)),
        sa.Column("doc_fields", sa.Text),
        sa.Column("ocr_text", sa.Text),
        sa.Column("warnings", sa.Text),
        sa.Column("image_path", sa.String(500)),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reviewer_id", sa.String(50)),
        sa.Column("resolved_at", sa.String(30)),
        sa.Column("decision", sa.String(20)),
        sa.Column("stamped", sa.Integer, server_default="0"),
    )

    op.create_table(
        "doc_templates",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.Text),
        sa.Column("is_system", sa.Integer, nullable=False, server_default="0"),
        sa.Column("classification_keywords", sa.Text),
        sa.Column("classification_regex", sa.Text),
        sa.Column("created_at", sa.String(30), nullable=False),
        sa.Column("updated_at", sa.String(30), nullable=False),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("requires_stamp", sa.Integer, server_default="1"),
        sa.Column("stamp_position", sa.String(100), server_default=""),
        sa.Column("stamp_keywords", sa.Text),
    )

    op.create_table(
        "template_fields",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "template_id",
            sa.Integer,
            sa.ForeignKey("doc_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("field_label", sa.String(100), nullable=False),
        sa.Column(
            "field_category", sa.String(20), nullable=False, server_default="required"
        ),
        sa.Column("ocr_pattern", sa.Text),
        sa.Column("validation_rule", sa.Text),
        sa.Column("sort_order", sa.Integer, server_default="0"),
    )

    op.create_table(
        "template_examples",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "template_id",
            sa.Integer,
            sa.ForeignKey("doc_templates.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("image_path", sa.String(500), nullable=False),
        sa.Column("generated_at", sa.String(30), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("template_examples")
    op.drop_table("template_fields")
    op.drop_table("doc_templates")
    op.drop_table("review_queue")
    op.drop_table("audit_log")
    op.drop_table("users")
    op.drop_table("personnel")
