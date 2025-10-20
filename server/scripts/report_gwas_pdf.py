#!/usr/bin/env python3
import os
from report_common import connect, q, build_doc, P, H2, BODY, TableFromRows, Spacer, ai_analyze

OUT = "db_integrity_reports/16_gwas.pdf"

def load():
    conn = connect()
    try:
        pres = q(conn, """
          SELECT
            (to_regclass('molecular.gwas_hits') IS NOT NULL) AS has_table,
            COALESCE((SELECT COUNT(*) FROM molecular.gwas_hits), 0) AS rows,
            (SELECT MIN(p_value) FROM molecular.gwas_hits) AS best_p
        """)[0]

        tables = q(conn, """
          SELECT 'molecular.gwas_hits' AS tbl,
                 COUNT(*)::bigint AS rows
          FROM molecular.gwas_hits
        """)

        nulls = q(conn, """
          SELECT
            COUNT(*) FILTER (WHERE disease_trait IS NULL)     AS null_disease_trait,
            COUNT(*) FILTER (WHERE mapped_trait  IS NULL)     AS null_mapped_trait,
            COUNT(*) FILTER (WHERE snps IS NULL)              AS null_snps,
            COUNT(*) FILTER (WHERE p_value IS NULL)           AS null_p_value
          FROM molecular.gwas_hits
        """)[0]

        dupes = q(conn, """
          SELECT COUNT(*) AS dupes FROM (
            SELECT COALESCE(study_accession,''), COALESCE(snps,''), COALESCE(disease_trait,''),
                   COUNT(*) c
            FROM molecular.gwas_hits
            GROUP BY 1,2,3
            HAVING COUNT(*) > 1
          ) d
        """)[0]

        p_hist = q(conn, """
          SELECT bucket::int, COUNT(*) AS n
          FROM (
            SELECT CASE
                     WHEN p_value IS NULL OR p_value <= 0 THEN NULL
                     ELSE floor( GREATEST(0, -log(p_value)/log(10)) )
                   END AS bucket
            FROM molecular.gwas_hits
          ) x
          WHERE bucket IS NOT NULL
          GROUP BY 1
          ORDER BY 1
        """)

        top_traits = q(conn, """
          SELECT disease_trait, COUNT(*) AS n
          FROM molecular.gwas_hits
          GROUP BY 1
          ORDER BY n DESC, disease_trait
          LIMIT 20
        """)

        top_snps = q(conn, """
          SELECT snps, COUNT(*) AS n
          FROM molecular.gwas_hits
          WHERE snps IS NOT NULL AND snps <> ''
          GROUP BY 1
          ORDER BY n DESC, snps
          LIMIT 20
        """)

        best_hits = q(conn, """
          SELECT disease_trait, mapped_trait, snps, p_value, strongest_snp_risk_allele,
                 mapped_gene, reported_genes
          FROM molecular.gwas_hits
          WHERE p_value IS NOT NULL
          ORDER BY p_value ASC
          LIMIT 20
        """)

        return pres, tables, nulls, dupes, p_hist, top_traits, top_snps, best_hits
    finally:
        conn.close()

def verdict_from(pres, nulls, dupes):
    if not pres["has_table"]:
        return "fail", "GWAS table is missing."
    if int(pres["rows"] or 0) == 0:
        return "fail", "GWAS table exists but contains 0 rows."
    # Heuristics:
    hard_nulls = int(nulls["null_disease_trait"] or 0) + int(nulls["null_snps"] or 0)
    if int(dupes["dupes"] or 0) > 0:
        return "warn", "Duplicate rows detected in natural key."
    if hard_nulls > 0:
        return "warn", "NULLs present in key fields (disease_trait/snps)."
    return "pass", "GWAS hits present with no duplicates and acceptable nulls."

def main(out=OUT, use_ai=False):
    pres, tables, nulls, dupes, p_hist, top_traits, top_snps, best_hits = load()
    verdict, why = verdict_from(pres, nulls, dupes)

    ai_obj = None
    if use_ai:
        facts = {
            "presence": pres,
            "nulls": nulls,
            "dupes": dupes,
            "p_hist_sample": p_hist[:10],
            "top_traits_sample": top_traits[:8],
        }
        ai_obj = ai_analyze(
            system=(
                "You audit a PostgreSQL GWAS Catalog subset. "
                "Return ONLY JSON like "
                "{\"verdict\":\"pass|warn|fail\",\"rationale\":\"<=3 short sentences\",\"actions\":[\"...\",\"...\"]}. "
                "Rules: fail if table missing or 0 rows; warn if duplicates>0 or NULLs in key fields; pass otherwise."
            ),
            user=facts
        )

    def flow(story, content_width):
        story.append(P(f"Verdict: {verdict.upper()} — {why}", BODY))
        story.append(Spacer(1, 8))

        story.append(P("Table presence & row counts", H2))
        story.append(TableFromRows(tables, ["tbl","rows"]))
        story.append(Spacer(1, 8))

        if pres["has_table"]:
            story.append(P("Null counts", H2))
            story.append(TableFromRows([nulls], ["null_disease_trait","null_mapped_trait","null_snps","null_p_value"]))
            story.append(Spacer(1, 6))

            story.append(P("Duplicate groups (natural key)", H2))
            story.append(TableFromRows([dupes], ["dupes"]))
            story.append(Spacer(1, 6))

            story.append(P("−log10(p) histogram (bucket, n)", H2))
            story.append(TableFromRows(p_hist, ["bucket","n"]))
            story.append(Spacer(1, 6))

            story.append(P("Top traits (by row count)", H2))
            story.append(TableFromRows(top_traits, ["disease_trait","n"]))
            story.append(Spacer(1, 6))

            story.append(P("Top SNPS (cell frequency)", H2))
            story.append(TableFromRows(top_snps, ["snps","n"]))
            story.append(Spacer(1, 6))

            story.append(P("Best hits (lowest p-values)", H2))
            story.append(TableFromRows(best_hits, ["disease_trait","mapped_trait","snps","p_value","strongest_snp_risk_allele","mapped_gene","reported_genes"]))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_doc(out, "GWAS CATALOG — AUTOIMMUNE TRAITS — INTEGRITY REPORT", None, flow, ai_obj=ai_obj)

if __name__ == "__main__":
    import sys, os
    out = OUT
    use_ai = ("--ai" in sys.argv) or (os.getenv("AI","0").lower() in ("1","true","yes"))
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out")+1]
    main(out, use_ai=use_ai)

