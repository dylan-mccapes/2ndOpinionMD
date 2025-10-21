#!/usr/bin/env python3
import os, json
from report_common import connect, q, build_doc, P, H2, BODY, TableFromRows, Spacer, ai_analyze

SQL = "database/sql/18_nice_audit.sql"
OUT = "db_integrity_reports/18_nice.pdf"

def load():
    conn = connect()
    try:
        row = q(conn, open(SQL).read())[0]
    finally:
        conn.close()
    return row

def verdict_from(a):
    pres   = a.get("presence", {}) or {}
    totals = a.get("totals",   {}) or {}

    docs       = int(totals.get("docs", 0))
    docs_no    = int(totals.get("docs_no_text", 0))
    sections   = int(totals.get("sections", 0))
    rag_rows   = int(totals.get("rag_rows", 0))

    if not pres.get("has_docs"):
        return "fail", "No NICE docs loaded."
    # Hard fail: docs but zero sections means ingestion didn’t parse any pages
    if sections == 0:
        return "fail", "Docs present but no sections; parsing step failed."

    # Warnings: lots of blank text_full or no RAG rows yet
    if docs and (docs_no / max(docs,1)) > 0.30:
        return "warn", "Many docs missing full text; extraction may be incomplete."
    if rag_rows == 0:
        return "warn", "No NICE rows in rag_corpus yet; embedding/search won’t work."

    return "pass", "NICE docs + sections present; data looks healthy."

def main(out=OUT, use_ai=False):
    audit = load()
    verdict, why = verdict_from(audit)

    ai_obj = None
    if use_ai:
        ai_obj = ai_analyze(
            system=(
                "You are auditing an import of NICE guidance PDFs. "
                "Return ONLY compact JSON like "
                '{"verdict":"pass|warn|fail","rationale":"<=3 short sentences","actions":["..."]}. '
                "Fail if no docs or no sections. "
                "Warn if >30% docs lack full text or there are zero rag rows. "
                "Otherwise Pass."
            ),
            user={
                "presence": audit.get("presence", {}),
                "totals":   audit.get("totals",   {}),
                "by_source":audit.get("by_source",[]),
                "top_docs": audit.get("top_docs", []),
            }
        )

    def flow(story, content_width):
        story.append(P(f"Verdict: {verdict.upper()} — {why}", BODY))
        story.append(Spacer(1, 8))

        # Totals
        totals = audit.get("totals", {}) or {}
        story.append(P("Totals (NICE)", H2))
        story.append(TableFromRows([totals], ["docs","docs_no_text","sections","rag_rows","rag_chunks"]))
        story.append(Spacer(1, 6))

        # By source (sanity: nice / cks / others present in db)
        bs = audit.get("by_source") or []
        if bs:
            story.append(P("Docs by source (all)", H2))
            story.append(TableFromRows(bs, ["source_key","docs"]))
            story.append(Spacer(1, 6))

        # Top docs snapshot
        td = audit.get("top_docs") or []
        if td:
            story.append(P("Top docs by sections (sample)", H2))
            story.append(TableFromRows(td, ["doc_key","title","n_sections","text_full_len"]))
            story.append(Spacer(1, 6))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_doc(out, "NICE (Guidelines & CKS) — INTEGRITY REPORT", None, flow, ai_obj=ai_obj)

if __name__ == "__main__":
    import sys
    out = OUT
    use_ai = ("--ai" in sys.argv) or (os.getenv("AI","0").lower() in ("1","true","yes"))
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out")+1]
    main(out, use_ai=use_ai)

