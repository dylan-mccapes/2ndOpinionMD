#!/usr/bin/env python
"""
Ingest the 2022 ACC/AHA/HFSA Guideline for the Management of Heart Failure
into rag_corpus, one row per PDF page.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, List

from pypdf import PdfReader
import psycopg

PDF_PATH = Path("data/guidelines/acc-aha-hfsa-hf-2022.pdf")
SOURCE = "acc_aha_hfsa_hf_2022"
BASE_URL = "https://www.ahajournals.org/doi/pdf/10.1161/CIR.0000000000001062"
GUIDELINE_TITLE = "2022 ACC/AHA/HFSA Guideline for the Management of Heart Failure"


def extract_pages(pdf_path: Path) -> List[Dict[str, Any]]:
    """Return one row per page. Never return an empty list silently."""
    reader = PdfReader(str(pdf_path))
    rows: List[Dict[str, Any]] = []

    n_pages = len(reader.pages)
    print(f"[HF2022] PDF has {n_pages} pages")

    for idx, page in enumerate(reader.pages, start=1):
        raw_text = (page.extract_text() or "").strip()

        if not raw_text:
            # Don’t drop the page; keep a placeholder so it’s queryable
            raw_text = f"[PAGE {idx}: no extractable text – likely figure/table-heavy]"

        meta = {
            "url": BASE_URL,
            "page": idx,
            "year": 2022,
            "topic": "heart_failure",
            "society": "ACC/AHA/HFSA",
            "file_name": pdf_path.name,
            "guideline_source": SOURCE,
        }

        rows.append(
            {
                "source": SOURCE,
                "source_id": f"{SOURCE}:p{idx:04d}",
                "title": f"{GUIDELINE_TITLE} – page {idx}",
                # canonical text; also mirrored into rag_corpus.text
                "text": raw_text,
                "meta": json.dumps(meta),
            }
        )

    print(f"[HF2022] extract_pages generated {len(rows)} rows")
    if len(rows) == 0:
        print("[HF2022] WARNING: 0 rows generated from PDF – something is wrong.")
    else:
        # Show a little sample for sanity
        sample = rows[0]
        print(
            "[HF2022] sample row:",
            sample["source_id"],
            "| title:",
            sample["title"],
            "| text_prefix:",
            sample["text"][:80].replace("\n", " "),
        )

    return rows


def main() -> None:
    if not PDF_PATH.exists():
        raise SystemExit(
            f"PDF not found at {PDF_PATH}. "
            "Download it first via browser and save it to that path."
        )

    dsn = os.getenv("SYNC_DATABASE_URL", "postgresql://localhost/2ndopinionmd")
    print(f"[HF2022] Connecting to DB: {dsn}")
    conn = psycopg.connect(dsn)
    cur = conn.cursor()

    rows = extract_pages(PDF_PATH)
    if not rows:
        print("[HF2022] No rows to insert; aborting without touching rag_corpus.")
        conn.close()
        return

    total = 0
    batch_size = 50

    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        cur.executemany(
            """
            INSERT INTO rag_corpus (source, source_id, title, content, meta, text)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (source, source_id) DO UPDATE
              SET title   = EXCLUDED.title,
                  content = EXCLUDED.content,
                  meta    = EXCLUDED.meta,
                  text    = EXCLUDED.text
            """,
            [
                (
                    row["source"],
                    row["source_id"],
                    row["title"],
                    row["text"],  # content
                    row["meta"],
                    row["text"],  # text (NOT NULL)
                )
                for row in batch
            ],
        )
        total += len(batch)
        print(f"[HF2022] ...inserted/updated {total} HF 2022 pages")

    conn.commit()
    cur.close()
    conn.close()
    print(
        f"[HF2022] Done. Inserted/updated ~{total} "
        "ACC/AHA/HFSA HF 2022 guideline pages."
    )


if __name__ == "__main__":
    main()