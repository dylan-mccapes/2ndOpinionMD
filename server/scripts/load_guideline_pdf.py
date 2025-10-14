#!/usr/bin/env python3
"""
Load a single NICE (or other guideline) PDF into Postgres:

- Upsert into guidelines.docs (stores sha256, storage_path, full text)
- Replace guidelines.sections for this doc_id with one row per page
- Upsert RAG rows into public.rag_corpus with provenance (source/doc/sect)
- Leaves FTS+embeddings to your existing make targets (guidelines-fts, guidelines-embed)

ENV or CLI args (CLI overrides ENV):
  SRC_KEY   e.g. 'nice'
  DOC_KEY   e.g. 'NG220'
  TITLE     optional nice title
  URL       original landing/resource URL (optional)
  PDF       path to the PDF file

Example:
  PY=server/venv312/bin/python make guidelines-load \
    GUIDE_SRC_KEY=nice GUIDE_DOC_KEY=NG220 \
    GUIDE_URL="https://www.nice.org.uk/guidance/ng220/resources" \
    GUIDE_PDF="data/nice/NG220.pdf"
"""
import os, sys, argparse, hashlib, datetime as dt, subprocess, shlex
import psycopg2
from psycopg2.extras import execute_values

DATABASE_URL = os.getenv("SYNC_DATABASE_URL", "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd")

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def extract_pdf_pages(path):
    """
    Try pdftotext -layout (best), fallback to PyPDF if available.
    Returns list[str] (one per page), blanks removed.
    """
    # 1) pdftotext (if installed)
    try:
        out = subprocess.check_output(f"pdftotext -layout {shlex.quote(path)} -", shell=True)
        txt = out.decode("utf-8", "replace")
        pages = [p.strip() for p in txt.split("\f")]
        return [p for p in pages if p]
    except Exception:
        pass

    # 2) PyPDF fallback
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        pages = []
        for p in reader.pages:
            t = p.extract_text() or ""
            t = t.replace("\r", "\n").strip()
            if t:
                pages.append(t)
        return pages
    except Exception as e:
        print(f"[ERROR] Could not extract text. Install 'pdftotext' or 'pypdf'. {e}", file=sys.stderr)
        return []

def upsert_doc(conn, *, source_key, doc_key, title, url, pdf_path, sha256):
    sql = """
    INSERT INTO guidelines.docs
      (source_key, doc_key, version, title, url, published_at, fetched_at,
       sha256, mime_type, bytes, storage_path, text_full, meta)
    VALUES (%s,%s,NULL,%s,%s,NULL,now(),%s,'application/pdf',NULL,%s,%s)
    ON CONFLICT (source_key, doc_key, version)
    DO UPDATE SET
      title = EXCLUDED.title,
      url = EXCLUDED.url,
      fetched_at = now(),
      sha256 = EXCLUDED.sha256,
      storage_path = EXCLUDED.storage_path,
      text_full = EXCLUDED.text_full,
      meta = COALESCE(guidelines.docs.meta,'{}'::jsonb) || EXCLUDED.meta
    RETURNING id;
    """
    # full text will be supplied by caller; here we just prepare statement
    with conn.cursor() as cur:
        # we set text_full later, so pass empty string now; caller re-executes with actual content
        cur.execute(sql, (source_key, doc_key, title, url, sha256, pdf_path, {"loader":"load_guideline_pdf.py"}))
        doc_id = cur.fetchone()[0]
    conn.commit()
    return doc_id

def update_doc_fulltext(conn, doc_id, full_text):
    with conn.cursor() as cur:
        cur.execute("UPDATE guidelines.docs SET text_full=%s WHERE id=%s", (full_text, doc_id))
    conn.commit()

def replace_sections(conn, doc_id, pages):
    """
    Delete existing sections for doc_id, then insert one row per page.
    Returns list[(sect_id, ord)] aligned to pages-order.
    """
    with conn.cursor() as cur:
        cur.execute("DELETE FROM guidelines.sections WHERE doc_id=%s", (doc_id,))
    conn.commit()

    rows = []
    for i, txt in enumerate(pages, start=1):
        rows.append((doc_id, i, None, f"page-{i}", txt, {}))

    sql = """
      INSERT INTO guidelines.sections
        (doc_id, ord, heading, anchor, text, meta)
      VALUES %s
      RETURNING id, ord
    """
    with conn.cursor() as cur:
        ret = execute_values(cur, sql, rows, page_size=200, fetch=True)
    conn.commit()
    # return in the same order as inserted (ord ascending)
    ret.sort(key=lambda x: x[1])
    return ret

