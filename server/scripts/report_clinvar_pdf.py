#!/usr/bin/env python3
import os, sys
from report_common import connect, q, build_doc, P, H2, BODY, TableFromRows, Spacer, ai_analyze

def has_col(conn, col):
    return q(conn, """
      SELECT EXISTS(
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='molecular' AND table_name='clinvar_summary' AND column_name=%s
      ) AS ok
    """, (col,))[0]["ok"]

def load():
    conn = connect()
    try:
        pres = q(conn, """
          SELECT
            (to_regclass('molecular.clinvar_summary') IS NOT NULL) AS has_table,
            COALESCE((SELECT COUNT(*) FROM molecular.clinvar_summary), 0)        AS rows
        """)[0]

        by_sig = []
        by_gene = []
        examples = []

        if pres["has_table"] and int(pres["rows"] or 0) > 0:
            if has_col(conn, "clinicalsignificance"):
                by_sig = q(conn, """
                  SELECT clinicalsignificance AS significance, COUNT(*)::bigint AS n
                  FROM molecular.clinvar_summary
                  GROUP BY 1 ORDER BY 2 DESC NULLS LAST LIMIT 20
                """)
            if has_col(conn, "genesymbol"):
                by_gene = q(conn, """
                  SELECT genesymbol AS gene, COUNT(*)::bigint AS n
                  FROM molecular.clinvar_summary
                  GROUP BY 1 ORDER BY 2 DESC NULLS LAST LIMIT 20
                """)
            cols = []
            for c in ("rcvaccession","genesymbol","clinicalsignificance","phenotypelist"):
                if has_col(conn, c): cols.append(c)
            if cols:
                sel = ", ".join(cols)
                examples = q(conn, f"SELECT {sel} FROM molecular.clinvar_summary LIMIT 10")

        return pres, by_sig, by_gene, examples
    finally:
        conn.close()

def verdict_from(pres):
    if not pres["has_table"]:
        return "fail", "ClinVar table not found."
    if int(pres["rows"] or 0) == 0:
        return "warn", "ClinVar table exists but contains 0 rows."
    return "pass", "ClinVar summary present."

def main(out="db_integrity_reports/10_clinvar.pdf", use_ai=False):
    pres, by_sig, by_gene, examples = load()
    verdict, why = verdict_from(pres)

    # Optional AI verdict box
    ai_obj = None
    if use_ai:
        facts = {
            "presence": pres,
            "top_significance": by_sig[:8] if by_sig else [],
            "top_genes": by_gene[:10] if by_gene else [],
        }
        ai_obj = ai_analyze(
            system=(
                "You are auditing a ClinVar import into PostgreSQL for a medical knowledge platform. "
                "Return ONLY JSON like {\"verdict\":\"pass|warn|fail\",\"rationale\":\"<=3 short sentences\"}. "
                "Rules: fail if table missing; warn if 0 rows; otherwise pass."
            ),
            user=facts
        )

    def flow(story, content_width):
        story.append(P(f"Verdict: {verdict.upper()} — {why}", BODY))
        story.append(Spacer(1, 8))
        story.append(P("Core counts", H2))
        story.append(TableFromRows([{"what":"rows", "n": int(pres["rows"])}], ["what","n"]))
        story.append(Spacer(1, 8))

        if by_sig:
            story.append(P("Top clinical significance", H2))
            story.append(TableFromRows(by_sig, ["significance","n"]))
            story.append(Spacer(1, 8))

        if by_gene:
            story.append(P("Top genes", H2))
            story.append(TableFromRows(by_gene, ["gene","n"]))
            story.append(Spacer(1, 8))

        if examples:
            story.append(P("Sample records", H2))
            story.append(TableFromRows(examples, list(examples[0].keys())))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_doc(out, "ClinVar — INTEGRITY REPORT", None, flow, ai_obj=ai_obj)

if __name__ == "__main__":
    out = "db_integrity_reports/10_clinvar.pdf"
    use_ai = ("--ai" in sys.argv) or (os.getenv("AI","0").lower() in ("1","true","yes"))
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out")+1]
    main(out, use_ai=use_ai)
