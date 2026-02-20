"""Add user_type to users (Phase 5c: Patient & Doctor portals)

Revision ID: 003
Revises: 002
Create Date: 2026-02-20

Adds user_type column for role-based routing: 'patient' | 'doctor'
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("users")}
    if "user_type" not in columns:
        op.add_column(
            "users",
            sa.Column("user_type", sa.String(20), nullable=False, server_default="patient"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("users")}
    if "user_type" in columns:
        op.drop_column("users", "user_type")
