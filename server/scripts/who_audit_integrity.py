#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WHO EML / AWaRe / Committee — Audit & Integrity Report

Outputs a Markdown report (and optional JSON) with:
- row counts by list_type/edition/year
- AWaRe coverage for antibacterials (ATC J01) and mismatches vs who_aware_map
- invalid/missing fields (ATC, ICD-11, formulations)
- duplicate med_keys, orphans, and alt_inn linkability
- committee & RAG coverage (who_eml/who_committee) + missing embeddings
- presence of expected GIN/IVFFLAT indexes

Usage:
  PYTHONPATH=. DATABASE_URL=... \
  python server/scripts/who_audit_integrity.py \
     --md server/reports/who_audit.md \
     --json server/reports/who_audit.json
"""
import os, re, json, argparse, datetime
import psycopg2
from psycopg2.extras import RealDictCursor

DSN = (os.environ.get("SYNC_DATABASE_URL") or os.environ.get("DATABASE_URL") or "").replace("+asyncpg","")
if not DSN:
    raise SystemExit("Set DATABASE_URL or SYNC_DATABASE_URL")

def q1(cur, sql, params=None):
    cur.execute(sql, params or ())
    row = cur.fetchone()
    return dict(row) if row else {}

def qn(cur, sql, params=None):
    cur.execute(sql, params or ())
    return [dict(r) for r in cur.fetchall()]

def detect_aware_group_col(cur):
    cur.execute("""
      SELECT column_name FROM information_schema.columns
      WHERE table_schema='guidelines' AND table_name='who_aware_map'
    """)
    rows = cur.fetchall()
    cols = set()
    for r in rows:
        if isinstance(r, dict):
            cols.add(r.get("column_name"))
        elif isinstance(r, (list, tuple)):
            cols.add(r[0])
        else:
            try:
                cols.add(r[0])
            except Exception:
                pass
    if "group_name" in cols:  return "group_name"
    if "group" in cols:       return '"group"'
    return None

def main(md_out: str|None, json_out: str|None):
    out = {"generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')}

    with psycopg2.connect(DSN, cursor_factory=RealDictCursor) as conn:
        with conn.cursor() as cur:
            aware_group_col = detect_aware_group_col(cur)

            # --- High-level counts ---
            out["counts"] = q1(cur, """
              SELECT
                COUNT(*)::int                                         AS n_meds,
                COUNT(*) FILTER (WHERE list_type='EML')::int          AS n_eml,
                COUNT(*) FILTER (WHERE list_type='EMLc')::int         AS n_emlc,
                COALESCE((SELECT COUNT(*) FROM guidelines.who_eml_atc),0)::int     AS n_atc,
                COALESCE((SELECT COUNT(*) FROM guidelines.who_eml_icd11),0)::int   AS n_icd11,
                COALESCE((SELECT COUNT(*) FROM guidelines.who_eml_formulations),0)::int AS n_forms,
                COALESCE((SELECT COUNT(*) FROM guidelines.who_eml_alternatives),0)::int AS n_alts
              FROM guidelines.who_eml_medicines
            """)

            # Edition/year spread
            out["editions"] = qn(cur, """
              SELECT year, edition, list_type, COUNT(*)::int AS n
              FROM guidelines.who_eml_medicines
              GROUP BY 1,2,3 ORDER BY year DESC, edition DESC, list_type
            """)

            # --- Antibacterials (J01) + AWaRe coverage ---
            out["aware"] = {}
            out["aware"]["coverage"] = q1(cur, """
              WITH j01 AS (
                SELECT DISTINCT m.med_id, m.antibiotic_group
                FROM guidelines.who_eml_medicines m
                JOIN guidelines.who_eml_atc a ON a.med_id=m.med_id
                WHERE a.atc_code ILIKE 'J01%%'
              )
              SELECT
                (SELECT COUNT(*) FROM j01)::int AS n_j01_meds,
                (SELECT COUNT(*) FROM j01 WHERE COALESCE(antibiotic_group,'')<>'')::int AS n_with_group
            """)

            # Mappings present?
            if aware_group_col:
                out["aware"]["unmapped_atc"] = qn(cur, f"""
                  SELECT DISTINCT a.atc_code
                  FROM guidelines.who_eml_atc a
                  WHERE a.atc_code ILIKE 'J01%%'
                    AND NOT EXISTS (
                      SELECT 1 FROM guidelines.who_aware_map w
                      WHERE w.atc_code = a.atc_code
                    )
                  ORDER BY 1
                  LIMIT 50
                """)

                # Per-medicine derived group from mapping vs stored antibiotic_group
                out["aware"]["mismatches"] = qn(cur, f"""
                  WITH per_med AS (
                    SELECT m.med_id, m.inn, m.antibiotic_group AS stored_group,
                           MIN(CASE WHEN w.{aware_group_col} IS NULL THEN NULL ELSE w.{aware_group_col} END) AS mapped_group
                    FROM guidelines.who_eml_medicines m
                    JOIN guidelines.who_eml_atc a ON a.med_id=m.med_id AND a.atc_code ILIKE 'J01%%'
                    LEFT JOIN guidelines.who_aware_map w ON w.atc_code=a.atc_code
                    GROUP BY m.med_id, m.inn, m.antibiotic_group
                  )
                  SELECT med_id, inn, stored_group, mapped_group
                  FROM per_med
                  WHERE (mapped_group IS NOT NULL AND stored_group IS DISTINCT FROM mapped_group)
                        OR (mapped_group IS NOT NULL AND (stored_group IS NULL OR stored_group=''))
                  ORDER BY inn
                  LIMIT 50
                """)
            else:
                out["aware"]["note"] = "guidelines.who_aware_map present but no recognizable group col (expected group_name or \"group\")."

            # --- Integrity: ATC/ICD/forms/dupes/alt linkability ---
            out["integrity"] = {}
            out["integrity"]["invalid_atc"] = qn(cur, r"""
              SELECT atc_code, COUNT(*)::int AS n
              FROM guidelines.who_eml_atc
              WHERE atc_code !~ '^[A-Z][0-9]{2}[A-Z]{2}[0-9]{2}$'
                 OR LENGTH(atc_code) NOT IN (5,7)  -- allow shorter oddities; flag anyway
              GROUP BY 1 ORDER BY n DESC, atc_code LIMIT 50
            """)

            out["integrity"]["icd11_suspect"] = qn(cur, r"""
              SELECT icd11_code, COUNT(*)::int AS n
              FROM guidelines.who_eml_icd11
              WHERE icd11_code ~ '[^A-Z0-9\.\-_]' OR LENGTH(icd11_code)>10
                    OR icd11_code IN ('', 'NULL')
              GROUP BY 1 ORDER BY n DESC LIMIT 50
            """)

            out["integrity"]["formulations_missing"] = qn(cur, """
              SELECT med_id, COUNT(*)::int AS n
              FROM guidelines.who_eml_formulations
              WHERE COALESCE(dose_form,'')='' OR COALESCE(strength,'')=''
              GROUP BY 1 ORDER BY n DESC LIMIT 50
            """)

            out["integrity"]["duplicate_med_keys"] = qn(cur, """
              SELECT med_key, COUNT(*)::int AS n
              FROM guidelines.who_eml_medicines
              GROUP BY 1 HAVING COUNT(*)>1
              ORDER BY n DESC LIMIT 50
            """)

            out["integrity"]["alt_inn_unmatched"] = qn(cur, """
              WITH all_inn AS (SELECT DISTINCT inn FROM guidelines.who_eml_medicines)
              SELECT alt_inn, COUNT(*)::int AS n
              FROM guidelines.who_eml_alternatives al
              WHERE NOT EXISTS (SELECT 1 FROM all_inn WHERE inn ILIKE alt_inn)
              GROUP BY 1 ORDER BY n DESC, alt_inn LIMIT 50
            """)

            # --- Committee & RAG coverage ---
            out["committee"] = q1(cur, """
              SELECT
                (SELECT COUNT(*) FROM guidelines.who_committee_reports)::int  AS n_reports,
                (SELECT COUNT(*) FROM guidelines.who_committee_sections)::int AS n_sections
            """)

            out["rag"] = q1(cur, """
              SELECT
                COUNT(*) FILTER (WHERE source='who_eml')::int        AS n_who_eml_rows,
                COUNT(*) FILTER (WHERE source='who_committee')::int   AS n_who_committee_rows,
                COUNT(*) FILTER (WHERE source='who_eml' AND embedding IS NULL)::int        AS n_who_eml_missing_emb,
                COUNT(*) FILTER (WHERE source='who_committee' AND embedding IS NULL)::int   AS n_who_committee_missing_emb
              FROM public.rag_corpus
            """)

            # --- Index checks (GIN on ts; ANN on rag_corpus) ---
            out["indexes"] = {}
            out["indexes"]["who_eml_ts_gin"] = qn(cur, """
              SELECT indexname FROM pg_indexes
              WHERE schemaname='guidelines' AND tablename='who_eml_medicines'
                AND indexdef ILIKE '% USING gin % (ts %'
            """)
            out["indexes"]["who_committee_ts_gin"] = qn(cur, """
              SELECT indexname FROM pg_indexes
              WHERE schemaname='guidelines' AND tablename='who_committee_sections'
                AND indexdef ILIKE '% USING gin % (ts %'
            """)
            out["indexes"]["rag_ann_who"] = qn(cur, """
              SELECT indexname, indexdef
              FROM pg_indexes
              WHERE schemaname='public' AND tablename='rag_corpus'
                AND indexdef ILIKE '%USING ivfflat%' AND indexdef ILIKE '% WHERE source=''who_%'' %'
            """)

    # -------- Markdown ----------
    md = []
    md.append(f"# WHO EML / AWaRe / Committee — Audit & Integrity\n")
    md.append(f"_Generated: {out['generated_at']}_\n")

    c = out["counts"]
    md.append("## High-level counts\n")
    md.append(f"- Medicines: **{c.get('n_meds',0)}** (EML {c.get('n_eml',0)}, EMLc {c.get('n_emlc',0)})\n"
              f"- ATC rows: {c.get('n_atc',0)}, ICD-11 rows: {c.get('n_icd11',0)}, Formulations: {c.get('n_forms',0)}, Alternatives: {c.get('n_alts',0)}\n")

    md.append("\n### Editions present\n")
    for row in out["editions"]:
        md.append(f"- {row['year']} — edition {row['edition']} {row['list_type']}: {row['n']}\n")

    aware = out["aware"]
    cov = aware["coverage"]
    md.append("\n## AWaRe (Antibacterials J01)\n")
    md.append(f"- J01 medicines: **{cov.get('n_j01_meds',0)}**; with antibiotic_group set: **{cov.get('n_with_group',0)}**\n")
    if aware.get("unmapped_atc") is not None:
        unm = [r['atc_code'] for r in aware["unmapped_atc"]]
        md.append(f"- Unmapped J01 ATC codes in who_aware_map (showing up to 50): {', '.join(unm) if unm else 'none'}\n")
    if aware.get("mismatches") is not None:
        mm = aware["mismatches"]
        md.append(f"- Medicine-level AWaRe mismatches (top 50): {len(mm)}\n")
        for r in mm[:10]:
            md.append(f"  - {r['inn']} (med_id {r['med_id']}): stored='{r['stored_group']}', mapped='{r['mapped_group']}'")

    integ = out["integrity"]
    def md_list(title, rows, key):
        md.append(f"\n## {title}\n")
        if not rows:
            md.append("- none\n"); return
        for r in rows[:10]:
            if isinstance(key, str):
                md.append(f"- {r.get(key)} (n={r.get('n',1)})")
            else:
                md.append("- " + ", ".join(f"{k}={r.get(k)}" for k in key))

    md_list("Invalid ATC codes", integ["invalid_atc"], "atc_code")
    md_list("Suspect ICD-11 codes", integ["icd11_suspect"], "icd11_code")
    md_list("Formulations missing fields (med_id → count)", integ["formulations_missing"], None)
    md_list("Duplicate med_keys", integ["duplicate_med_keys"], "med_key")
    md_list("Alternatives not matching any known INN", integ["alt_inn_unmatched"], "alt_inn")

    md.append("\n## Committee & RAG\n")
    md.append(f"- Committee: reports={out['committee'].get('n_reports',0)}, sections={out['committee'].get('n_sections',0)}\n")
    md.append(f"- RAG who_eml rows={out['rag'].get('n_who_eml_rows',0)} (missing_emb={out['rag'].get('n_who_eml_missing_emb',0)}); "
              f"who_committee rows={out['rag'].get('n_who_committee_rows',0)} (missing_emb={out['rag'].get('n_who_committee_missing_emb',0)})\n")

    md.append("\n## Index checks\n")
    md.append(f"- who_eml_medicines.ts GIN: {'OK' if out['indexes']['who_eml_ts_gin'] else 'MISSING'}\n")
    md.append(f"- who_committee_sections.ts GIN: {'OK' if out['indexes']['who_committee_ts_gin'] else 'MISSING'}\n")
    md.append(f"- rag_corpus IVFFLAT (WHO sources): {'OK' if out['indexes']['rag_ann_who'] else 'MISSING'}\n")

    md_text = "\n".join(md).strip()

    if md_out:
        os.makedirs(os.path.dirname(md_out), exist_ok=True)
        with open(md_out, "w", encoding="utf-8") as f:
            f.write(md_text)

    if json_out:
        os.makedirs(os.path.dirname(json_out), exist_ok=True)
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)

    print(md_text)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default="server/reports/who_audit.md")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    main(args.md, args.json)

