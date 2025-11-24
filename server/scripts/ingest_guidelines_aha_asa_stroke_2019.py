#!/usr/bin/env python
"""
Ingest the 2019 AHA/ASA Guideline for the Early Management of Patients
With Acute Ischemic Stroke into rag_corpus, one row per PDF page.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, Iterator

from pypdf import PdfReader
import psycopg

PDF_PATH = Path("data/guidelines/aha_asa_stroke_2019_acute.pdf")
SOURCE = "aha_asa_stroke_2019_acute"
BASE_URL = "https://www.ahajournals.org/doi/10.1161/STR.0000000000000211"
GUIDELINE_TITLE = "AHA/ASA 2019 Acute Ischemic Stroke Guideline"


def extract_pages(pdf_path: Path) -> Iterator[Dict[str, Any]]:
    reader = PdfReader(str(pdf_path))
    n_pages = len(reader.pages)
    print(f"[STROKE2019] PDF has {n_pages} pages")

    for idx, page in enumerate(reader.pages, start=1):
        # Raw text from pypdf
        raw_text = (page.extract_text() or "").strip()

        # If there is *absolutely nothing*, skip the page
        if not raw_text:
            print(f"[STROKE2019] Skipping page {idx}: no extractable text")
            continue

        meta = {
            "url": BASE_URL,
            "page": idx,
            "year": 2019,
            "topic": "acute_ischemic_stroke",
            "society": "AHA/ASA",
            "file_name": pdf_path.name,
            "guideline_source": SOURCE,
        }

        yield {
            "source": SOURCE,
            "source_id": f"{SOURCE}:p{idx:04d}",
            "title": f"{GUIDELINE_TITLE} – page {idx}",
            # IMPORTANT: this maps to rag_corpus.text (NOT NULL)
            "text": raw_text,
            "meta": json.dumps(meta),
            # Keep raw_text for future debugging / alt tokenization
            "raw_text": raw_text,
        }


def main() -> None:
    if not PDF_PATH.exists():
        raise SystemExit(
            f"[STROKE2019] PDF not found at {PDF_PATH}. "
            "Download it first (browser or make target)."
        )

    dsn = os.getenv("SYNC_DATABASE_URL", "postgresql://localhost/2ndopinionmd")
    print(f"[STROKE2019] Connecting to DB: {dsn}")

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        rows = list(extract_pages(PDF_PATH))
        print(f"[STROKE2019] extract_pages generated {len(rows)} rows")

        if not rows:
            print("[STROKE2019] No rows to insert; aborting.")
            return

        # Optional: show a sample row for sanity
        sample = rows[0]
        print(
            "[STROKE2019] sample row:",
            sample["source_id"],
            "| title:",
            sample["title"],
            "| text_prefix:",
            sample["text"][:80].replace("\n", " "),
        )

        total = 0
        for start in range(0, len(rows), 50):
            batch = rows[start : start + 50]
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
                        row["source"],
                        row["source_id"],
                        row["title"],
                        row["text"],
                        row["meta"],
                    )
                    for row in batch
                ],
            )
            total += len(batch)
            print(f"[STROKE2019] ...inserted/updated {total} stroke 2019 pages")


if __name__ == "__main__":
    main()