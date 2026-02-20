"""Add doctor_id to users (Phase 5c: Doctor–patient linking)

Revision ID: 004
Revises: 003
Create Date: 2026-02-20

Adds doctor_id column for linking patients to their doctor.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("doctor_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "users_doctor_id_fkey",
        "users",
        "users",
        ["doctor_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("users_doctor_id_fkey", "users", type_="foreignkey")
    op.drop_column("users", "doctor_id")
