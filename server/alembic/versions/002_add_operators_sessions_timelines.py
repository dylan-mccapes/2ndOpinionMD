"""Add operators, sessions, patient_timelines, timeline_access (2OPMD game plan auth)

Revision ID: 002
Revises: 755e5f98fff6
Create Date: 2026-02-01

Game plan: II. AUTHENTICATION SYSTEM (3Pi$73Mic87MLV4UL7)
- operators: one per user (patient/doctor/researcher)
- sessions: active operator sessions (Start Session / Close Session)
- patient_timelines: one per patient operator
- timeline_access: who can see which timelines
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002"
down_revision: Union[str, None] = "755e5f98fff6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Operators: canonical identity for vault/session flow (links to users)
    op.create_table(
        "operators",
        sa.Column("operator_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("operator_type", sa.String(20), nullable=False),  # patient, doctor, researcher
        sa.Column("sovereignty_level", sa.String(20), nullable=False),  # full, shared, observer
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("last_session_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("operator_id"),
        sa.UniqueConstraint("user_id", name="uq_operators_user_id"),
    )
    op.create_index(op.f("ix_operators_user_id"), "operators", ["user_id"], unique=True)
    op.create_index(op.f("ix_operators_operator_type"), "operators", ["operator_type"], unique=False)

    # Sessions: active operator sessions (session_token = JWT or opaque token)
    op.create_table(
        "sessions",
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("operator_id", sa.UUID(), nullable=False),
        sa.Column("session_token", sa.Text(), nullable=False),
        sa.Column("instantiated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("session_metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["operator_id"], ["operators.operator_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index(op.f("ix_sessions_session_token"), "sessions", ["session_token"], unique=True)
    op.create_index(op.f("ix_sessions_operator_id"), "sessions", ["operator_id"], unique=False)
    op.create_index(op.f("ix_sessions_closed_at"), "sessions", ["closed_at"], unique=False)

    # Patient timelines: one per patient operator
    op.create_table(
        "patient_timelines",
        sa.Column("timeline_id", sa.UUID(), nullable=False),
        sa.Column("patient_operator_id", sa.UUID(), nullable=False),
        sa.Column("timeline_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("last_enrichment_at", sa.DateTime(), nullable=True),
        sa.Column("anonymization_consent", sa.Boolean(), server_default="false", nullable=True),
        sa.ForeignKeyConstraint(
            ["patient_operator_id"], ["operators.operator_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("timeline_id"),
        sa.UniqueConstraint("patient_operator_id", name="uq_patient_timelines_operator"),
    )
    op.create_index(
        op.f("ix_patient_timelines_patient_operator_id"),
        "patient_timelines",
        ["patient_operator_id"],
        unique=True,
    )

    # Timeline access: who can see which timelines (for doctor/researcher later)
    op.create_table(
        "timeline_access",
        sa.Column("access_id", sa.UUID(), nullable=False),
        sa.Column("timeline_id", sa.UUID(), nullable=False),
        sa.Column("operator_id", sa.UUID(), nullable=False),
        sa.Column("access_level", sa.String(20), nullable=False),  # owner, editor, viewer, anonymous
        sa.Column("granted_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("granted_by", sa.UUID(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("access_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["timeline_id"], ["patient_timelines.timeline_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["operator_id"], ["operators.operator_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["granted_by"], ["operators.operator_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("access_id"),
    )
    op.create_index(
        op.f("ix_timeline_access_timeline_id"), "timeline_access", ["timeline_id"], unique=False
    )
    op.create_index(
        op.f("ix_timeline_access_operator_id"), "timeline_access", ["operator_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("timeline_access")
    op.drop_table("patient_timelines")
    op.drop_table("sessions")
    op.drop_table("operators")
