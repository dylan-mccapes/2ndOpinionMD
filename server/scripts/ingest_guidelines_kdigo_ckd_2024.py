#!/usr/bin/env python
import os
import json
from pathlib import Path

import psycopg
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parents[2]  # repo root
GUIDE_DIR = BASE_DIR / "data" / "guidelines"

SYNC_DATABASE_URL = os.getenv(
    "SYNC_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd"),
)

KDIGO_CKD_2024 = {
    "source": "kdigo_ckd_2024",
    "file": "kdigo-2024-ckd.pdf",
    "title_prefix": "KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease",
    "topic": "chronic_kidney_disease",
    "society": "KDIGO",
    "year": 2024,
    # If wget 403s you can still download via browser and keep this URL for meta
    "url": "https://kdigo.org/wp-content/uploads/2024/03/KDIGO-2024-CKD-Guideline.pdf",
}


def extract_pages(doc_cfg):
    pdf_path = GUIDE_DIR / doc_cfg["file"]
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

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
    for row in extract_pages(KDIGO_CKD_2024):
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
            print(f"...inserted/updated {total} KDIGO CKD 2024 pages")

    print(f"Done. Inserted/updated ~{total} KDIGO CKD 2024 guideline pages.")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
