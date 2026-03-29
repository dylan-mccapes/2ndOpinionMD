#!/usr/bin/env python3
"""
Ingest NormanEricRoberts_decrypted.pdf into ehr.patient_timeline
with GPT-4.1 graph enrichment at every batch.

Run from 2ndOpinionMD-MVP/:
    python server/scripts/ingest_norman_pdf.py

Flags:
    --no-enrich   Skip GPT-4.1 graph enrichment (fast mode, regex only)
"""
import argparse
import asyncio
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

PDF_PATH = project_root / "data" / "patient_timelines" / "NormanEricRoberts_decrypted.pdf"
PATIENT_ID = "NORMAN_ROBERTS"


async def main(enable_enrichment: bool = True):
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

    if not PDF_PATH.exists():
        print(f"PDF not found: {PDF_PATH}")
        sys.exit(1)

    pdf_bytes = PDF_PATH.read_bytes()
    print(f"\nRead {len(pdf_bytes):,} bytes from {PDF_PATH.name}")
    print(f"Graph enrichment: {'ENABLED (GPT-4.1)' if enable_enrichment else 'DISABLED (regex only)'}")

    async with SessionLocal() as session:
        result = await session.execute(
            sa_text("DELETE FROM ehr.patient_timeline WHERE patient_id = :pid"),
            {"pid": PATIENT_ID},
        )
        deleted = result.rowcount
        await session.commit()
        if deleted:
            print(f"Cleared {deleted} old timeline events for {PATIENT_ID}")

        stats = await run_ingest_from_pdf_bytes(
            db=session,
            pdf_bytes=pdf_bytes,
            patient_id=PATIENT_ID,
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
    parser = argparse.ArgumentParser(description="Ingest Norman Roberts PDF with graph enrichment")
    parser.add_argument("--no-enrich", action="store_true", help="Skip GPT-4.1 graph enrichment")
    args = parser.parse_args()
    asyncio.run(main(enable_enrichment=not args.no_enrich))
