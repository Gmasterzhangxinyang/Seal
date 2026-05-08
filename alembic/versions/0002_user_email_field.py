"""add email and created_at to users

Revision ID: 0002_user_email
Revises: 0001_initial
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_user_email'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('email', sa.String(100), nullable=False, server_default=''))
    op.add_column('users', sa.Column('created_at', sa.String(30), nullable=False, server_default=''))
    op.create_unique_constraint('uq_users_email', 'users', ['email'])


def downgrade() -> None:
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_column('users', 'created_at')
    op.drop_column('users', 'email')
