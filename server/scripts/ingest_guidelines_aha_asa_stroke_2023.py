#!/usr/bin/env python
import os
import json
from pathlib import Path

import psycopg
from pypdf import PdfReader

# Repo root
BASE_DIR = Path(__file__).resolve().parents[2]
GUIDE_DIR = BASE_DIR / "data" / "guidelines"

SYNC_DATABASE_URL = os.getenv(
    "SYNC_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd"),
)

STROKE_2023 = {
    "source": "aha_asa_stroke_2023",
    "file": "aha-asa-stroke-2023.pdf",
    "title_prefix": "AHA/ASA Guideline for the Early Management of Patients With Acute Ischemic Stroke",
    "topic": "acute_ischemic_stroke",
    "society": "AHA/ASA",
    "year": 2023,
    "url": "https://www.ahajournals.org/doi/pdf/10.1161/STR.0000000000000406",
}


def extract_pages(doc_cfg: dict):
    pdf_path = GUIDE_DIR / doc_cfg["file"]
    if not pdf_path.exists():
        raise FileNotFoundError(f"Missing AHA/ASA stroke PDF: {pdf_path}")

    reader = PdfReader(str(pdf_path))
    for idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if not text:
            continue

        title = f"{doc_cfg['title_prefix']} – page {idx}"
        meta = {
            "guideline_source": doc_cfg["source"],
            "file_name": doc_cfg["file"],
            "page": idx,
            "topic": doc_cfg["topic"],
            "society": doc_cfg["society"],
            "year": doc_cfg["year"],
            "url": doc_cfg["url"],
        }

        yield {
            "source": doc_cfg["source"],
            "source_id": f"{doc_cfg['source']}:p{idx:04d}",
            "title": title,
            "text": text,
            "meta": meta,
        }


def main():
    conn = psycopg.connect(SYNC_DATABASE_URL, autocommit=True)
    cur = conn.cursor()

    sql = """
        INSERT INTO rag_corpus (source, source_id, title, text, meta, ts)
        VALUES (%(source)s, %(source_id)s, %(title)s, %(text)s, %(meta)s::jsonb,
                to_tsvector('english', %(ts_body)s))
        ON CONFLICT (source, source_id) DO UPDATE
        SET title = EXCLUDED.title,
            text  = EXCLUDED.text,
            meta  = EXCLUDED.meta,
            ts    = EXCLUDED.ts;
    """

    total = 0
    for row in extract_pages(STROKE_2023):
        ts_body = f"{row['title']}\n\n{row['text']}"
        params = {
            "source": row["source"],
            "source_id": row["source_id"],
            "title": row["title"],
            "text": row["text"],
            "meta": json.dumps(row["meta"]),
            "ts_body": ts_body,
        }
        cur.execute(sql, params)
        total += 1
        if total % 50 == 0:
            print(f"...inserted/updated {total} AHA/ASA stroke pages")

    print(f"Done. Inserted/updated ~{total} AHA/ASA stroke guideline pages.")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
