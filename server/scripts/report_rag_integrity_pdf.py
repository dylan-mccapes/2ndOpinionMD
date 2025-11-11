#!/usr/bin/env python3
"""
Generate an integrity PDF summarizing rag_corpus by source:
- total / embedded / pending / %
- presence of GIN text index and IVFFLAT index
- example doc_keys per source
Output: reports/rag_integrity.pdf
"""
import os, io, textwrap, asyncpg, asyncio
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from pathlib import Path

DBURL = os.getenv("DATABASE_URL")
OUT = Path("reports/rag_integrity.pdf")

SQL_SUMMARY = """
SELECT source,
       COUNT(*) AS total,
       COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS done,
       COUNT(*) FILTER (WHERE embedding IS NULL)     AS pending,
       ROUND(100.0 * COUNT(*) FILTER (WHERE embedding IS NOT NULL) / NULLIF(COUNT(*),0), 2) AS pct
FROM public.rag_corpus
GROUP BY source ORDER BY total DESC;
"""

SQL_SAMPLES = """
SELECT source, source_id, title
FROM public.rag_corpus
WHERE source = $1
ORDER BY id DESC
LIMIT 5;
"""

SQL_INDEXES = """
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname='public' AND tablename='rag_corpus'
ORDER BY 1;
"""

def build_pdf(summary_rows, index_rows, examples_by_source):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, title="RAG Integrity Report")
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("RAG Integrity Report", styles["Title"]))
    story.append(Spacer(1, 6))

    # indexes
    story.append(Paragraph("<b>Indexes</b>", styles["Heading2"]))
    for idx, ddl in index_rows:
        story.append(Paragraph(f"{idx}: {ddl}", styles["BodyText"]))
    story.append(Spacer(1, 8))

    # per-source table
    data = [["Source","Total","Embedded","Pending","% Embedded"]]
    for r in summary_rows:
        data.append([r["source"], str(r["total"]), str(r["done"]), str(r["pending"]), f"{r['pct']}%"])
    tbl = Table(data, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), colors.lightgrey),
        ("GRID",(0,0),(-1,-1), 0.25, colors.grey),
        ("ALIGN",(0,0),(-1,-1), "LEFT"),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"),
    ]))
    story.append(tbl)
    story.append(Spacer(1,10))

    # examples
    for src, rows in examples_by_source.items():
        story.append(Paragraph(f"<b>Examples: {src}</b>", styles["Heading3"]))
        for s in rows:
            story.append(Paragraph(f"{s['source_id']} — {s['title']}", styles["BodyText"]))
        story.append(Spacer(1,6))

    doc.build(story)
    return buf.getvalue()

async def main():
    if not DBURL: raise SystemExit("DATABASE_URL not set")
    conn = await asyncpg.connect(dsn=DBURL)
    try:
        summary = await conn.fetch(SQL_SUMMARY)
        indexes = await conn.fetch(SQL_INDEXES)

        examples = {}
        for r in summary:
            src = r["source"]
            examples[src] = await conn.fetch(SQL_SAMPLES, src)

        pdf = build_pdf(summary, [(i["indexname"], i["indexdef"]) for i in indexes], examples)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_bytes(pdf)
        print(f"Wrote {OUT}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())

