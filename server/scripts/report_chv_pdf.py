#!/usr/bin/env python3
import argparse, os, sys, datetime as dt
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras

def get_db_url() -> str:
    url = os.getenv("DATABASE_URL") or "postgresql:///2ndopinionmd"
    return url.replace("+asyncpg", "")

def q(conn, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params if params is not None else None)
        return [dict(r) for r in cur.fetchall()]

def one(conn, sql: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
    rows = q(conn, sql, params)
    return rows[0] if rows else None

def has_col(conn, schema: str, table: str, col: str) -> bool:
    r = one(conn, """
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema=%s AND table_name=%s AND column_name=%s
      LIMIT 1
    """, (schema, table, col))
    return r is not None

# ---------- tiny text-to-PDF (ReportLab) with TXT fallback ----------
class _TextDoc:
    def __init__(self, width=100, lpp=56):
        self.width = width
        self.lpp = lpp
        self.lines: List[str] = []

    def _wrap(self, s: str) -> List[str]:
        out, s = [], s.rstrip("\n")
        if not s:
            return [""]
        while len(s) > self.width:
            cut = s.rfind(" ", 0, self.width)
            cut = cut if cut > 0 else self.width
            out.append(s[:cut])
            s = s[cut:].lstrip()
        out.append(s)
        return out

    def p(self, text: str = ""):
        for ln in text.splitlines():
            self.lines += self._wrap(ln)
        if text != "":
            self.lines.append("")

    def h1(self, t: str):
        self.p(t.upper())
        self.p("=" * min(len(t), self.width))

    def h2(self, t: str):
        self.p(t)
        self.p("-" * min(len(t), self.width))

    def table(self, rows: List[Dict[str, Any]]):
        if not rows:
            self.p("(no rows)")
            return
        cols = list(rows[0].keys())
        widths = [len(c) for c in cols]
        for r in rows:
            for i, c in enumerate(cols):
                widths[i] = max(widths[i], len(str(r[c]) if r[c] is not None else ""))
        widths = [min(w, 40) for w in widths]

        def fmt(vals):
            out = []
            for i, v in enumerate(vals):
                s = "" if v is None else str(v)
                if len(s) > widths[i]:
                    s = s[:max(0, widths[i]-1)] + "…"
                out.append(s.ljust(widths[i]))
            return "  ".join(out)

        self.lines.append(fmt(cols))
        self.lines.append(fmt(["-"*w for w in widths]))
        for r in rows:
            self.lines.append(fmt([r[c] for c in cols]))
        self.lines.append("")

    def paginate(self) -> List[List[str]]:
        pages, page = [], []
        for i, ln in enumerate(self.lines, 1):
            page.append(ln)
            if len(page) >= self.lpp:
                pages.append(page); page = []
        if page:
            pages.append(page)
        return pages

def _write_pdf_or_txt(out_path: str, pages: List[List[str]]):
    # Try PDF
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch

        c = canvas.Canvas(out_path, pagesize=letter)
        w, h = letter
        x, y0, leading = 0.75*inch, h-0.75*inch, 12
        for page in pages:
            y = y0
            c.setFont("Courier", 10)
            for ln in page:
                c.drawString(x, y, ln)
                y -= leading
            c.showPage()
        c.save()
        print(f"Wrote {out_path}")
        return
    except Exception as e:
        print(f"[report] PDF failed ({e}); writing TXT fallback.", file=sys.stderr)
    # Fallback TXT
    root, _ = os.path.splitext(out_path)
    txt = root + ".txt"
    with open(txt, "w", encoding="utf-8") as f:
        for pi, page in enumerate(pages, 1):
            for ln in page:
                f.write(ln + "\n")
            if pi < len(pages):
                f.write("\n" + "="*30 + f" (page {pi}) " + "="*30 + "\n\n")
    print(f"Wrote {txt}")

# ---------- metrics ----------

def compute_metrics(conn) -> Dict[str, Any]:
    m: Dict[str, Any] = {}
    m["rows_total"] = one(conn, "SELECT COUNT(*) n FROM ontology.synonyms WHERE source='CHV'")["n"]
    m["distinct_cui"] = one(conn, "SELECT COUNT(DISTINCT cui) n FROM ontology.synonyms WHERE source='CHV'")["n"]
    m["distinct_term"] = one(conn, "SELECT COUNT(DISTINCT lower(term)) n FROM ontology.synonyms WHERE source='CHV'")["n"]

    # aux tables present?
    has_stop = one(conn, "SELECT to_regclass('ontology.chv_stop_cui') IS NOT NULL AS ok")["ok"]
    has_inc  = one(conn, "SELECT to_regclass('ontology.chv_incorrect_map') IS NOT NULL AS ok")["ok"]
    has_best = one(conn, "SELECT to_regclass('ontology.chv_best') IS NOT NULL AS ok")["ok"]
    has_ng   = one(conn, "SELECT to_regclass('ontology.chv_ngrams') IS NOT NULL AS ok")["ok"]

    m["stop_cuis"] = one(conn, "SELECT COUNT(*) n FROM ontology.chv_stop_cui")["n"] if has_stop else 0
    m["incorrect"] = one(conn, "SELECT COUNT(*) n FROM ontology.chv_incorrect_map")["n"] if has_inc else 0
    m["ngrams"]    = one(conn, "SELECT COUNT(*) n FROM ontology.chv_ngrams")["n"] if has_ng else 0

    # QC
    m["blank_terms"] = one(conn, """
      SELECT COUNT(*) n FROM ontology.synonyms
      WHERE source='CHV' AND (term IS NULL OR btrim(term)='')
    """)["n"]
    m["invalid_cui"] = one(conn, """
      SELECT COUNT(*) n FROM ontology.synonyms
      WHERE source='CHV' AND NOT (cui ~ '^C[0-9]{7}$')
    """)["n"]
    m["dup_pairs"] = one(conn, """
      SELECT COUNT(*) n FROM (
        SELECT lower(term) tl, cui
        FROM ontology.synonyms WHERE source='CHV'
        GROUP BY tl, cui HAVING COUNT(*) > 1
      ) s
    """)["n"]

    # ambiguity raw
    distinct_term = float(m["distinct_term"] or 1)
    raw_n = one(conn, """
      SELECT COUNT(*) n FROM (
        SELECT lower(term) tl
        FROM ontology.synonyms WHERE source='CHV'
        GROUP BY tl HAVING COUNT(DISTINCT cui) > 1
      ) s
    """)["n"]
    m["ambig_raw_n"] = raw_n
    m["ambig_rate_raw"] = float(raw_n)/distinct_term

    # ambiguity post-filter (detect term_lower vs term)
    post_n = 0
    if has_stop and has_inc:
        has_term_lower = has_col(conn, "ontology", "chv_incorrect_map", "term_lower")
        join_expr = "im.term_lower" if has_term_lower else "lower(im.term)"
        post_n = one(conn, f"""
          WITH chv_filtered AS (
            SELECT lower(s.term) AS tl, s.cui
            FROM ontology.synonyms s
            LEFT JOIN ontology.chv_stop_cui sc ON sc.cui = s.cui
            LEFT JOIN ontology.chv_incorrect_map im
              ON im.cui = s.cui AND {join_expr} = lower(s.term)
            WHERE s.source='CHV' AND sc.cui IS NULL AND im.cui IS NULL
          )
          SELECT COUNT(*) n FROM (
            SELECT tl FROM chv_filtered
            GROUP BY tl HAVING COUNT(DISTINCT cui) > 1
          ) x
        """)["n"]
    m["ambig_post_n"] = post_n
    m["ambig_rate_post"] = float(post_n)/distinct_term

    # ambiguity best
    best_n = one(conn, """
      SELECT COUNT(*) n FROM (
        SELECT term_lower FROM ontology.chv_best
        GROUP BY term_lower HAVING COUNT(*) > 1
      ) s
    """)["n"] if has_best else 0
    m["ambig_best_n"] = best_n
    m["ambig_rate_best"] = float(best_n)/distinct_term

    # samples
    m["ambiguous_terms_sample"] = q(conn, """
      SELECT lower(term) AS term, COUNT(DISTINCT cui) AS n_cui
      FROM ontology.synonyms WHERE source='CHV'
      GROUP BY lower(term) HAVING COUNT(DISTINCT cui) > 1
      ORDER BY n_cui DESC, term LIMIT 15
    """)
    m["top_cuis"] = q(conn, """
      SELECT cui, COUNT(*) n
      FROM ontology.synonyms WHERE source='CHV'
      GROUP BY cui ORDER BY n DESC, cui LIMIT 15
    """)

    # indexes
    m["idx_best_term_lower"] = bool(one(conn, """
      SELECT 1 FROM pg_indexes
      WHERE schemaname='ontology' AND tablename='chv_best'
        AND indexname='chv_best_term_lower_idx'
      LIMIT 1
    """) or {})
    m["idx_ngrams_trgm"] = bool(one(conn, """
      SELECT 1 FROM pg_indexes
      WHERE schemaname='ontology' AND tablename='chv_ngrams'
        AND indexname='chv_ngrams_term_trgm'
      LIMIT 1
    """) or {})
    return m

def verdict(metrics: Dict[str, Any]) -> (str, str):
    post = metrics.get("ambig_rate_post", 0.0)
    raw  = metrics.get("ambig_rate_raw", 0.0)
    ngrams = int(metrics.get("ngrams") or 0)

    v = "PASS"
    if post > 0.05: v = "FAIL"
    elif post > 0.025: v = "WARN"
    if ngrams == 0 and v == "PASS":
        v = "WARN"

    why = f"Raw ambiguous rate {raw:.2%}. Post-filter {post:.2%}. "
    if ngrams == 0: why += "n-grams not loaded. "
    why += {"PASS":"Disambiguation acceptable.",
            "WARN":"Residual ambiguity; add filters/merges.",
            "FAIL":"High ambiguity; strengthen filters/merges."}[v]
    return v, why

def build_pages(m: Dict[str, Any], want_ai: bool) -> List[List[str]]:
    d = _TextDoc()
    d.h1("Consumer Health Vocabulary (CHV) — Integrity Report")
    d.p(f"Generated: {dt.datetime.now().isoformat(timespec='seconds')}")
    d.p("Source: ontology.synonyms(source='CHV') + chv_stop_cui + chv_incorrect_map + chv_ngrams + chv_best")

    v, why = verdict(m)
    d.h2(f"Verdict: {v}")
    if want_ai: d.p(why)

    d.h2("CHV — core counts")
    d.table([
        {"what":"rows_total","n":m["rows_total"]},
        {"what":"distinct_cui","n":m["distinct_cui"]},
        {"what":"distinct_term","n":m["distinct_term"]},
        {"what":"stop_cuis","n":m["stop_cuis"]},
        {"what":"incorrect","n":m["incorrect"]},
        {"what":"ngrams","n":m["ngrams"]},
    ])

    d.h2("CHV — quality checks")
    d.table([
        {"what":"blank_terms","n":m["blank_terms"]},
        {"what":"invalid_cui","n":m["invalid_cui"]},
        {"what":"dup_pairs","n":m["dup_pairs"]},
    ])

    d.h2("Ambiguity — raw vs post-filter vs best")
    d.table([
        {"metric":"ambig_rate_raw","rate":f"{m['ambig_rate_raw']:.6f}"},
        {"metric":"ambig_rate_post","rate":f"{m['ambig_rate_post']:.6f}"},
        {"metric":"ambig_rate_best","rate":f"{m['ambig_rate_best']:.6f}"},
        {"metric":"ambig_raw_n","rate":m["ambig_raw_n"]},
        {"metric":"ambig_post_n","rate":m["ambig_post_n"]},
        {"metric":"ambig_best_n","rate":m["ambig_best_n"]},
    ])

    d.h2("Ambiguous lay terms (sample)")
    d.table(m["ambiguous_terms_sample"])

    d.h2("Top CUIs by term count")
    d.table(m["top_cuis"])

    d.h2("Indexes present")
    d.table([
        {"index":"chv_best_term_lower_idx","ok":str(m["idx_best_term_lower"]).lower()},
        {"index":"chv_ngrams_term_trgm","ok":str(m["idx_ngrams_trgm"]).lower()},
    ])

    return d.paginate()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--ai", action="store_true")
    args = ap.parse_args()

    conn = psycopg2.connect(get_db_url())
    try:
        m = compute_metrics(conn)
    finally:
        conn.close()

    pages = build_pages(m, args.ai)
    _write_pdf_or_txt(args.out, pages)

if __name__ == "__main__":
    main()
