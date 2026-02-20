"""Add doctor_patient_invites table (Phase 6: Connection invite flow)

Revision ID: 005
Revises: 004
Create Date: 2026-02-20

Stores pending and accepted invites between doctors and patients.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if "doctor_patient_invites" not in tables:
        op.create_table(
            "doctor_patient_invites",
            sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
            sa.Column("from_user_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("to_email", sa.String(), nullable=False),
            sa.Column("invite_type", sa.String(30), nullable=False),
            sa.Column("token", sa.String(), nullable=False, unique=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if "doctor_patient_invites" in tables:
        op.drop_table("doctor_patient_invites")
