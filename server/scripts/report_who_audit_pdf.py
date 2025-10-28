#!/usr/bin/env python3
# WHO EML / AWaRe / Committee — Audit & Integrity PDF
import os, json
from report_common import (
    connect, q, build_doc, P, H2, BODY, TableFromRows, Spacer, ai_analyze
)

OUT = "db_integrity_reports/19_who.pdf"

def fetch_counts(conn):
    row = q(conn, """
        SELECT
          (SELECT count(*) FROM guidelines.who_eml_medicines)  AS n_meds,
          (SELECT count(*) FROM guidelines.who_eml_atc)        AS n_atc,
          (SELECT count(*) FROM guidelines.who_eml_icd11)      AS n_icd11,
          (SELECT count(*) FROM guidelines.who_committee_sections) AS n_committee_sec
    """)[0]
    return {k:int(row.get(k,0) or 0) for k in ("n_meds","n_atc","n_icd11","n_committee_sec")}

def fetch_aware_distribution(conn):
    return q(conn, """
        SELECT COALESCE(NULLIF(m.antibiotic_group,''),'(Unlabeled)') AS group_name,
               COUNT(*)::int AS n
        FROM guidelines.who_eml_medicines m
        WHERE EXISTS (
            SELECT 1 FROM guidelines.who_eml_atc a
            WHERE a.med_id=m.med_id AND a.atc_code ILIKE 'J01%'
        )
        GROUP BY 1
        ORDER BY 1
    """)

def fetch_missing_formulations(conn, limit=50):
    return q(conn, f"""
        SELECT m.med_id, m.inn, COUNT(*)::int AS n_missing
        FROM guidelines.who_eml_medicines m
        LEFT JOIN guidelines.who_eml_formulations f ON f.med_id=m.med_id
        WHERE COALESCE(f.route,'')='' OR COALESCE(f.dose_form,'')='' OR COALESCE(f.strength,'')=''
        GROUP BY m.med_id, m.inn
        ORDER BY n_missing DESC, m.inn
        LIMIT {int(limit)}
    """)

def fetch_rag_counts(conn):
    def count_for(src):
        return q(conn, "SELECT count(*)::int AS n FROM public.rag_corpus WHERE source=%s", (src,))[0]["n"]
    out = {
        "who_eml": count_for("who_eml"),
        "who_committee": count_for("who_committee"),
    }
    return out

def has_index_like(conn, like_expr):
    row = q(conn, "SELECT 1 FROM pg_indexes WHERE indexname ILIKE %s LIMIT 1", (like_expr, ))
    return bool(row)

def fetch_indexes(conn):
    return {
        # tolerate different naming patterns
        "who_eml_ts_gin": has_index_like(conn, "%who_eml_ts_gin%"),
        "who_committee_sections_ts_gin": has_index_like(conn, "%who_committee_sections_ts_gin%"),
        "rag_who_eml_ann": has_index_like(conn, "%who_eml%ann%"),
        "rag_who_committee_ann": has_index_like(conn, "%who_committee%ann%"),
    }

def verdict_from(counts, forms_missing):
    if counts.get("n_meds",0) == 0:
        return "fail", "No WHO EML medicines were found."
    if forms_missing:
        return "warn", "Some formulations have missing route/form/strength fields."
    return "pass", "Core tables present with no major integrity issues detected."

def load():
    conn = connect()
    try:
        counts = fetch_counts(conn)
        aware  = fetch_aware_distribution(conn)
        miss   = fetch_missing_formulations(conn, limit=50)
        rag    = fetch_rag_counts(conn)
        idx    = fetch_indexes(conn)
        return {
            "counts": counts,
            "aware": aware,
            "forms_missing": miss,
            "rag": rag,
            "indexes": idx,
        }
    finally:
        conn.close()

def main(out=OUT, use_ai=False, brief=False):
    a = load()
    verdict, why = verdict_from(a["counts"], a["forms_missing"])

    # AI analysis block (JSON only; build_doc will render a short AI section if provided)
    ai_obj = None
    if use_ai:
        facts = {
            "counts": a.get("counts"),
            "aware_distribution": a.get("aware"),
            "forms_missing_total": sum(r["n_missing"] for r in (a.get("forms_missing") or [])),
            "top_forms_missing": a.get("forms_missing")[:10],
            "indexes": a.get("indexes"),
            "rag": a.get("rag"),
        }
        ai_obj = ai_analyze(
            system=(
                "You audit a WHO Essential Medicines (EML) + AWaRe import in PostgreSQL. "
                "Return ONLY JSON like "
                "{\"verdict\":\"pass|warn|fail\",\"rationale\":\"<=3 short sentences\","
                "\"actions\":[\"...\",\"...\"]}. "
                "Rules: fail if n_meds==0; warn if any formulations have missing route/form/strength "
                "or if n_icd11==0; otherwise pass. Keep actions concrete and short."
            ),
            user=facts
        )

    # limits to keep pages nice
    FM_LIMIT = 15 if brief else 50

    def clamp(lst, n): return (lst or [])[:n]

    def flow(story, content_width):
        # Verdict
        story.append(P(f"Verdict: {verdict.upper()} — {why}", BODY))
        story.append(Spacer(1, 8))

        # Counts
        story.append(P("Table presence & counts", H2))
        story.append(TableFromRows(
            [{
                "who_eml_medicines": a["counts"]["n_meds"],
                "who_eml_atc": a["counts"]["n_atc"],
                "who_eml_icd11": a["counts"]["n_icd11"],
                "who_committee_sections": a["counts"]["n_committee_sec"],
            }],
            ["who_eml_medicines","who_eml_atc","who_eml_icd11","who_committee_sections"]
        ))
        story.append(Spacer(1, 8))

        # RAG corpus
        story.append(P("RAG corpus rows (by source)", H2))
        story.append(TableFromRows(
            [
                {"source":"who_eml","n":a["rag"]["who_eml"]},
                {"source":"who_committee","n":a["rag"]["who_committee"]},
            ],
            ["source","n"]
        ))
        story.append(Spacer(1, 8))

        # Indexes
        story.append(P("Index presence", H2))
        story.append(TableFromRows(
            [a["indexes"]],
            ["who_eml_ts_gin","who_committee_sections_ts_gin","rag_who_eml_ann","rag_who_committee_ann"]
        ))
        story.append(Spacer(1, 8))

        # AWaRe
        story.append(P("AWaRe distribution (J01 antibacterials)", H2))
        story.append(TableFromRows(a["aware"], ["group_name","n"]))
        story.append(Spacer(1, 8))

        # Integrity: missing formulations
        story.append(P("Formulations with missing fields (route/form/strength) — top offenders", H2))
        story.append(TableFromRows(clamp(a["forms_missing"], FM_LIMIT), ["med_id","inn","n_missing"]))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_doc(out, "WHO ESSENTIAL MEDICINES — AUDIT & INTEGRITY", None, flow, ai_obj=ai_obj)

if __name__ == "__main__":
    import sys
    out = OUT
    env = lambda k: os.getenv(k,"").lower() in ("1","true","yes","on")
    use_ai = ("--ai" in sys.argv) or env("AI")
    brief  = ("--brief" in sys.argv) or env("BRIEF")
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out")+1]
    main(out, use_ai=use_ai, brief=brief)
