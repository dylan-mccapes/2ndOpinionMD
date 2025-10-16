#!/usr/bin/env python3
import os
from report_common import connect, q, build_doc, P, H2, BODY, TableFromRows, Spacer, ai_analyze

OUT = "db_integrity_reports/14_diagnostic_rules.pdf"

def load():
    conn = connect()
    try:
        pres = q(conn, """
          SELECT
            (to_regclass('guidelines.diagnostic_rules') IS NOT NULL) AS has_table,
            COALESCE((SELECT COUNT(*) FROM guidelines.diagnostic_rules), 0) AS rules,
            COALESCE((SELECT COUNT(*) FROM guidelines.diagnostic_rule_tests), 0) AS tests
        """)[0]

        tables = q(conn, """
          WITH t AS (
            SELECT 'guidelines.diagnostic_rules' AS tbl, COUNT(*)::bigint AS rows FROM guidelines.diagnostic_rules
            UNION ALL SELECT 'guidelines.diagnostic_rule_tests', COUNT(*) FROM guidelines.diagnostic_rule_tests
            UNION ALL SELECT 'public.rag_corpus', COUNT(*) FROM public.rag_corpus WHERE source='acr_eular'
          )
          SELECT tbl, rows FROM t ORDER BY tbl;
        """)

        by_cond = []
        by_org  = []
        missing_dates = []
        missing_sources = []
        rules_no_tests = []
        samples = []

        if pres["has_table"]:
            by_cond = q(conn, """
              SELECT COALESCE(NULLIF(condition,''),'(blank)') AS condition, COUNT(*)::bigint AS rules
              FROM guidelines.diagnostic_rules GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 20
            """)
            by_org = q(conn, """
              SELECT COALESCE(NULLIF(org,''),'(blank)') AS org, COUNT(*)::bigint AS rules
              FROM guidelines.diagnostic_rules GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 20
            """)
            missing_dates = q(conn, """
              SELECT rule_key, title FROM guidelines.diagnostic_rules
              WHERE published_date IS NULL ORDER BY rule_key LIMIT 20
            """)
            missing_sources = q(conn, """
              SELECT rule_key, title FROM guidelines.diagnostic_rules
              WHERE (source_urls IS NULL OR cardinality(source_urls)=0)
              ORDER BY rule_key LIMIT 20
            """)
            rules_no_tests = q(conn, """
              SELECT r.rule_key, r.title
              FROM guidelines.diagnostic_rules r
              LEFT JOIN guidelines.diagnostic_rule_tests t ON t.rule_key = r.rule_key
              GROUP BY r.rule_key, r.title
              HAVING COUNT(t.test_id)=0
              ORDER BY r.rule_key LIMIT 20
            """)
            samples = q(conn, """
              SELECT rule_key, title, org, condition, version,
                     to_char(published_date,'YYYY-MM-DD') AS published_date,
                     COALESCE(cardinality(source_urls),0) AS n_sources
              FROM guidelines.diagnostic_rules
              ORDER BY rule_key
              LIMIT 12
            """)

        return pres, tables, by_cond, by_org, missing_dates, missing_sources, rules_no_tests, samples
    finally:
        conn.close()

def verdict_from(pres, missing_dates, missing_sources, rules_no_tests):
    if not pres["has_table"]:
        return "fail", "Diagnostic rules table is missing."
    if int(pres["rules"] or 0) == 0:
        return "warn", "Diagnostic rules table exists but contains 0 rows."
    # heuristics → warn if data looks thin
    if missing_dates or missing_sources or rules_no_tests:
        return "warn", "Some metadata gaps (dates/sources/tests) detected."
    return "pass", "Diagnostic rules present with basic coverage."

def main(out=OUT, use_ai=False):
    pres, tables, by_cond, by_org, missing_dates, missing_sources, rules_no_tests, samples = load()
    verdict, why = verdict_from(pres, missing_dates, missing_sources, rules_no_tests)

    ai_obj = None
    if use_ai:
        facts = {
            "presence": pres,
            "by_condition": by_cond[:8],
            "by_org": by_org[:8],
            "missing_dates": len(missing_dates),
            "missing_sources": len(missing_sources),
            "rules_without_tests": len(rules_no_tests),
        }
        ai_obj = ai_analyze(
            system=(
                "You audit ACR/EULAR diagnostic rules in PostgreSQL. "
                "Return ONLY JSON like {\"verdict\":\"pass|warn|fail\",\"rationale\":\"<=3 short sentences\",\"actions\":[\"...\",\"...\"]}. "
                "Rules: fail if table missing; warn if 0 rows; warn if many metadata gaps; pass otherwise."
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
            story.append(P("Rules by condition", H2))
            story.append(TableFromRows(by_cond, ["condition","rules"]))
            story.append(Spacer(1, 6))

            story.append(P("Rules by organization", H2))
            story.append(TableFromRows(by_org, ["org","rules"]))
            story.append(Spacer(1, 6))

            if missing_dates:
                story.append(P("Rules missing published_date (sample)", H2))
                story.append(TableFromRows(missing_dates, ["rule_key","title"]))
                story.append(Spacer(1, 6))

            if missing_sources:
                story.append(P("Rules missing source_urls (sample)", H2))
                story.append(TableFromRows(missing_sources, ["rule_key","title"]))
                story.append(Spacer(1, 6))

            if rules_no_tests:
                story.append(P("Rules with no test cases (sample)", H2))
                story.append(TableFromRows(rules_no_tests, ["rule_key","title"]))
                story.append(Spacer(1, 6))

            if samples:
                story.append(P("Sample rules", H2))
                story.append(TableFromRows(samples, ["rule_key","title","org","condition","version","published_date","n_sources"]))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_doc(out, "ACR/EULAR — DIAGNOSTIC RULES — INTEGRITY REPORT", None, flow, ai_obj=ai_obj)

if __name__ == "__main__":
    import sys, os
    out = OUT
    use_ai = ("--ai" in sys.argv) or (os.getenv("AI","0").lower() in ("1","true","yes"))
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out")+1]
    main(out, use_ai=use_ai)

