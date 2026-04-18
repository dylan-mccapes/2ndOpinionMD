"""Add patient_reported_outcomes JSON for FORWARD PRO on journal_entries

Revision ID: 006
Revises: 005
Create Date: 2026-04-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("journal_entries")}
    if "patient_reported_outcomes" not in cols:
        op.add_column(
            "journal_entries",
            sa.Column("patient_reported_outcomes", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("journal_entries")}
    if "patient_reported_outcomes" in cols:
        op.drop_column("journal_entries", "patient_reported_outcomes")
