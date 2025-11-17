# server/scripts/ingest_ra_guidelines.py

import os
import sys
import uuid
from pathlib import Path
from typing import Iterable

import psycopg2
from psycopg2.extras import execute_batch

# If you have a shared config module, import from there:
PG_DSN = os.environ.get("PG_DSN", "dbname=2ndopinionmd")

DATA_DIR = Path("data/ra_guidelines")


def chunk_text(text: str, max_chars: int = 1500) -> Iterable[str]:
    # Replace with your existing chunker if you have one.
    text = text.replace("\r", " ").replace("\n", " ")
    words = text.split()
    buf = []
    buf_len = 0
    for w in words:
        if buf_len + len(w) + 1 > max_chars and buf:
            yield " ".join(buf)
            buf = []
            buf_len = 0
        buf.append(w)
        buf_len += len(w) + 1
    if buf:
        yield " ".join(buf)


def extract_text_from_pdf(pdf_path: Path) -> str:
    # Reuse whatever you used for VA/NICE. Example with pdfplumber:
    import pdfplumber

    out = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            out.append(text)
    return "\n".join(out)


def main():
    conn = psycopg2.connect(PG_DSN)
    cur = conn.cursor()

    for pdf in sorted(DATA_DIR.glob("*.pdf")):
        doc_id = pdf.stem  # e.g., "acr_ra_2021_treatment"
        print(f"Ingesting {pdf} as doc_id={doc_id}")
        full_text = extract_text_from_pdf(pdf)

        chunks = list(chunk_text(full_text))
        rows = []
        for idx, chunk in enumerate(chunks):
            rows.append(
                (
                    "ra_guidelines",  # source
                    doc_id,
                    idx,
                    chunk,
                )
            )

        execute_batch(
            cur,
            """
            INSERT INTO rag_corpus (source, doc_id, chunk_id, text)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            rows,
        )
        conn.commit()

    cur.close()
    conn.close()


if __name__ == "__main__":
    sys.exit(main())

