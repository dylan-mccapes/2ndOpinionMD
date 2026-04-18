"""Add ehr.patient_artifacts table for HIPAA-compliant raw document storage

Revision ID: 008
Revises: 007
Create Date: 2026-04-17

Stores the original uploaded bytes + extracted text per patient per artifact.
This row is the compliance record; the PTV graph JSON in ehr.patient_graph_vision
is the reasoning record.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    ehr_tables = inspector.get_table_names(schema="ehr")

    if "patient_artifacts" not in ehr_tables:
        op.create_table(
            "patient_artifacts",
            sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True, nullable=False),
            sa.Column("patient_id", sa.Text(), nullable=False),
            sa.Column("artifact_id", sa.Text(), nullable=False),
            sa.Column("filename", sa.Text(), nullable=False),
            sa.Column("mime_type", sa.Text(), nullable=True),
            sa.Column("size_bytes", sa.BigInteger(), nullable=True),
            sa.Column("document_type", sa.Text(), nullable=True),
            sa.Column("document_date", sa.Text(), nullable=True),
            sa.Column("user_notes", sa.Text(), nullable=True),
            sa.Column("content_sha", sa.Text(), nullable=True),
            sa.Column("text_content", sa.Text(), nullable=True),   # extracted UTF-8 text
            sa.Column("raw_bytes", sa.LargeBinary(), nullable=True),  # original file bytes
            sa.Column("uploaded_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
            schema="ehr",
        )
        # artifact_id is unique per patient
        op.create_index(
            "ix_patient_artifacts_patient_artifact",
            "patient_artifacts",
            ["patient_id", "artifact_id"],
            unique=True,
            schema="ehr",
        )
        # fast lookup by patient
        op.create_index(
            "ix_patient_artifacts_patient",
            "patient_artifacts",
            ["patient_id"],
            schema="ehr",
        )
        # GIN full-text index for recall queries
        op.execute(
            """
            CREATE INDEX ix_patient_artifacts_fts
                ON ehr.patient_artifacts
                USING GIN (to_tsvector('english', coalesce(text_content, '') || ' ' || coalesce(filename, '')))
                WHERE text_content IS NOT NULL OR filename IS NOT NULL
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    ehr_tables = inspector.get_table_names(schema="ehr")
    if "patient_artifacts" in ehr_tables:
        op.drop_table("patient_artifacts", schema="ehr")
