#!/usr/bin/env python3
import os, sys, argparse, math
import psycopg2
from psycopg2.extras import execute_values, Json

DATABASE_URL = os.getenv("SYNC_DATABASE_URL", "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd")

def ensure_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS public.rag_corpus_chunks (
          id        BIGSERIAL PRIMARY KEY,
          source    TEXT,
          title     TEXT,
          text      TEXT,
          ts        TSVECTOR,
          meta      JSONB DEFAULT '{}'::jsonb,
          doc_id    BIGINT,
          sect_id   BIGINT,
          parent_id BIGINT
          -- ord might be missing on older installs; we add it below
        );
        """)
        # add ord if the table already existed without it
        cur.execute("ALTER TABLE public.rag_corpus_chunks ADD COLUMN IF NOT EXISTS ord INT;")
        cur.execute("CREATE INDEX IF NOT EXISTS rag_chunks_ts_gin ON public.rag_corpus_chunks USING GIN (ts);")
        cur.execute("CREATE INDEX IF NOT EXISTS rag_chunks_parent  ON public.rag_corpus_chunks (parent_id);")
    conn.commit()

def chunk_text(s, size=3000, overlap=300):
    if not s: return []
    out = []
    i = 0
    n = len(s)
    while i < n:
        out.append(s[i:i+size])
        i += max(size - overlap, 1)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-len", type=int, default=8000, help="chunk rows with length(text) >= min-len")
    ap.add_argument("--sources", default="nice,cks", help="comma-separated sources to include")
    ap.add_argument("--doc-key", help="optional: only chunk a specific doc_key")
    ap.add_argument("--size", type=int, default=3000)
    ap.add_argument("--overlap", type=int, default=300)
    args = ap.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    ensure_table(conn)

    srcs = [s.strip() for s in args.sources.split(",") if s.strip()]

    base = """
      SELECT rc.id, rc.source, rc.title, rc.text, rc.meta, rc.doc_id, rc.sect_id
      FROM public.rag_corpus rc
      WHERE rc.source = ANY(%s) AND length(rc.text) >= %s
    """
    params = [srcs, args.min_len]

    if args.doc_key:
        base += " AND EXISTS (SELECT 1 FROM guidelines.docs d WHERE d.id = rc.doc_id AND d.doc_key = %s)"
        params.append(args.doc_key)

    with conn.cursor() as cur:
        cur.execute(base, params)
        rows = cur.fetchall()

    total_chunks = 0
    for (parent_id, source, title, text, meta, doc_id, sect_id) in rows:
        # wipe existing chunks for this parent
        with conn.cursor() as cur:
            cur.execute("DELETE FROM public.rag_corpus_chunks WHERE parent_id=%s", (parent_id,))
        conn.commit()

        parts = chunk_text(text, size=args.size, overlap=args.overlap)
        payload = []
        for i, part in enumerate(parts, start=1):
            m = dict(meta or {})
            m["chunk"] = i
            payload.append((
                source, title, part, None, Json(m), doc_id, sect_id, parent_id, i
            ))

        if payload:
            sql = """
              INSERT INTO public.rag_corpus_chunks
                (source, title, text, ts, meta, doc_id, sect_id, parent_id, ord)
              VALUES %s
            """
            with conn.cursor() as cur:
                execute_values(cur, sql, payload, page_size=500)
            conn.commit()
            total_chunks += len(payload)

    print(f"Chunked {len(rows)} parent rows into {total_chunks} chunks.")
    conn.close()

if __name__ == "__main__":
    main()

