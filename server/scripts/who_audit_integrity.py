#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WHO EML / AWaRe / Expert Committee audit + integrity report.

Env:
  - SYNC_DATABASE_URL or DATABASE_URL (psycopg2 DSN). "+asyncpg" suffix removed automatically.

Outputs:
  --json : machine-readable summary
  --md   : human-readable Markdown

Usage:
  python server/scripts/who_audit_integrity.py \
    --md server/reports/who_audit.md \
    --json server/reports/who_audit.json
"""
from __future__ import annotations
import argparse, os, json, datetime, sys
from pathlib import Path

import psycopg2
import psycopg2.extras

# ---------- DSN ----------
def get_dsn() -> str:
    dsn = os.environ.get("SYNC_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("Set SYNC_DATABASE_URL or DATABASE_URL")
    return dsn.replace("+asyncpg", "")

# ---------- SQL helpers ----------
def q(cur, sql: str, params=None):
    if params is None or params == () or params == {}:
        cur.execute(sql)
    else:
        cur.execute(sql, params)
    return cur.fetchall()

def q1(cur, sql: str, params=None, default=0):
    rows = q(cur, sql, params)
    if not rows:
        return default
    row = rows[0]
    # first value of dict row or first column
    if isinstance(row, dict):
        return next(iter(row.values()))
    return row[0] if isinstance(row, (list, tuple)) else default

def table_exists(cur, schema: str, table: str) -> bool:
    return bool(q1(cur, """
      SELECT 1 FROM information_schema.tables
      WHERE table_schema=%s AND table_name=%s
      LIMIT 1
    """, (schema, table), default=0))

def index_exists(cur, schema: str, index: str) -> bool:
    return bool(q1(cur, """
      SELECT 1 FROM pg_indexes
      WHERE schemaname=%s AND indexname=%s
      LIMIT 1
    """, (schema, index), default=0))

def detect_aware_group_col(cur) -> str | None:
    cols = q(cur, """
      SELECT column_name FROM information_schema.columns
      WHERE table_schema='guidelines' AND table_name='who_aware_map'
    """)
    names = { (r["column_name"] if isinstance(r, dict) else r[0]) for r in cols }
    if "group_name" in names: return "group_name"
    if "group" in names:      return '"group"'
    return None

def compute_verdict_and_warn_reasons(conn):
    """
    Compute audit verdict and warn_reasons for WHO EML.

    Returns:
      {
        "verdict": "OK" | "WARN",
        "warn_reasons": [str, ...],
        "stats": {
          "n_meds": int,
          "n_form": int,
          "n_icd11": int,
          "n_form_missing": int,
          "n_meds_with_missing": int,
          "n_committee_sections": int,
          "rag_eml_rows": int,
          "rag_committee_rows": int,
          "icd11_coverage": float
        }
      }
    """
    with conn.cursor() as cur:
        cur.execute("""
            WITH
            meds AS (SELECT COUNT(*)::int n FROM guidelines.who_eml_medicines),
            forms AS (SELECT COUNT(*)::int n FROM guidelines.who_eml_formulations),
            icd11 AS (SELECT COUNT(*)::int n FROM guidelines.who_eml_icd11),
            missing_form AS (
                SELECT COUNT(*)::int n,
                       COUNT(DISTINCT med_id)::int meds
                FROM guidelines.who_eml_formulations
                WHERE COALESCE(route,'')='' OR COALESCE(dose_form,'')='' OR COALESCE(strength,'')=''
            ),
            committee AS (SELECT COUNT(*)::int n FROM guidelines.who_committee_sections),
            rag_who_eml AS (
                SELECT COUNT(*)::int n FROM public.rag_corpus WHERE source='who_eml'
            ),
            rag_who_committee AS (
                SELECT COUNT(*)::int n FROM public.rag_corpus WHERE source='who_committee'
            )
            SELECT
                (SELECT n FROM meds)                        AS n_meds,
                (SELECT n FROM forms)                       AS n_form,
                (SELECT n FROM icd11)                       AS n_icd11,
                (SELECT n FROM missing_form)                AS n_form_missing,
                (SELECT meds FROM missing_form)             AS n_meds_with_missing,
                (SELECT n FROM committee)                   AS n_committee_sections,
                (SELECT n FROM rag_who_eml)                 AS rag_eml_rows,
                (SELECT n FROM rag_who_committee)           AS rag_committee_rows
            ;
        """)
        r = cur.fetchone()

    stats = {
        "n_meds": r[0] or 0,
        "n_form": r[1] or 0,
        "n_icd11": r[2] or 0,
        "n_form_missing": r[3] or 0,
        "n_meds_with_missing": r[4] or 0,
        "n_committee_sections": r[5] or 0,
        "rag_eml_rows": r[6] or 0,
        "rag_committee_rows": r[7] or 0,
    }
    # Coverage is how many meds have at least one ICD-11 mapping (table is 1 row per mapping)
    # If your icd11 table is 1 row per med (unique), this is exact; if multiple per med, it’s an upper bound.
    stats["icd11_coverage"] = (stats["n_icd11"] / stats["n_meds"]) if stats["n_meds"] else 0.0

    warn_reasons = []

    # Reason 1: Missing formulations (route/form/strength)
    if stats["n_form_missing"] > 0:
        warn_reasons.append(
            f"{stats['n_form_missing']} formulations have missing route/form/strength "
            f"across {stats['n_meds_with_missing']} medicines."
        )

    # Reason 2: Low ICD-11 coverage
    # Tune thresholds to your preference; chosen to match the current WARN signal you’re seeing.
    # We warn if either absolute mappings are very low, or % coverage is low.
    ABSOLUTE_MIN_FOR_OK = 25      # require at least this many mappings
    RELATIVE_MIN_FOR_OK = 0.10    # or at least 10% of meds mapped
    if stats["n_icd11"] < ABSOLUTE_MIN_FOR_OK or stats["icd11_coverage"] < RELATIVE_MIN_FOR_OK:
        warn_reasons.append(
            f"ICD-11 coverage is low ({stats['n_icd11']}/{stats['n_meds']} = "
            f"{stats['icd11_coverage']:.1%}); mappings may be incomplete."
        )

    # (Optional) Reason 3: Committee/RAG rows present but very small – informational, not a hard fail.
    # Uncomment if you want these to contribute to WARNs:
    # if stats["rag_eml_rows"] < stats["n_meds"]:
    #     warn_reasons.append(
    #         f"RAG corpus rows for who_eml ({stats['rag_eml_rows']}) are fewer than total medicines ({stats['n_meds']})."
    #     )

    verdict = "WARN" if warn_reasons else "OK"

    return {
        "verdict": verdict,
        "warn_reasons": warn_reasons,
        "stats": stats,
    }

try:
    import psycopg
    _PSYCOPG3 = True
except ImportError:  # pragma: no cover
    import psycopg2 as psycopg
    _PSYCOPG3 = False


def _open_conn():
    dsn = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("SYNC_DATABASE_URL")
        or "dbname=2ndopinionmd"
    )
    if _PSYCOPG3:
        conn = psycopg.connect(dsn)
    else:
        conn = psycopg.connect(dsn)
    try:
        conn.autocommit = True
    except Exception:
        pass
    return conn


def _format_md(audit):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    v = audit["verdict"]
    badge = "🟡 WARN" if v == "WARN" else "✅ OK"
    s = audit["stats"]

    lines = []
    lines.append(f"# WHO EML Integrity Audit")
    lines.append("")
    lines.append(f"_Generated: {now}_")
    lines.append("")
    lines.append(f"**Verdict:** {badge}")
    lines.append("")
    if audit["warn_reasons"]:
        lines.append("**Reasons:**")
        for r in audit["warn_reasons"]:
            lines.append(f"- {r}")
        lines.append("")
    else:
        lines.append("**Reasons:** none")
        lines.append("")

    lines.append("## Key Stats")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Medicines | {s['n_meds']} |")
    lines.append(f"| Formulations | {s['n_form']} |")
    lines.append(f"| ICD-11 mappings | {s['n_icd11']} |")
    lines.append(f"| Missing formulations | {s['n_form_missing']} |")
    lines.append(f"| Medicines with any missing | {s['n_meds_with_missing']} |")
    lines.append(f"| Committee sections | {s['n_committee_sections']} |")
    lines.append(f"| RAG rows (who_eml) | {s['rag_eml_rows']} |")
    lines.append(f"| RAG rows (who_committee) | {s['rag_committee_rows']} |")
    lines.append(f"| ICD-11 coverage | {s['icd11_coverage']:.1%} |")
    lines.append("")
    return "\n".join(lines)


def _write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _write_md(path, md_text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(md_text)

# ---------- Audit ----------
def run_audit() -> dict:
    out = {"generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00","Z")}
    with psycopg2.connect(get_dsn(), cursor_factory=psycopg2.extras.RealDictCursor) as conn:
        with conn.cursor() as cur:
            # existence checks (don’t assume anything)
            have_eml     = table_exists(cur, "guidelines", "who_eml_medicines")
            have_atc     = table_exists(cur, "guidelines", "who_eml_atc")
            have_icd11   = table_exists(cur, "guidelines", "who_eml_icd11")
            have_forms   = table_exists(cur, "guidelines", "who_eml_formulations")
            have_commit  = table_exists(cur, "guidelines", "who_committee_sections")
            have_aware   = table_exists(cur, "guidelines", "who_aware_map")
            have_ragcorp = table_exists(cur, "public",     "rag_corpus")

            out["tables"] = {
                "who_eml_medicines": have_eml,
                "who_eml_atc": have_atc,
                "who_eml_icd11": have_icd11,
                "who_eml_formulations": have_forms,
                "who_committee_sections": have_commit,
                "who_aware_map": have_aware,
                "rag_corpus": have_ragcorp,
            }

            # counts (safe defaults)
            out["counts"] = {
                "n_meds":         q1(cur, "SELECT COUNT(*) FROM guidelines.who_eml_medicines") if have_eml else 0,
                "n_atc":          q1(cur, "SELECT COUNT(*) FROM guidelines.who_eml_atc") if have_atc else 0,
                "n_icd11":        q1(cur, "SELECT COUNT(*) FROM guidelines.who_eml_icd11") if have_icd11 else 0,
                "n_committee_sec":q1(cur, "SELECT COUNT(*) FROM guidelines.who_committee_sections") if have_commit else 0,
            }

            # rag corpus (by source) if present
            sources = {}
            missing = {}
            if have_ragcorp:
                for src in ("who_eml","who_committee"):
                    sources[f"n_{src}"] = q1(cur, "SELECT COUNT(*) FROM public.rag_corpus WHERE source=%s", (src,))
                # “missing” (heuristic): if a given source has zero rows, report everything “missing”
                missing["n_who_eml_missing"] = 0 if sources.get("n_who_eml",0) > 0 else out["counts"]["n_meds"]
                missing["n_who_committee_missing"] = 0 if sources.get("n_who_committee",0) > 0 else out["counts"]["n_committee_sec"]
            else:
                sources["n_who_eml"] = 0
                sources["n_who_committee"] = 0
                missing["n_who_eml_missing"] = out["counts"]["n_meds"]
                missing["n_who_committee_missing"] = out["counts"]["n_committee_sec"]

            out.update(sources)
            out.update(missing)

            # indexes we expect (best-effort)
            out["indexes"] = {
                "who_eml_ts_gin": index_exists(cur, "guidelines", "who_eml_medicines_ts_gin") if have_eml else False,
                "who_committee_sections_ts_gin": index_exists(cur, "guidelines", "who_committee_sections_ts_gin") if have_commit else False,
                # partial ANN indexes are installation-specific; detect loosely by name presence
                "rag_who_eml_ann": bool(q1(cur, "SELECT COUNT(*) FROM pg_indexes WHERE indexname ILIKE %s", ("%rag_corpus%who_eml%",))) if have_ragcorp else False,
                "rag_who_committee_ann": bool(q1(cur, "SELECT COUNT(*) FROM pg_indexes WHERE indexname ILIKE %s", ("%rag_corpus%who_committee%",))) if have_ragcorp else False,
            }

            # AWaRe coverage on antibacterials (J01*)
            aware = []
            if have_eml and have_atc:
                aware = q(cur, """
                  SELECT COALESCE(NULLIF(m.antibiotic_group,''),'(Unlabeled)') AS group_name,
                         COUNT(*)::int AS n
                  FROM guidelines.who_eml_medicines m
                  WHERE EXISTS (SELECT 1 FROM guidelines.who_eml_atc a WHERE a.med_id=m.med_id AND a.atc_code ILIKE 'J01%')
                  GROUP BY 1 ORDER BY 1
                """)
            out["aware_distribution"] = aware

            # integrity checks (very light)
            integ = {}

            if have_forms:
                integ["formulations_missing"] = q(cur, """
                  SELECT m.med_id, m.inn, COUNT(*)::int AS n_missing
                  FROM guidelines.who_eml_medicines m
                  JOIN guidelines.who_eml_formulations f ON f.med_id=m.med_id
                  WHERE (NULLIF(TRIM(COALESCE(f.dose_form,'')), '') IS NULL)
                     OR (NULLIF(TRIM(COALESCE(f.strength,'')), '') IS NULL)
                  GROUP BY m.med_id, m.inn
                  ORDER BY n_missing DESC, m.inn
                  LIMIT 50
                """)
            else:
                integ["formulations_missing"] = []

            out["integrity"] = integ

    return out

# ---------- Markdown ----------
def to_markdown(data: dict) -> str:
    md = []
    md.append("# WHO Audit & Integrity Report")
    md.append("")
    md.append(f"_Generated: {data.get('generated_at','')}_")
    md.append("")

    md.append("## Table presence")
    for k, v in (data.get("tables") or {}).items():
        md.append(f"- {k}: {'✅' if v else '❌'}")
    md.append("")

    md.append("## Counts")
    counts = data.get("counts") or {}
    md.append(f"- EML medicines: **{counts.get('n_meds',0)}**")
    md.append(f"- EML ATC links: **{counts.get('n_atc',0)}**")
    md.append(f"- EML ICD-11 links: **{counts.get('n_icd11',0)}**")
    md.append(f"- Committee sections: **{counts.get('n_committee_sec',0)}**")
    md.append("")

    md.append("## RAG corpus")
    md.append(f"- who_eml rows: **{data.get('n_who_eml',0)}**")
    md.append(f"- who_committee rows: **{data.get('n_who_committee',0)}**")
    md.append(f"- who_eml missing (heuristic): **{data.get('n_who_eml_missing',0)}**")
    md.append(f"- who_committee missing (heuristic): **{data.get('n_who_committee_missing',0)}**")
    md.append("")

    md.append("## Indexes")
    for k, v in (data.get("indexes") or {}).items():
        md.append(f"- {k}: {'✅' if v else '❌'}")
    md.append("")

    md.append("## AWaRe distribution (antibacterials J01*)")
    aware = data.get("aware_distribution") or []
    if not aware:
        md.append("- (none)")
    else:
        for r in aware:
            md.append(f"- {r.get('group_name','(unknown)')}: {r.get('n',0)}")
    md.append("")

    md.append("## Integrity checks")
    fm = (data.get("integrity") or {}).get("formulations_missing") or []
    md.append("### Formulations missing fields (top 50)")
    if not fm:
        md.append("- (none)")
    else:
        for r in fm:
            md.append(f"- med_id={r.get('med_id')} inn={r.get('inn')} missing_rows={r.get('n_missing')}")
    md.append("")

    return "\n".join(md)

# ---------- CLI ----------
def main(argv=None):
    parser = argparse.ArgumentParser(description="WHO EML audit")
    parser.add_argument("--json", default="server/reports/who_audit.json")
    parser.add_argument("--md",   default="server/reports/who_audit.md")
    args = parser.parse_args(argv)

    conn = _open_conn()
    audit = compute_verdict_and_warn_reasons(conn)

    _write_json(args.json, audit)
    print(f"Wrote {args.json}")
    _write_md(args.md, _format_md(audit))
    print(f"Wrote {args.md}")

    # Keep non-failing exit to not break Make; flip to non-zero if you want WARN to fail CI.
    # return 0 if audit["verdict"] == "OK" else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
