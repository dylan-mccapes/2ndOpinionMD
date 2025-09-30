# server/api/guidelines_va_routes.py
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import os, psycopg2
from psycopg2.extras import RealDictCursor

def _dsn():
    return os.environ.get("SYNC_DATABASE_URL", "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd")

router = APIRouter(prefix="/api/guidelines/va", tags=["va_guidelines"])

@router.get("/health")
def health():
    return {"ok": True}

@router.get("/stats")
def stats():
    with psycopg2.connect(_dsn()) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT COUNT(*) AS docs FROM guidelines.va_docs;")
        docs = cur.fetchone()["docs"]

        cur.execute("SELECT COUNT(*) AS sections FROM guidelines.va_sections;")
        sections = cur.fetchone()["sections"]

        cur.execute("""
            SELECT doc_slug, COUNT(*) AS n
            FROM guidelines.va_sections
            GROUP BY doc_slug
            ORDER BY n DESC
            LIMIT 20;
        """)
        by_doc = cur.fetchall()
    return {"docs": docs, "sections": sections, "by_doc": by_doc}

@router.get("/search")
def search(
    q: str = Query(..., min_length=2, description="Search string (websearch syntax OK)"),
    limit: int = Query(10, ge=1, le=50),
    doc: Optional[str] = Query(None, description="Optional VA doc slug to filter to one document")
):
    base_sql = """
    SELECT
        s.section_id,
        s.doc_slug,
        d.url  AS doc_url,
        d.title AS doc_title,
        s.heading,
        NULL::text AS rec_number,
        ts_headline('english', s.text_plain,
                    websearch_to_tsquery('english', %s),
                    'MaxFragments=2, MinWords=5, MaxWords=20, ShortWord=3, HighlightAll=FALSE') AS snippet,
        ts_rank(s.ts, websearch_to_tsquery('english', %s)) AS rank
    FROM guidelines.va_sections s
    JOIN guidelines.va_docs d ON d.slug = s.doc_slug
    WHERE s.ts @@ websearch_to_tsquery('english', %s)
    """
    params = [q, q, q]

    if doc:
        base_sql += " AND s.doc_slug = %s\n"
        params.append(doc)

    base_sql += " ORDER BY rank DESC LIMIT %s;"
    params.append(limit)

    with psycopg2.connect(_dsn()) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(base_sql, params)
        return cur.fetchall()

@router.get("/section/{section_id}")
def get_section(section_id: int):
    with psycopg2.connect(_dsn()) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT s.*, d.url AS doc_url, d.title AS doc_title
            FROM guidelines.va_sections s
            JOIN guidelines.va_docs d ON d.slug = s.doc_slug
            WHERE s.section_id = %s;
        """, (section_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not Found")
    return row

# Optional: expose cross-indexed codes when you seed guidelines.v_va_section_codes
@router.get("/codes/{section_id}")
def section_codes(section_id: int):
    sql = """
      SELECT section_id, system, code, display, how_derived, confidence
      FROM guidelines.v_va_section_codes
      WHERE section_id = %s
      ORDER BY confidence DESC, system, code;
    """
    with psycopg2.connect(_dsn()) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        try:
            cur.execute(sql, (section_id,))
            return cur.fetchall()
        except psycopg2.Error:
            # view may not exist yet; keep this endpoint non-fatal
            raise HTTPException(status_code=404, detail="Codes view not available or section not found")
