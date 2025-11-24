#!/usr/bin/env python
"""
Generic guideline PDF ingester for rag_corpus.

Usage example:

  python server/scripts/ingest_guideline_pdf.py \
    --pdf-path data/guidelines/esmo_mzl_2020.pdf \
    --source esmo_mzl_2020 \
    --guideline-title "ESMO 2020 Marginal Zone Lymphoma Guidelines" \
    --base-url "https://www.esmo.org/guidelines/haematological-malignancies/marginal-zone-lymphomas" \
    --year 2020 \
    --topic marginal_zone_lymphoma \
    --disease SMZL \
    --society ESMO
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterator

from pypdf import PdfReader
import psycopg


def extract_pages(
    pdf_path: Path,
    source: str,
    guideline_title: str,
    base_url: str | None,
    meta_extra: Dict[str, Any],
) -> Iterator[Dict[str, Any]]:
    reader = PdfReader(str(pdf_path))
    num_pages = len(reader.pages)
    print(f"[GUIDE_INGEST] PDF has {num_pages} pages at {pdf_path}")

    for idx, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            print(f"[GUIDE_INGEST] Skipping page {idx}: no extractable text")
            continue

        meta: Dict[str, Any] = {}
        if base_url:
            meta["url"] = base_url
        meta["page"] = idx
        meta["file_name"] = pdf_path.name
        meta["guideline_source"] = source

        # Merge extra metadata (year, topic, disease, society, etc.)
        for k, v in meta_extra.items():
            if v is not None:
                meta[k] = v

        yield {
            "source_id": f"{source}:p{idx:04d}",
            "title": f"{guideline_title} – page {idx}",
            "text": text,
            "meta": json.dumps(meta),
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest a guideline PDF into rag_corpus (one row per page)."
    )
    parser.add_argument(
        "--pdf-path",
        required=True,
        type=Path,
        help="Path to the guideline PDF file",
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Short source name to use in rag_corpus.source (e.g. esmo_mzl_2020)",
    )
    parser.add_argument(
        "--guideline-title",
        required=True,
        help="Human-readable guideline title used in rag_corpus.title",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Canonical URL for the guideline (used in meta['url'])",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Guideline year (stored in meta['year'])",
    )
    parser.add_argument(
        "--topic",
        default=None,
        help="High-level topic (e.g. lupus_nephritis, marginal_zone_lymphoma)",
    )
    parser.add_argument(
        "--disease",
        default=None,
        help="Disease label (e.g. SLE, SMZL, HF, RA)",
    )
    parser.add_argument(
        "--society",
        default=None,
        help="Guideline society (e.g. EULAR, ESMO, ACR, ESC, KDIGO)",
    )
    parser.add_argument(
        "--meta-json",
        default=None,
        help=(
            "Optional JSON string with extra meta fields to merge "
            "(e.g. '{\"region\": \"EU\", \"version\": \"v1\"}')"
        ),
    )

    args = parser.parse_args()

    pdf_path: Path = args.pdf_path
    source: str = args.source
    guideline_title: str = args.guideline_title
    base_url: str | None = args.base_url

    if not pdf_path.exists():
        raise SystemExit(f"[GUIDE_INGEST] PDF not found at {pdf_path}")

    # Build extra meta
    meta_extra: Dict[str, Any] = {
        "year": args.year,
        "topic": args.topic,
        "disease": args.disease,
        "society": args.society,
    }
    if args.meta_json:
        try:
            parsed = json.loads(args.meta_json)
            if isinstance(parsed, dict):
                meta_extra.update(parsed)
            else:
                print("[GUIDE_INGEST] Ignoring meta_json: not a dict")
        except json.JSONDecodeError as e:
            print(f"[GUIDE_INGEST] Failed to parse meta_json: {e}")

    dsn = os.getenv("SYNC_DATABASE_URL", "postgresql://localhost/2ndopinionmd")
    print(f"[GUIDE_INGEST] Connecting to DB: {dsn}")
    conn = psycopg.connect(dsn)
    cur = conn.cursor()

    rows = list(extract_pages(pdf_path, source, guideline_title, base_url, meta_extra))
    print(f"[GUIDE_INGEST] extract_pages generated {len(rows)} rows")

    if not rows:
        print("[GUIDE_INGEST] No rows to insert; exiting.")
        return

    # Peek at first row
    sample = rows[0]
    print(
        f"[GUIDE_INGEST] sample row: {source}:{sample['source_id'].split(':')[-1]} | "
        f"title: {sample['title']} | "
        f"text_prefix: {sample['text'][:80].replace('\\n', ' ')}"
    )

    BATCH_SIZE = 50
    total = 0

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
                    source,
                    row["source_id"],
                    row["title"],
                    row["text"],
                    row["meta"],
                )
                for row in batch
            ],
        )
        total += len(batch)
        print(f"[GUIDE_INGEST] ...inserted/updated {total} rows for {source}")

    conn.commit()
    cur.close()
    conn.close()
    print(
        f"[GUIDE_INGEST] Done. Inserted/updated ~{total} rows for source={source}."
    )


if __name__ == "__main__":
    main()
