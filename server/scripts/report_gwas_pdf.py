#!/usr/bin/env python3
import os, json, pathlib
from report_common import (
    connect, q, build_doc, P, H2, BODY, TableFromRows, Spacer, ai_analyze
)

OUT = "db_integrity_reports/16_gwas.pdf"
SQL_PATH = "database/sql/16_gwas_audit.sql"  # change if you stored it elsewhere

def load():
    if not pathlib.Path(SQL_PATH).exists():
        raise SystemExit(f"Missing audit SQL at {SQL_PATH}")
    sql = pathlib.Path(SQL_PATH).read_text(encoding="utf-8")
    conn = connect()
    try:
        row = q(conn, sql)[0]
        data = row.get("audit") or row  # support either shape
        # ensure python types
        return json.loads(json.dumps(data))
    finally:
        conn.close()

def verdict_from(audit):
    rows = int(audit.get("presence", {}).get("rows", 0) or 0)
    nulls = audit.get("nulls", {}) or {}
    has_nulls = any((nulls.get("null_disease_trait",0),
                     nulls.get("null_mapped_trait",0),
                     nulls.get("null_snps",0),
                     nulls.get("null_p_value",0)))
    if rows == 0:
        return "fail", "GWAS table exists but contains 0 rows."
    if has_nulls:
        return "warn", "NULLs present in key fields (trait/snps/p_value)."
    return "pass", "GWAS hits present with basic coverage and no key NULLs."

def main(out=OUT, use_ai=False, brief=False, no_hist=False):
    a = load()
    verdict, why = verdict_from(a)

    ai_obj = None
    if use_ai:
        facts = {
            "presence": a.get("presence"),
            "nulls": a.get("nulls"),
            "duplicates": a.get("duplicates"),
            "hist_total_bins": a.get("score_hist_total_bins", 0),
        }
        ai_obj = ai_analyze(
            system=(
                "You audit a GWAS Catalog subset in PostgreSQL. "
                "Return ONLY JSON like "
                "{\"verdict\":\"pass|warn|fail\",\"rationale\":\"<=3 short sentences\","
                "\"actions\":[\"...\",\"...\"]}. "
                "Rules: fail if table 0 rows; warn if any key NULLs; pass otherwise."
            ),
            user=facts
        )

    # limits
    HIST_LIMIT = 25 if brief else 60   # table rows for histogram (single page-ish)
    TRAITS_LIMIT = 15 if brief else 25
    SNPS_LIMIT   = 15 if brief else 25
    BEST_LIMIT   = 12 if brief else 20

    def clamp(lst, n): return (lst or [])[:n]

    def flow(story, content_width):
        story.append(P(f"Verdict: {verdict.upper()} — {why}", BODY))
        story.append(Spacer(1, 8))

        # Presence
        story.append(P("Table presence & row counts", H2))
        story.append(TableFromRows(
            [{"tbl": "molecular.gwas_hits", "rows": a.get("presence",{}).get("rows",0)}],
            ["tbl","rows"]
        ))
        story.append(Spacer(1, 8))

        # Nulls
        story.append(P("Null counts", H2))
        story.append(TableFromRows(
            [a.get("nulls",{})],
            ["null_disease_trait","null_mapped_trait","null_snps","null_p_value"]
        ))
        story.append(Spacer(1, 8))

        # Dupes
        story.append(P("Duplicate groups (natural key)", H2))
        story.append(TableFromRows(
            [a.get("duplicates",{})],
            ["groups","rows_over_min"]
        ))
        story.append(Spacer(1, 8))

        # Histogram (optional + truncated)
        if not no_hist:
            hist = a.get("score_hist") or []
            total_bins = int(a.get("score_hist_total_bins", len(hist)) or 0)
            shown = clamp(hist, HIST_LIMIT)
            title = "−log10(p) histogram (bucket, n)"
            if len(shown) < total_bins:
                title += f" — showing first {len(shown)} of {total_bins} bins"
            story.append(P(title, H2))
            story.append(TableFromRows(shown, ["bucket","n"]))
            story.append(Spacer(1, 8))

        # Top traits
        story.append(P("Top traits (by row count)", H2))
        story.append(TableFromRows(clamp(a.get("top_traits"), TRAITS_LIMIT), ["disease_trait","n"]))
        story.append(Spacer(1, 8))

        # Top SNPs
        story.append(P("Top SNPS (cell frequency)", H2))
        story.append(TableFromRows(clamp(a.get("top_snps"), SNPS_LIMIT), ["snps","n"]))
        story.append(Spacer(1, 8))

        # Best hits (lowest p-values)
        best = a.get("best_hits") or []
        story.append(P("Best hits (lowest p-values)", H2))
        story.append(TableFromRows(
            clamp(best, BEST_LIMIT),
            ["disease_trait","mapped_trait","snps","p_value","strongest_snp_risk_allele","mapped_gene","reported_genes"]
        ))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_doc(out, "GWAS CATALOG — AUTOIMMUNE TRAITS — INTEGRITY REPORT", None, flow, ai_obj=ai_obj)

if __name__ == "__main__":
    import sys
    out = OUT
    env = lambda k: os.getenv(k,"").lower() in ("1","true","yes","on")
    use_ai = ("--ai" in sys.argv) or env("AI")
    brief  = ("--brief" in sys.argv) or env("BRIEF")
    no_hist= ("--no-hist" in sys.argv) or env("NO_HIST")
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out")+1]
    main(out, use_ai=use_ai, brief=brief, no_hist=no_hist)
