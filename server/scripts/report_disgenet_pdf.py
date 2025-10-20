#!/usr/bin/env python3
# server/scripts/report_disgenet_pdf.py
import os
from report_common import (
    connect, q, build_doc,
    P, H2, BODY, TableFromRows, Spacer, ai_analyze
)

OUT = "db_integrity_reports/15_disgenet.pdf"
TITLE = "DisGeNET — Gene–Disease Associations — INTEGRITY REPORT"

def load():
    conn = connect()
    try:
        # Presence & simple row count
        pres = q(conn, """
          SELECT
            (to_regclass('molecular.disgenet_associations') IS NOT NULL) AS has_table,
            COALESCE((SELECT COUNT(*) FROM molecular.disgenet_associations), 0) AS rows
        """)[0]

        # If the table exists, pull the rest; otherwise return empties
        totals = {}
        nulls = {}
        duplicates = {}
        score_hist = []
        top_genes = []
        top_diseases = []
        top_hits = []

        if pres["has_table"]:
            totals = q(conn, """
              SELECT
                COUNT(*)::bigint                                  AS rows,
                COUNT(DISTINCT assoc_id)::bigint                  AS assoc_ids,
                SUM(CASE WHEN assoc_id IS NULL THEN 1 ELSE 0 END)::bigint AS null_assoc_ids,
                COUNT(DISTINCT gene_symbol)::bigint               AS genes,
                COUNT(DISTINCT gene_ncbi_id)::bigint              AS gene_ids,
                COUNT(DISTINCT disease_name)::bigint              AS diseases
              FROM molecular.disgenet_associations
            """)[0]

            nulls = q(conn, """
              SELECT
                SUM(CASE WHEN gene_symbol   IS NULL THEN 1 ELSE 0 END)::bigint AS null_gene_symbol,
                SUM(CASE WHEN gene_ncbi_id  IS NULL THEN 1 ELSE 0 END)::bigint AS null_gene_id,
                SUM(CASE WHEN disease_name  IS NULL THEN 1 ELSE 0 END)::bigint AS null_disease_name,
                SUM(CASE WHEN score         IS NULL THEN 1 ELSE 0 END)::bigint AS null_score
              FROM molecular.disgenet_associations
            """)[0]

            duplicates = q(conn, """
              SELECT COALESCE((
                SELECT COUNT(*)::bigint
                FROM (
                  SELECT assoc_id
                  FROM molecular.disgenet_associations
                  WHERE assoc_id IS NOT NULL
                  GROUP BY assoc_id
                  HAVING COUNT(*) > 1
                ) d
              ),0) AS assoc_dupes
            """)[0]

            score_hist = q(conn, """
              SELECT
                FLOOR(score * 10)::int AS bucket,
                COUNT(*)::bigint       AS n
              FROM molecular.disgenet_associations
              WHERE score IS NOT NULL
              GROUP BY 1
              ORDER BY 1
            """)

            top_genes = q(conn, """
              SELECT gene_symbol, COUNT(*)::bigint AS n
              FROM molecular.disgenet_associations
              WHERE gene_symbol IS NOT NULL
              GROUP BY gene_symbol
              ORDER BY n DESC, gene_symbol ASC
              LIMIT 20
            """)

            top_diseases = q(conn, """
              SELECT disease_name, COUNT(*)::bigint AS n
              FROM molecular.disgenet_associations
              WHERE disease_name IS NOT NULL
              GROUP BY disease_name
              ORDER BY n DESC, disease_name ASC
              LIMIT 20
            """)

            top_hits = q(conn, """
              SELECT
                gene_symbol,
                disease_name,
                score::float  AS score,
                num_pmids::int AS num_pmids
              FROM molecular.disgenet_associations
              ORDER BY score DESC NULLS LAST, num_pmids DESC NULLS LAST
              LIMIT 20
            """)

        return pres, totals, nulls, duplicates, score_hist, top_genes, top_diseases, top_hits
    finally:
        conn.close()