def replace_rag(conn, *, source_key, title, doc_id, doc_key, sect_ids_and_ords):
    """
    Remove existing RAG rows for this doc, then insert one per section.
    We keep ts NULL here; your 'make guidelines-fts' populates it.
    """
    with conn.cursor() as cur:
        cur.execute("DELETE FROM public.rag_corpus WHERE source=%s AND doc_id=%s", (source_key, doc_id))
    conn.commit()

    # fetch the fresh section texts to avoid re-plumbing them here
    with conn.cursor() as cur:
        cur.execute("""
          SELECT s.id, s.ord, s.text
          FROM guidelines.sections s
          WHERE s.doc_id = %s
          ORDER BY s.ord
        """, (doc_id,))
        sect_rows = cur.fetchall()

    rag_rows = []
    for sid, ord_, text in sect_rows:
        rag_rows.append((
            source_key,                                 # source
            title or doc_key,                           # title
            text,                                       # text
            None,                                       # ts (NULL; filled by guidelines-fts)
            {"doc_key": doc_key},                       # meta
            doc_id,                                     # doc_id
            sid                                         # sect_id
        ))

    sql = """
      INSERT INTO public.rag_corpus
        (source, title, text, ts, meta, doc_id, sect_id)
      VALUES %s
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rag_rows, page_size=300)
    conn.commit()
    return len(rag_rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("PDF", nargs="?", help="Path to PDF (or set PDF env)")
    ap.add_argument("--src", dest="SRC_KEY")
    ap.add_argument("--doc", dest="DOC_KEY")
    ap.add_argument("--title", dest="TITLE")
    ap.add_argument("--url", dest="URL")
    args = ap.parse_args()

    SRC_KEY = args.SRC_KEY or os.getenv("SRC_KEY") or os.getenv("GUIDE_SRC_KEY") or "nice"
    DOC_KEY = args.DOC_KEY or os.getenv("DOC_KEY") or os.getenv("GUIDE_DOC_KEY")
    TITLE   = args.TITLE   or os.getenv("TITLE")   or os.getenv("GUIDE_TITLE") or DOC_KEY
    URL     = args.URL     or os.getenv("URL")     or os.getenv("GUIDE_URL")
    PDF     = args.PDF     or os.getenv("PDF")     or os.getenv("GUIDE_PDF")

    if not (DOC_KEY and PDF):
        print("Usage: load_guideline_pdf.py --src nice --doc NG220 --url <u> --title <t> <PDF>", file=sys.stderr)
        sys.exit(2)
    if not os.path.exists(PDF):
        print(f"[ERROR] PDF not found: {PDF}", file=sys.stderr); sys.exit(2)

    pages = extract_pdf_pages(PDF)
    if not pages:
        print("[ERROR] No text extracted from PDF.", file=sys.stderr); sys.exit(3)

    full_text = "\n\n".join(pages)
    sha = sha256_file(PDF)

    conn = psycopg2.connect(DATABASE_URL)
    try:
        doc_id = upsert_doc(conn,
                            source_key=SRC_KEY, doc_key=DOC_KEY,
                            title=TITLE, url=URL or "", pdf_path=os.path.abspath(PDF), sha256=sha)
        update_doc_fulltext(conn, doc_id, full_text)

        sect_pairs = replace_sections(conn, doc_id, pages)  # [(id, ord), ...]
        n_rag = replace_rag(conn,
                            source_key=SRC_KEY, title=TITLE,
                            doc_id=doc_id, doc_key=DOC_KEY,
                            sect_ids_and_ords=sect_pairs)

        print(f"✅ Loaded {DOC_KEY}: {len(pages)} pages → {len(sect_pairs)} sections, {n_rag} RAG rows")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
