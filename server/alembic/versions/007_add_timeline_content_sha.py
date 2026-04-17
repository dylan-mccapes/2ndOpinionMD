"""Add content_sha + unique index to ehr.patient_timeline for dedup-safe inserts

Revision ID: 007
Revises: 006
Create Date: 2026-04-17

Adds:
  ehr.patient_timeline.content_sha  VARCHAR(64)  NULLABLE (back-filled by app)
  UNIQUE INDEX ux_patient_timeline_dedup ON ehr.patient_timeline
      (patient_id, event_type, content_sha)
      WHERE content_sha IS NOT NULL

We intentionally omit ``ts::date`` from the index: casting ``timestamptz`` to
``date`` is not IMMUTABLE in PostgreSQL (depends on session timezone), so the
index creation fails. The ``content_sha`` already encodes the canonical
coordinate from ``event_dedup.canonical_event_id`` (including calendar day).

Once the index is in place, _store_extracted_events uses:
    INSERT ... ON CONFLICT (patient_id, event_type, content_sha)
      WHERE content_sha IS NOT NULL DO NOTHING
so re-importing the same document never duplicates rows.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Only touch the ehr schema table
    ehr_cols = {
        c["name"]
        for c in inspector.get_columns("patient_timeline", schema="ehr")
    }

    if "content_sha" not in ehr_cols:
        op.add_column(
            "patient_timeline",
            sa.Column("content_sha", sa.String(64), nullable=True),
            schema="ehr",
        )

    # Create unique partial index (WHERE content_sha IS NOT NULL) so rows
    # without a sha (legacy / null) are never blocked.
    existing_indexes = {
        idx["name"]
        for idx in inspector.get_indexes("patient_timeline", schema="ehr")
    }
    if "ux_patient_timeline_dedup" not in existing_indexes:
        op.execute(
            """
            CREATE UNIQUE INDEX ux_patient_timeline_dedup
                ON ehr.patient_timeline (patient_id, event_type, content_sha)
                WHERE content_sha IS NOT NULL
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_indexes = {
        idx["name"]
        for idx in inspector.get_indexes("patient_timeline", schema="ehr")
    }
    if "ux_patient_timeline_dedup" in existing_indexes:
        op.execute("DROP INDEX IF EXISTS ehr.ux_patient_timeline_dedup")

    ehr_cols = {
        c["name"]
        for c in inspector.get_columns("patient_timeline", schema="ehr")
    }
    if "content_sha" in ehr_cols:
        op.drop_column("patient_timeline", "content_sha", schema="ehr")
