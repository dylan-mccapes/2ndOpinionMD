#!/usr/bin/env python
"""
Ingest the 2025 EULAR recommendations for SLE with kidney involvement
(lupus nephritis) into rag_corpus, one row per PDF page.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, Iterator

from pypdf import PdfReader
import psycopg

PDF_PATH = Path("data/guidelines/eular-2025-sle-nephritis.pdf")
SOURCE = "eular_sle_nephritis_2025"
BASE_URL = "https://www.eular.org/recommendations-management"
GUIDELINE_TITLE = "EULAR 2025 SLE with kidney involvement (lupus nephritis) recommendations"


def extract_pages(pdf_path: Path) -> Iterator[Dict[str, Any]]:
    reader = PdfReader(str(pdf_path))
    num_pages = len(reader.pages)
    print(f"[SLELN2025] PDF has {num_pages} pages")

    for idx, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            # Skip truly empty pages (covers blank pages, pure-figure, etc.)
            print(f"[SLELN2025] Skipping page {idx}: no extractable text")
            continue

        meta = {
            "url": BASE_URL,
            "page": idx,
            "year": 2025,
            "topic": "lupus_nephritis",
            "disease": "SLE",
            "society": "EULAR",
            "file_name": pdf_path.name,
            "guideline_source": SOURCE,
        }

        yield {
            "source_id": f"{SOURCE}:p{idx:04d}",
            "title": f"{GUIDELINE_TITLE} – page {idx}",
            "text": text,
            "meta": json.dumps(meta),
        }


def main() -> None:
    if not PDF_PATH.exists():
        raise SystemExit(
            f"[SLELN2025] PDF not found at {PDF_PATH}. "
            "Download it first (or place the file there)."
        )

    dsn = os.getenv("SYNC_DATABASE_URL", "postgresql://localhost/2ndopinionmd")
    print(f"[SLELN2025] Connecting to DB: {dsn}")
    conn = psycopg.connect(dsn)
    cur = conn.cursor()

    rows = list(extract_pages(PDF_PATH))
    print(f"[SLELN2025] extract_pages generated {len(rows)} rows")

    if not rows:
        print("[SLELN2025] No rows to insert; exiting.")
        return

    # Peek at first row for sanity
    sample = rows[0]
    print(
        f"[SLELN2025] sample row: {sample['source_id']} | "
        f"title: {sample['title']} | "
        f"text_prefix: {sample['text'][:80].replace('\\n', ' ')}"
    )

    total = 0
    BATCH_SIZE = 50

    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        cur.executemany(
            """
            INSERT INTO rag_corpus (source, source_id, title, text, meta)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (source, source_id) DO UPDATE
              SET title = EXCLUDED.title,
                  text  = EXCLUDED.text,
                  meta  = EXCLUDED.meta
            """,
            [
                (
                    SOURCE,
                    row["source_id"],
                    row["title"],
                    row["text"],
                    row["meta"],
                )
                for row in batch
            ],
        )
        total += len(batch)
        print(f"[SLELN2025] ...inserted/updated {total} SLE LN 2025 pages")

    conn.commit()
    cur.close()
    conn.close()
    print(
        f"[SLELN2025] Done. Inserted/updated ~{total} "
        "EULAR 2025 SLE lupus nephritis guideline pages."
    )


if __name__ == "__main__":
    main()
