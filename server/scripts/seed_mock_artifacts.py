#!/usr/bin/env python3
"""
seed_mock_artifacts.py — ingest the four vault fixture files into
ehr.patient_artifacts + ehr.patient_artifact_embeddings for a given user.

Usage (from repo root, in the server venv):
    python server/scripts/seed_mock_artifacts.py --email patient@example.com

The script:
  1. Looks up the user by email.
  2. Reads each fixture file from fixtures/vault_upload_samples/.
  3. Upserts a row into ehr.patient_artifacts (raw bytes + text_content).
  4. Adds a lightweight patient_artifact event to the user's PTV vision.
  5. Computes a sentence-transformers embedding and saves it to the
     ehr.patient_artifact_embeddings store.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# ── repo root on sys.path ────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "server"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("seed_mock_artifacts")

FIXTURES_DIR = REPO_ROOT / "fixtures" / "vault_upload_samples"

MOCK_ARTIFACTS = [
    {
        "path": FIXTURES_DIR / "lab_results_sample.txt",
        "document_type": "lab",
        "document_date": "2025-02-01",
        "notes": "Synthetic CBC + CMP panel",
    },
    {
        "path": FIXTURES_DIR / "cardiology_consult_note.txt",
        "document_type": "note",
        "document_date": "2025-11-14",
        "notes": "Cardiology consultation for exertional chest tightness",
    },
    {
        "path": FIXTURES_DIR / "mri_brain_imaging_report.txt",
        "document_type": "imaging",
        "document_date": "2025-09-03",
        "notes": "MRI brain 3T w/ & w/o contrast",
    },
    {
        "path": FIXTURES_DIR / "medication_summary.txt",
        "document_type": "prescription",
        "document_date": "2025-12-01",
        "notes": "Active medication list",
    },
    {
        "path": FIXTURES_DIR / "symptom_diary_cardio.txt",
        "document_type": "note",
        "document_date": "2025-11-10",
        "notes": "Patient symptom diary Oct–Nov 2025",
    },
]


async def main(email: str, db_url: Optional[str] = None) -> None:
    import asyncpg
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text

    raw_url = db_url or os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://2ndopinionmd@localhost:5432/2ndopinionmd",
    )
    asyncpg_dsn = raw_url.replace("postgresql+asyncpg://", "postgresql://")

    pool = await asyncpg.create_pool(dsn=asyncpg_dsn, min_size=1, max_size=5, command_timeout=60)

    # ── Resolve user id ───────────────────────────────────────────────────────
    row = await pool.fetchrow("SELECT id FROM public.users WHERE email = $1", email)
    if not row:
        logger.error("User '%s' not found. Register first.", email)
        await pool.close()
        sys.exit(1)
    patient_id = str(row["id"])
    logger.info("Found user %s → patient_id=%s", email, patient_id)

    # ── Ensure embeddings table ───────────────────────────────────────────────
    from server.eoh.artifact_embeddings import ensure_embeddings_table, embed_and_store_artifact
    await ensure_embeddings_table(pool)

    # ── Ensure PTV row ────────────────────────────────────────────────────────
    from server.eoh.ptv_journal_bridge import ensure_user_ptv_row, add_patient_artifact_event
    await ensure_user_ptv_row(pool, patient_id)

    # ── Ingest each fixture ───────────────────────────────────────────────────
    for spec in MOCK_ARTIFACTS:
        fpath: Path = spec["path"]
        if not fpath.exists():
            logger.warning("Fixture missing: %s — skipping", fpath)
            continue

        raw_bytes = fpath.read_bytes()
        text_content = raw_bytes.decode("utf-8", errors="replace")
        sha = hashlib.sha256(raw_bytes).hexdigest()
        artifact_id = f"art_{sha[:16]}"
        filename = fpath.name
        doc_type = spec["document_type"]
        doc_date = spec["document_date"]
        notes = spec["notes"]

        logger.info("Ingesting %s (artifact_id=%s)…", filename, artifact_id)

        # 1. patient_artifacts row
        try:
            await pool.execute(
                """
                INSERT INTO ehr.patient_artifacts
                    (patient_id, artifact_id, filename, mime_type, size_bytes,
                     document_type, document_date, user_notes, content_sha,
                     text_content, raw_bytes)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                ON CONFLICT (patient_id, artifact_id) DO UPDATE
                  SET text_content = EXCLUDED.text_content,
                      updated_at   = EXCLUDED.uploaded_at
                """,
                patient_id, artifact_id, filename, "text/plain", len(raw_bytes),
                doc_type, doc_date, notes, sha,
                text_content[:500_000], raw_bytes,
            )
        except Exception as e:
            # column updated_at may not exist — upsert without it
            try:
                await pool.execute(
                    """
                    INSERT INTO ehr.patient_artifacts
                        (patient_id, artifact_id, filename, mime_type, size_bytes,
                         document_type, document_date, user_notes, content_sha,
                         text_content, raw_bytes)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                    ON CONFLICT (patient_id, artifact_id) DO NOTHING
                    """,
                    patient_id, artifact_id, filename, "text/plain", len(raw_bytes),
                    doc_type, doc_date, notes, sha,
                    text_content[:500_000], raw_bytes,
                )
            except Exception as e2:
                logger.error("patient_artifacts insert failed for %s: %s", filename, e2)
                continue

        # 2. PTV event
        try:
            result = await add_patient_artifact_event(
                pool,
                patient_id,
                filename=filename,
                content_type="text/plain",
                size_bytes=len(raw_bytes),
                document_type=doc_type,
                document_date=doc_date,
                notes=notes,
                text_snippet=text_content[:2000],
                content_sha256=sha,
                raw_bytes=raw_bytes,
            )
            logger.info("  PTV event_id=%s is_duplicate=%s", result["event_id"], result["is_duplicate"])
        except Exception as e:
            logger.warning("  PTV upsert failed (non-fatal): %s", e)

        # 3. Embedding
        try:
            await embed_and_store_artifact(
                pool,
                patient_id,
                artifact_id=artifact_id,
                filename=filename,
                document_type=doc_type,
                document_date=doc_date,
                text_content=text_content[:4000],
            )
            logger.info("  Embedding stored for %s", artifact_id)
        except Exception as e:
            logger.warning("  Embedding failed (non-fatal): %s", e)

    logger.info("Seeding complete.")
    await pool.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed mock vault artifacts for a user")
    parser.add_argument("--email", required=True, help="Patient email address")
    parser.add_argument("--db-url", default=None, help="Override DATABASE_URL")
    args = parser.parse_args()
    asyncio.run(main(args.email, args.db_url))
