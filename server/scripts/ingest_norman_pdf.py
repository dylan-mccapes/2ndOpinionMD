#!/usr/bin/env python3
"""
Ingest a decrypted patient PDF into ``ehr.patient_timeline`` with GPT-4.1
graph enrichment at every batch.

Historically this script pointed at a file and patient_id that contained
the patient's name ("NormanEricRoberts_decrypted.pdf" /
``PATIENT_ID = "NORMAN_ROBERTS"``). That is a PHI leak: the filename is
shown in ``metadata.last_pdf_ingest``, and the patient_id becomes the
primary key in ``ehr.patient_timeline``. Both are now derived, not
literal:

  - ``PDF_PATH`` defaults to ``data/patient_timelines/source.pdf`` but
    can be overridden with ``--pdf`` or the ``PATIENT_PDF`` env var.
  - ``PATIENT_ID`` is a SHA-256 hash of the PDF bytes (first 16 hex
    chars, prefixed with ``P-`` for readability) unless the caller
    passes ``--patient-id`` explicitly. Never hard-code a name.

Run from 2ndOpinionMD-MVP/:
    python server/scripts/ingest_norman_pdf.py --pdf path/to/file.pdf

Flags:
    --pdf PATH          Path to the decrypted patient PDF (overrides env)
    --patient-id ID     Use this patient_id instead of hashing the PDF
    --no-enrich         Skip GPT-4.1 graph enrichment (fast mode, regex only)
"""
import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
for name in (".pulse", ".env"):
    p = project_root / name
    if p.is_file():
        load_dotenv(p)
        break
for name in (".pulse", ".env"):
    p = project_root / "server" / name
    if p.is_file():
        load_dotenv(p)
        break

DEFAULT_PDF = project_root / "data" / "patient_timelines" / "source.pdf"


def _pdf_hash_id(pdf_bytes: bytes) -> str:
    """Derive a non-identifying, deterministic patient_id from file bytes."""
    return "P-" + hashlib.sha256(pdf_bytes).hexdigest()[:16]


async def main(
    enable_enrichment: bool = True,
    pdf_path: Path | None = None,
    patient_id: str | None = None,
):
    from sqlalchemy import text as sa_text
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from server.timeline.ingest import run_ingest_from_pdf_bytes

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(name)-40s  %(levelname)-7s  %(message)s",
    )

    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://2ndopinionmd@localhost:5432/2ndopinionmd")
    if "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(db_url)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    pdf_path = pdf_path or Path(os.getenv("PATIENT_PDF", str(DEFAULT_PDF)))
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        sys.exit(1)

    pdf_bytes = pdf_path.read_bytes()
    resolved_patient_id = patient_id or _pdf_hash_id(pdf_bytes)
    # Deliberately do not log the source filename — it may contain PHI.
    print(f"\nRead {len(pdf_bytes):,} bytes (sha256/16 -> patient_id={resolved_patient_id})")
    print(f"Graph enrichment: {'ENABLED (GPT-4.1)' if enable_enrichment else 'DISABLED (regex only)'}")

    async with SessionLocal() as session:
        result = await session.execute(
            sa_text("DELETE FROM ehr.patient_timeline WHERE patient_id = :pid"),
            {"pid": resolved_patient_id},
        )
        deleted = result.rowcount
        await session.commit()
        if deleted:
            print(f"Cleared {deleted} old timeline events for {resolved_patient_id}")

        stats = await run_ingest_from_pdf_bytes(
            db=session,
            pdf_bytes=pdf_bytes,
            patient_id=resolved_patient_id,
            password=None,
            enable_graph_enrichment=enable_enrichment,
        )

        print(f"\n{'='*70}")
        print(f"  INGESTION STATS")
        print(f"{'='*70}")
        print(f"  events stored:    {stats['events_stored']}")
        print(f"  total pages:      {stats['total_pages']}")
        print(f"  pages with text:  {stats['pages_with_text']}")
        print(f"  batches:          {stats['batches']}")
        print(f"  elapsed:          {stats['elapsed_ms']:,}ms")

        if stats.get("enrichment_stats"):
            print(f"\n  ENRICHMENT PER BATCH:")
            total_events = 0
            total_edges = 0
            for es in stats["enrichment_stats"]:
                total_events += es.get("events_extracted", 0)
                total_edges += es.get("edges_extracted", 0)
                err = es.get("error")
                status = "ERROR" if err else "OK"
                print(
                    f"    batch {es['batch_index']+1} "
                    f"pages={es['page_range']}  "
                    f"events={es.get('events_extracted', 0)}  "
                    f"edges={es.get('edges_extracted', 0)}  "
                    f"time={es.get('elapsed_ms', 0):,}ms  "
                    f"[{status}]"
                )
            print(f"  TOTAL enrichment: {total_events} events, {total_edges} edges")

        vision = stats.get("vision")
        if vision:
            print(f"\n  FINAL GRAPH:")
            print(f"    events: {len(vision.events)}")
            print(f"    edges:  {vision.count_edges()}")

            by_type = {}
            for ev in vision.events.values():
                by_type[ev.event_type] = by_type.get(ev.event_type, 0) + 1
            for etype, cnt in sorted(by_type.items(), key=lambda x: -x[1]):
                print(f"      {etype}: {cnt}")

        print(f"{'='*70}")

    await engine.dispose()
    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest a patient PDF with graph enrichment")
    parser.add_argument("--pdf", type=Path, default=None,
                        help="Path to the decrypted patient PDF (overrides $PATIENT_PDF)")
    parser.add_argument("--patient-id", type=str, default=None,
                        help="Use this patient_id instead of hashing the PDF bytes")
    parser.add_argument("--no-enrich", action="store_true", help="Skip GPT-4.1 graph enrichment")
    args = parser.parse_args()
    asyncio.run(main(
        enable_enrichment=not args.no_enrich,
        pdf_path=args.pdf,
        patient_id=args.patient_id,
    ))
