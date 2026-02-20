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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("users")}
    if "doctor_id" not in columns:
        op.add_column(
            "users",
            sa.Column("doctor_id", sa.UUID(), nullable=True),
        )

    fks = {fk.get("name") for fk in inspector.get_foreign_keys("users")}
    if "users_doctor_id_fkey" not in fks:
        op.create_foreign_key(
            "users_doctor_id_fkey",
            "users",
            "users",
            ["doctor_id"],
            ["id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    fks = {fk.get("name") for fk in inspector.get_foreign_keys("users")}
    if "users_doctor_id_fkey" in fks:
        op.drop_constraint("users_doctor_id_fkey", "users", type_="foreignkey")

    columns = {c["name"] for c in inspector.get_columns("users")}
    if "doctor_id" in columns:
        op.drop_column("users", "doctor_id")
