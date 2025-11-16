#!/usr/bin/env python
"""
Ingest NICE guideline PDFs into rag_corpus as source='nice'.

Usage examples (from repo root, with venv active):

  python server/scripts/ingest_nice_guidelines.py \
    --pdf-path data/guidelines/nice/nice_ng106_full.pdf \
    --guideline-id NG106 \
    --guideline-title "NICE NG106 Chronic heart failure in adults: diagnosis and management"

  python server/scripts/ingest_nice_guidelines.py \
    --pdf-path data/guidelines/nice/nice_ng28_full.pdf \
    --guideline-id NG28 \
    --guideline-title "NICE NG28 Type 2 diabetes in adults: management"

Environment:

  - OPENAI_API_KEY      : your OpenAI API key (already used elsewhere)
  - RAG_EMBED_MODEL     : embedding model name (must match rag_corpus dimension),
                          e.g. "text-embedding-3-large"
  - DATABASE_URL        : psycopg2 DSN (optional, defaults to "dbname=2ndopinionmd")

Schema expectation:

  rag_corpus(
      id         bigserial primary key,
      source     text,
      title      text,
      text       text,
      meta       jsonb,
      embedding  vector
  )
"""

import argparse
import json
import os
from typing import List, Dict

import psycopg2
from openai import OpenAI
from pypdf import PdfReader

# --- Config -------------------------------------------------------------------

DEFAULT_DB_DSN = os.getenv("DATABASE_URL", "dbname=2ndopinionmd")
EMBED_MODEL = os.getenv("RAG_EMBED_MODEL", "text-embedding-3-small")
EMBED_DIMS = 1536

client = OpenAI()


# --- PDF loading / chunking ---------------------------------------------------


def load_pdf_pages(pdf_path: str) -> List[Dict]:
    """
    Extract text page-by-page from a PDF.

    Returns a list of dicts:
        {
            "page_index": int (0-based),
            "text": str
        }
    """
    reader = PdfReader(pdf_path)
    pages: List[Dict] = []

    for idx, page in enumerate(reader.pages):
        try:
            raw = page.extract_text() or ""
        except Exception as exc:  # pragma: no cover
            print(f"[WARN] Failed to extract page {idx + 1} from {pdf_path}: {exc}")
            raw = ""

        text = raw.replace("\x00", "").strip()
        if not text:
            # Skip empty pages (cover, blank, etc.)
            continue

        pages.append(
            {
                "page_index": idx,
                "text": text,
            }
        )

    print(f"[INFO] Loaded {len(pages)} non-empty pages from {pdf_path}")
    return pages


# --- Embeddings ---------------------------------------------------------------


def embed_texts(texts: List[str]) -> List[List[float]]:
    print(f"[INFO] Requesting {len(texts)} embeddings with model='{EMBED_MODEL}'")
    resp = client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
    )
    vectors = [d.embedding for d in resp.data]

    for i, v in enumerate(vectors):
        if len(v) != EMBED_DIMS:
            raise ValueError(
                f"Embedding dim mismatch for item {i}: got {len(v)}, "
                f"expected {EMBED_DIMS}. Check EMBED_MODEL='{EMBED_MODEL}'."
            )
    return vectors



# --- Database helpers ---------------------------------------------------------


def get_db_connection():
    """
    Create a psycopg2 connection using DATABASE_URL or fallback DSN.
    """
    print(f"[INFO] Connecting to Postgres with DSN: {DEFAULT_DB_DSN!r}")
    conn = psycopg2.connect(DEFAULT_DB_DSN)
    return conn


def vector_to_literal(vec: List[float]) -> str:
    """
    Convert a Python list[float] into a pgvector-compatible string literal.

    Example:
        [0.1, 0.2] -> "[0.10000000,0.20000000]"
    """
    return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"


def upsert_guideline_pages(
    pages: List[Dict],
    embeddings: List[List[float]],
    guideline_id: str,
    guideline_title: str,
    source: str = "nice",
) -> None:
    """
    Insert each page as a row in rag_corpus with source='nice'.

    We don't rely on ON CONFLICT here – if you want idempotency, you can add a
    unique index later on (source, guideline_id, page_index) and adjust the
    INSERT to use ON CONFLICT DO NOTHING.
    """
    if len(pages) != len(embeddings):
        raise ValueError(
            f"pages ({len(pages)}) vs embeddings ({len(embeddings)}) length mismatch"
        )

    conn = get_db_connection()
    inserted = 0

    try:
        with conn:
            with conn.cursor() as cur:
                for page, emb in zip(pages, embeddings):
                    page_index = page["page_index"]
                    text = page["text"]

                    title = (
                        f"{guideline_id} {guideline_title} – page {page_index + 1}"
                    )

                    meta = {
                        "guideline_id": guideline_id,
                        "guideline_title": guideline_title,
                        "page_index": page_index,
                        "publisher": "NICE",
                        "source_type": "guideline",
                    }

                    emb_literal = vector_to_literal(emb)

                    # Simple insert; you can add ON CONFLICT if you later
                    # create a unique constraint / index.
                    cur.execute(
                        """
                        INSERT INTO rag_corpus (source, title, text, meta, embedding)
                        VALUES (%s, %s, %s, %s::jsonb, %s::vector)
                        """,
                        (
                            source,
                            title,
                            text,
                            json.dumps(meta),
                            emb_literal,
                        ),
                    )
                    inserted += 1

        print(
            f"[OK] Inserted {inserted} rows into rag_corpus for guideline {guideline_id}"
        )
    finally:
        conn.close()


# --- CLI ----------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest a NICE guideline PDF into rag_corpus as source='nice'."
    )
    parser.add_argument(
        "--pdf-path",
        required=True,
        help="Path to the NICE PDF (e.g. data/guidelines/nice/nice_ng106_full.pdf)",
    )
    parser.add_argument(
        "--guideline-id",
        required=True,
        help="Short guideline id, e.g. NG106 or NG28.",
    )
    parser.add_argument(
        "--guideline-title",
        required=True,
        help='Human-readable title, e.g. "NICE NG106 Chronic heart failure in adults".',
    )
    parser.add_argument(
        "--source",
        default="nice",
        help="Value to store in rag_corpus.source (default: 'nice').",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    pdf_path = args.pdf_path
    guideline_id = args.guideline_id
    guideline_title = args.guideline_title
    source = args.source

    if not os.path.exists(pdf_path):
        raise SystemExit(f"[ERROR] PDF not found: {pdf_path}")

    print(f"[INFO] Ingesting PDF {pdf_path} as guideline {guideline_id} ({source})")
    print(f"[INFO] Using embedding model: {EMBED_MODEL}")

    pages = load_pdf_pages(pdf_path)
    texts = [p["text"] for p in pages]
    embeddings = embed_texts(texts)
    upsert_guideline_pages(
        pages=pages,
        embeddings=embeddings,
        guideline_id=guideline_id,
        guideline_title=guideline_title,
        source=source,
    )


if __name__ == "__main__":
    main()

