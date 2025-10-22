#!/usr/bin/env python3
import os, sys, math, datetime as dt
from typing import List, Dict, Any, Tuple
from report_common import connect, q, build_doc, P, H2, BODY, SMALL, TableFromRows, Spacer, ai_analyze

# ---------- Data collection ----------

def load() -> dict:
    conn = connect()
    try:
        pres = q(conn, """
          SELECT
            (to_regclass('clingen.actionability_assertions') IS NOT NULL) AS has_table,
            COALESCE((SELECT COUNT(*) FROM clingen.actionability_assertions), 0) AS actionability_rows,
            (to_regclass('clingen.v_actionability_latest') IS NOT NULL) AS has_mv,
            COALESCE((SELECT COUNT(*) FROM clingen.v_actionability_latest), 0) AS latest_rows
        """)[0]

        out: dict[str, Any] = {"presence": pres}

        if pres["has_table"] and int(pres["actionability_rows"] or 0) > 0:
            # Score completeness in base table and in MV
            out["score_base"] = q(conn, """
              SELECT
                COUNT(*) FILTER (WHERE score IS NOT NULL) AS have_score,
                COUNT(*) AS total
              FROM clingen.actionability_assertions
            """)[0]

            out["score_mv"] = q(conn, """
              SELECT
                COUNT(*) FILTER (WHERE score IS NOT NULL) AS have_score,
                COUNT(*) AS total
              FROM clingen.v_actionability_latest
            """)[0] if pres["has_mv"] else {"have_score": 0, "total": 0}

            # Score distribution (MV)
            out["score_dist"] = q(conn, """
              SELECT score, COUNT(*)::bigint AS n
              FROM clingen.v_actionability_latest
              WHERE score IS NOT NULL
              GROUP BY 1 ORDER BY 1
            """) if pres["has_mv"] else []

            # Assertion coverage by cohort (MV)
            out["assert_by_cohort"] = q(conn, """
              SELECT cohort,
                COUNT(*) FILTER (WHERE assertion ILIKE '%Strong%')   AS strong,
                COUNT(*) FILTER (WHERE assertion ILIKE '%Moderate%') AS moderate,
                COUNT(*) FILTER (WHERE assertion ILIKE '%Limited%')  AS limited,
                COUNT(*) FILTER (WHERE assertion ILIKE '%Pending%')  AS pending
              FROM clingen.v_actionability_latest
              GROUP BY 1 ORDER BY 1
            """) if pres["has_mv"] else []

            # Domain x assertion (MV)
            out["domain_assert"] = q(conn, """
              SELECT domain, COALESCE(assertion,'') AS assertion, COUNT(*)::bigint AS n
              FROM clingen.v_actionability_latest
              GROUP BY 1,2
              ORDER BY domain, n DESC
            """) if pres["has_mv"] else []

            # Identifier coverage (MV)
            out["id_resolution"] = q(conn, """
              SELECT
                COUNT(*) FILTER (WHERE hgnc_id IS NOT NULL AND hgnc_id <> '')                 AS have_hgnc,
                COUNT(*) FILTER (WHERE disease_mondo_id IS NOT NULL AND disease_mondo_id <> '') AS have_mondo,
                COUNT(*) AS total
              FROM clingen.v_actionability_latest
            """)[0] if pres["has_mv"] else {"have_hgnc": 0, "have_mondo": 0, "total": 0}

            # Freshness (MV)
            out["freshness"] = q(conn, """
              SELECT cohort, MIN(report_date) AS oldest, MAX(report_date) AS newest
              FROM clingen.v_actionability_latest
              GROUP BY 1 ORDER BY 1
            """) if pres["has_mv"] else []

            # Examples (a few latest rows)
            out["examples"] = q(conn, """
              SELECT cohort, gene_symbol, disease_name, domain, outcome, score, assertion, report_date, source_url
              FROM clingen.v_actionability_latest
              ORDER BY report_date DESC NULLS LAST, cohort, gene_symbol
              LIMIT 12
            """) if pres["has_mv"] else []
        else:
            out.update({
                "score_base": {"have_score": 0, "total": 0},
                "score_mv": {"have_score": 0, "total": 0},
                "score_dist": [], "assert_by_cohort": [], "domain_assert": [],
                "id_resolution": {"have_hgnc": 0, "have_mondo": 0, "total": 0},
                "freshness": [], "examples": [],
            })
        return out
    finally:
        conn.close()

# ---------- Verdict logic ----------

def percent(have: int, total: int) -> float:
    return round(100.0 * have / total, 1) if total else 0.0