def verdict_from(pres, totals, nulls, duplicates):
    if not pres["has_table"]:
        return "fail", "DisGeNET table is missing."
    if int(pres.get("rows", 0) or 0) == 0:
        return "warn", "DisGeNET table exists but contains 0 rows."
    # Warn if any obvious data-quality issues
    if (int(nulls.get("null_gene_symbol", 0)) > 0 or
        int(nulls.get("null_gene_id", 0)) > 0 or
        int(nulls.get("null_disease_name", 0)) > 0 or
        int(duplicates.get("assoc_dupes", 0)) > 0):
        return "warn", "Some NULLs/duplicates detected in key fields."
    return "pass", "DisGeNET associations present with basic coverage."

def main(out=OUT, use_ai=False):
    pres, totals, nulls, duplicates, score_hist, top_genes, top_diseases, top_hits = load()
    verdict, why = verdict_from(pres, totals, nulls, duplicates)

    ai_obj = None
    if use_ai:
        facts = {
            "presence": pres,
            "totals": totals,
            "nulls": nulls,
            "duplicates": duplicates,
            "score_histogram_head": score_hist[:8],
            "sample_top_genes": top_genes[:8],
            "sample_top_diseases": top_diseases[:8],
        }
        ai_obj = ai_analyze(
            system=(
                "You audit a PostgreSQL import of DisGeNET gene–disease associations. "
                "Return ONLY compact JSON like "
                '{"verdict":"pass|warn|fail","rationale":"<=3 short sentences","actions":["...","..."]}. '
                "Rules: fail if table missing; warn if 0 rows; warn if assoc_id duplicates or NULLs in "
                "gene_symbol/gene_ncbi_id/disease_name are present; pass otherwise. "
                "Keep actions practical (<=5), e.g., constraints, indexes, refresh routines."
            ),
            user=facts
        )

    def flow(story, content_width):
        story.append(P(f"Verdict: {verdict.upper()} — {why}", BODY))
        story.append(Spacer(1, 8))

        story.append(P("Table presence & totals", H2))
        if pres["has_table"]:
            story.append(TableFromRows([totals], ["rows","assoc_ids","null_assoc_ids","genes","gene_ids","diseases"]))
        else:
            story.append(TableFromRows([{"rows":0,"assoc_ids":0,"null_assoc_ids":0,"genes":0,"gene_ids":0,"diseases":0}],
                                       ["rows","assoc_ids","null_assoc_ids","genes","gene_ids","diseases"]))
        story.append(Spacer(1, 8))

        if pres["has_table"]:
            story.append(P("Nulls & duplicates (key fields)", H2))
            story.append(TableFromRows([{
                "null_gene_symbol": nulls.get("null_gene_symbol", 0),
                "null_gene_id": nulls.get("null_gene_id", 0),
                "null_disease_name": nulls.get("null_disease_name", 0),
                "null_score": nulls.get("null_score", 0),
                "assoc_dupes": duplicates.get("assoc_dupes", 0),
            }], ["null_gene_symbol","null_gene_id","null_disease_name","null_score","assoc_dupes"]))
            story.append(Spacer(1, 8))

            if score_hist:
                story.append(P("Score histogram (bucket = floor(score×10))", H2))
                story.append(TableFromRows(score_hist, ["bucket","n"]))
                story.append(Spacer(1, 8))

            if top_genes:
                story.append(P("Top genes by association count", H2))
                story.append(TableFromRows(top_genes, ["gene_symbol","n"]))
                story.append(Spacer(1, 6))

            if top_diseases:
                story.append(P("Top diseases by association count", H2))
                story.append(TableFromRows(top_diseases, ["disease_name","n"]))
                story.append(Spacer(1, 6))

            if top_hits:
                story.append(P("Highest-scoring associations (top 20)", H2))
                story.append(TableFromRows(top_hits, ["gene_symbol","disease_name","score","num_pmids"]))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_doc(out, TITLE, None, flow, ai_obj=ai_obj)

if __name__ == "__main__":
    import sys
    out = OUT
    use_ai = ("--ai" in sys.argv) or (os.getenv("AI","0").lower() in ("1","true","yes"))
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out")+1]
    main(out, use_ai=use_ai)