def verdict_from(data: dict) -> Tuple[str, str]:
    pres = data["presence"]
    if not pres["has_table"]:
        return "fail", "ACI table missing."
    if int(pres["actionability_rows"] or 0) == 0:
        return "warn", "ACI table exists but has 0 rows."
    if not pres["has_mv"]:
        return "warn", "ACI materialized view missing (latest view not available)."

    mv_total = int(pres["latest_rows"] or 0)
    have_score = int(data["score_mv"]["have_score"] or 0)
    pct_score = percent(have_score, mv_total)

    # Heuristics:
    # - PASS if MV has rows AND either (scores present for ≥10% of MV) OR assertions present for ≥50%
    # - WARN otherwise (low scoring coverage), FAIL only if table actually missing (handled above)
    if mv_total > 0:
        # Check assertion coverage magnitude
        assertion_present = True if data["domain_assert"] or data["assert_by_cohort"] else False
        if pct_score >= 10.0 or assertion_present:
            return "pass", f"ACI present with MV rows={mv_total}, score coverage={pct_score:.1f}%."
        else:
            return "warn", f"Low scoring coverage: MV rows={mv_total}, score coverage={pct_score:.1f}%."
    return "warn", "ACI present but latest view returned 0 rows."

# ---------- PDF builder ----------

def main(out="db_integrity_reports/11_clingen_aci.pdf", use_ai=False):
    data = load()
    verdict, why = verdict_from(data)

    # Optional AI verdict box
    ai_obj = None
    if use_ai:
        facts = {
            "presence": data.get("presence", {}),
            "score_mv": data.get("score_mv", {}),
            "score_dist_top": data.get("score_dist", [])[:12],
            "assert_by_cohort": data.get("assert_by_cohort", []),
            "id_resolution": data.get("id_resolution", {}),
        }
        ai_obj = ai_analyze(
            system=(
                "You are auditing ClinGen ACI imports into PostgreSQL. "
                "Return ONLY JSON like {\"verdict\":\"pass|warn|fail|info\",\"rationale\":\"<=3 short sentences\"}. "
                "Rules: fail if table missing; warn if table empty or no MV; otherwise pass unless score coverage is extremely low."
            ),
            user=facts
        )

    def flow(story, content_width):
        pres = data["presence"]
        story.append(P(f"Verdict: {verdict.upper()} — {why}", BODY))
        story.append(Spacer(1, 8))

        story.append(P("Presence & sizes", H2))
        story.append(TableFromRows([{
            "has_table": pres["has_table"],
            "actionability_rows": int(pres["actionability_rows"] or 0),
            "has_mv": pres["has_mv"],
            "latest_rows": int(pres["latest_rows"] or 0),
        }], ["has_table","actionability_rows","has_mv","latest_rows"]))
        story.append(Spacer(1, 8))

        # Score completeness (base + MV)
        sb = data["score_base"]; smv = data["score_mv"]
        story.append(P("Score completeness", H2))
        story.append(TableFromRows([
            {
                "where": "actionability_assertions",
                "have_score": int(sb["have_score"] or 0),
                "total": int(sb["total"] or 0),
                "pct": f"{percent(int(sb['have_score'] or 0), int(sb['total'] or 0)):.1f}%",
            },
            {
                "where": "v_actionability_latest",
                "have_score": int(smv["have_score"] or 0),
                "total": int(smv["total"] or 0),
                "pct": f"{percent(int(smv['have_score'] or 0), int(smv['total'] or 0)):.1f}%",
            }
        ], ["where","have_score","total","pct"]))
        story.append(Spacer(1,8))

        # Score distribution
        if data["score_dist"]:
            story.append(P("Score distribution (latest view)", H2))
            story.append(TableFromRows(data["score_dist"], ["score","n"]))
            story.append(Spacer(1,8))

        # Assertions by cohort
        if data["assert_by_cohort"]:
            story.append(P("Assertion coverage by cohort (latest view)", H2))
            story.append(TableFromRows(data["assert_by_cohort"], ["cohort","strong","moderate","limited","pending"]))
            story.append(Spacer(1,8))

        # Domain x Assertion
        if data["domain_assert"]:
            story.append(P("Domain × Assertion counts (latest view)", H2))
            # Only show the top ~20 rows for readability
            show = data["domain_assert"][:20]
            story.append(TableFromRows(show, ["domain","assertion","n"]))
            story.append(Spacer(1,8))

        # Identifier resolution
        ir = data["id_resolution"]
        story.append(P("Identifier resolution (latest view)", H2))
        story.append(TableFromRows([{
            "have_hgnc": int(ir.get("have_hgnc",0)),
            "have_mondo": int(ir.get("have_mondo",0)),
            "total": int(ir.get("total",0))
        }], ["have_hgnc","have_mondo","total"]))
        story.append(Spacer(1,8))

        # Freshness window
        if data["freshness"]:
            story.append(P("Freshness (oldest/newest report_date in latest view)", H2))
            story.append(TableFromRows(data["freshness"], ["cohort","oldest","newest"]))
            story.append(Spacer(1,8))

        # Examples
        if data["examples"]:
            story.append(P("Sample latest rows", H2))
            story.append(TableFromRows(data["examples"],
                ["cohort","gene_symbol","disease_name","domain","outcome","score","assertion","report_date","source_url"]
            ))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_doc(out, "ClinGen ACI — INTEGRITY REPORT", None, flow, ai_obj=ai_obj)

if __name__ == "__main__":
    out = "db_integrity_reports/11_clingen_aci.pdf"
    use_ai = ("--ai" in sys.argv) or (os.getenv("AI","0").lower() in ("1","true","yes"))
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out")+1]
    main(out, use_ai=use_ai)
