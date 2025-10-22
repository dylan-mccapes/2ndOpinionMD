#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ingest ClinGen Clinical Actionability (ACI) exports.

It supports two kinds of TSVs per cohort (Adult, Pediatric):
  1) SCORES  : per-domain rows with final/prelim component scores
  2) STATUS/ASSERTIONS : rows with suggested / preliminary / consensus assertions

We normalize headers, parse integers robustly (e.g., "7 (High)" -> 7),
insert into clingen.actionability_assertions, and refresh the MV
clingen.v_actionability_latest.

Assumptions about DB schema (already created by database/schemas/clingen_aci.sql):
  Table clingen.actionability_assertions has (nullable) columns:
    cohort, assertion_type, domain, intervention, outcome, score, rationale,
    gene_symbol, hgnc_id, disease_name, disease_mondo_id,
    assertion, report_date, source_url
"""

from __future__ import annotations

import csv
import os
import re
import sys
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

import psycopg2


# ---------- constants / dirs ----------

HERE = os.path.abspath(os.path.dirname(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA_DIR = os.path.abspath(os.path.join(REPO_ROOT, "..", "data", "clingen"))

COHORTS = ("Adult", "Pediatric")

# Columns that define a TRUE scoring file (after normalization)
SCORE_KEYS = (
    "final_overall",
    "final_severity",
    "final_likelihood",
    "final_natureofintervention",
    "final_effectiveness",
)

# Columns that indicate assertion/status files
STATUS_KEYS = (
    "suggestedassertion",
    "preliminaryassertion",
    "consensusassertion",
    "status_assertion",
    "status_overall",
    "status_stg1",
)


# ---------- utilities ----------

def norm(s: str) -> str:
    """normalize header -> snake, alnum + underscore"""
    return re.sub(r"[^a-z0-9]+", "_", s.strip().lower()).strip("_")


def to_int_or_none(x) -> Optional[int]:
    """
    Extract an integer even if the cell has text like '7 (High)' or 'NA'.
    Returns None if no integer is present.
    """
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    m = re.search(r"[-+]?\d+", s)
    if not m:
        return None
    try:
        return int(m.group(0))
    except Exception:
        return None


def first_nonempty(*vals) -> Optional[str]:
    for v in vals:
        if v is None:
            continue
        s = str(v).strip()
        if s != "":
            return s
    return None


def parse_date_or_none(s: Optional[str]) -> Optional[str]:
    """Return ISO date (YYYY-MM-DD) or None."""
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    # Try a few common forms
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    # Last resort: keep as-is if it looks like a date prefix
    m = re.match(r"^\d{4}-\d{2}-\d{2}", s)
    if m:
        return m.group(0)
    return None


def load_tsv(path: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """Read TSV returning (normalized_headers, rows-with-normalized-keys)."""
    with open(path, "rt", encoding="utf-8", newline="") as f:
        rdr = csv.reader(f, delimiter="\t")
        raw_header = next(rdr)
        # Skip optional comment marker in col0 like "# docId"
        header = [h.lstrip("# ").strip() for h in raw_header]
        nheader = [norm(h) for h in header]

    rows: List[Dict[str, str]] = []
    with open(path, "rt", encoding="utf-8", newline="") as f:
        dr = csv.DictReader(f, delimiter="\t")
        # normalize dict keys
        for r in dr:
            nr = {}
            for k, v in r.items():
                if k is None:
                    continue
                nk = norm(k.lstrip("# "))
                nr[nk] = v
            rows.append(nr)
    return nheader, rows


def detect_file_kind(headers: List[str]) -> str:
    """
    Return 'scores' or 'assertions' based on header content.

    Tight rules:
      - SCORES: must contain at least TWO of SCORE_KEYS (true per-domain scoring files)
      - ASSERTIONS: has any STATUS_KEYS or the assertion columns
      - Otherwise 'unknown' (ignore)
    """
    h = set(headers)

    n_finals = sum(1 for k in SCORE_KEYS if k in h)
    if n_finals >= 2:
        return "scores"

    if any(k in h for k in STATUS_KEYS):
        return "assertions"

    # older assertion/status sometimes only have the assertion fields:
    if any(k in h for k in ("suggestedassertion", "preliminaryassertion", "consensusassertion")):
        return "assertions"

    return "unknown"


# ---------- record builders ----------

def rec_from_scores(row: Dict[str, str], cohort: str) -> Dict[str, object]:
    """
    Build a DB row from a SCORES TSV line.
    """
    # robust domain/outcome/intervention headers
    outcome = first_nonempty(
        row.get("outcome"),
    )
    domain = first_nonempty(
        row.get("outcomescoringgroup"),
        row.get("outcome_scoring_group"),
    )
    intervention = first_nonempty(
        row.get("intervention"),
    )

    # Primary score: final_overall; robustly parse, then fall back to sums.
    score_int = to_int_or_none(row.get("final_overall"))
    if score_int is None:
        finals = [
            to_int_or_none(row.get("final_severity")),
            to_int_or_none(row.get("final_likelihood")),
            to_int_or_none(row.get("final_natureofintervention")),
            to_int_or_none(row.get("final_effectiveness")),
        ]
        if any(v is not None for v in finals):
            score_int = sum(v for v in finals if v is not None)
    if score_int is None:
        prelims = [
            to_int_or_none(row.get("prelim_severity")),
            to_int_or_none(row.get("prelim_likelihood")),
            to_int_or_none(row.get("prelim_natureofintervention")),
            to_int_or_none(row.get("prelim_effectiveness")),
        ]
        if any(v is not None for v in prelims):
            score_int = sum(v for v in prelims if v is not None)

    report_date = parse_date_or_none(
        first_nonempty(row.get("lastupdated"), row.get("releasedate"))
    )

    return {
        "cohort": cohort,
        "assertion_type": None,
        "domain": domain,
        "intervention": intervention,
        "outcome": outcome,
        "score": score_int,
        "rationale": None,
        "gene_symbol": first_nonempty(row.get("geneorvariant"), row.get("gene")),
        "hgnc_id": first_nonempty(row.get("geneomim"), row.get("hgnc_id")),  # sometimes empty
        "disease_name": first_nonempty(row.get("disease")),
        "disease_mondo_id": first_nonempty(row.get("mondo")),
        "assertion": None,
        "report_date": report_date,
        "source_url": first_nonempty(row.get("iri")),
    }


def rec_from_assertions(row: Dict[str, str], cohort: str) -> Dict[str, object]:
    """
    Build a DB row from ASSERTIONS/STATUS TSV line.
    """
    # choose best available assertion, and tag its type
    assertion_fields = [
        ("consensus", row.get("consensusassertion")),
        ("preliminary", row.get("preliminaryassertion")),
        ("suggested", row.get("suggestedassertion")),
    ]
    a_type = None
    a_val = None
    for t, v in assertion_fields:
        if v and str(v).strip():
            a_type, a_val = t, str(v).strip()
            break

    report_date = parse_date_or_none(
        first_nonempty(row.get("lastupdated"))
    )

    return {
        "cohort": cohort,
        "assertion_type": a_type,
        "domain": None,
        "intervention": None,
        "outcome": None,
        "score": None,
        "rationale": None,
        "gene_symbol": first_nonempty(row.get("geneorvariant"), row.get("gene")),
        "hgnc_id": first_nonempty(row.get("geneomim"), row.get("hgnc_id")),
        "disease_name": first_nonempty(row.get("disease")),
        "disease_mondo_id": first_nonempty(row.get("mondo")),
        "assertion": a_val,
        "report_date": report_date,
        "source_url": first_nonempty(row.get("iri")),
    }


# ---------- DB ----------

def connect():
    dsn = os.environ.get("SYNC_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR: SYNC_DATABASE_URL (or DATABASE_URL) is not set", file=sys.stderr)
        sys.exit(2)
    return psycopg2.connect(dsn)


def bulk_insert(cur, rows: Iterable[Dict[str, object]]) -> int:
    rows = list(rows)
    if not rows:
        return 0
    cols = [
        "cohort", "assertion_type", "domain", "intervention", "outcome", "score",
        "rationale", "gene_symbol", "hgnc_id", "disease_name", "disease_mondo_id",
        "assertion", "report_date", "source_url",
    ]
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"""
        INSERT INTO clingen.actionability_assertions
        ({", ".join(cols)})
        VALUES ({placeholders})
    """
    data = []
    for r in rows:
        data.append(tuple(r.get(c) for c in cols))
    cur.executemany(sql, data)
    return len(rows)


def refresh_materialized(cur) -> int:
    # We assume MV exists per schema file
    cur.execute("REFRESH MATERIALIZED VIEW clingen.v_actionability_latest;")
    # Count rows
    cur.execute("SELECT COUNT(*) FROM clingen.v_actionability_latest;")
    return int(cur.fetchone()[0])


# ---------- file resolution ----------

def find_candidate_paths() -> List[str]:
    """Collect likely TSVs in DATA_DIR."""
    if not os.path.isdir(DATA_DIR):
        return []
    out = []
    for name in os.listdir(DATA_DIR):
        if name.lower().endswith(".tsv"):
            out.append(os.path.join(DATA_DIR, name))
    return sorted(out)


def resolve_files_content_based() -> Dict[Tuple[str, str], Optional[str]]:
    """
    Returns a dict mapping (kind, cohort) -> path or None
    where kind in {"scores","assertions"} and cohort in COHORTS.
    We read a line of each file and detect kind by headers, then assign
    Adult/Pediatric by reading either 'context' or presence in filename,
    else fallback by load order (first Adult, second Pediatric).
    """
    cand = find_candidate_paths()
    buckets = {"scores": {"Adult": None, "Pediatric": None},
               "assertions": {"Adult": None, "Pediatric": None}}

    scores_unknown: List[str] = []
    asserts_unknown: List[str] = []

    for path in cand:
        try:
            headers, _ = load_tsv(path)
        except Exception:
            continue
        kind = detect_file_kind(headers)
        if kind == "unknown":
            continue

        # Try to infer cohort: header 'context' or by filename
        cohort = None
        try:
            _, rows = load_tsv(path)
            if rows:
                ctx = first_nonempty(rows[0].get("context"))
                if ctx and ctx.lower().startswith("adult"):
                    cohort = "Adult"
                elif ctx and ctx.lower().startswith("pediatric"):
                    cohort = "Pediatric"
        except Exception:
            pass

        if cohort is None:
            low = os.path.basename(path).lower()
            if "adult" in low:
                cohort = "Adult"
            elif "pediatric" in low:
                cohort = "Pediatric"

        if cohort in COHORTS:
            if buckets[kind][cohort] is None:
                buckets[kind][cohort] = path
        else:
            if kind == "scores":
                scores_unknown.append(path)
            else:
                asserts_unknown.append(path)

    # Assign unknowns in stable order: first -> Adult, second -> Pediatric
    for kind, unknowns in (("scores", scores_unknown), ("assertions", asserts_unknown)):
        u = [p for p in unknowns if p is not None]
        if u and buckets[kind]["Adult"] is None:
            buckets[kind]["Adult"] = u[0]
        if len(u) >= 2 and buckets[kind]["Pediatric"] is None:
            buckets[kind]["Pediatric"] = u[1]

    return {(k, c): buckets[k][c] for k in ("scores", "assertions") for c in COHORTS}


# ---------- main ----------

def main():
    files = resolve_files_content_based()
    print("ACI file resolution (content-based):")
    for key in (("assertions", "Adult"), ("assertions", "Pediatric"),
                ("scores", "Adult"), ("scores", "Pediatric")):
        print(f"  {key} -> {files.get(key)}")

    with connect() as conn:
        conn.autocommit = False
        cur = conn.cursor()

        inserted_total = 0
        per_kind_counts = {"Adult": {"scores": 0, "assertions": 0},
                           "Pediatric": {"scores": 0, "assertions": 0}}

        for cohort in COHORTS:
            # SCORES
            spath = files.get(("scores", cohort))
            if spath and os.path.exists(spath):
                print(f"→ Loading SCORES for {cohort} from {spath}")
                _, srows = load_tsv(spath)
                recs = [rec_from_scores(r, cohort) for r in srows]
                per_kind_counts[cohort]["scores"] = bulk_insert(cur, recs)
                inserted_total += per_kind_counts[cohort]["scores"]
            else:
                print(f"⚠ No scores file found for {cohort}")

            # ASSERTIONS
            apath = files.get(("assertions", cohort))
            if apath and os.path.exists(apath):
                print(f"→ Loading ASSERTIONS for {cohort} from {apath}")
                _, arows = load_tsv(apath)
                recs = [rec_from_assertions(r, cohort) for r in arows]
                per_kind_counts[cohort]["assertions"] = bulk_insert(cur, recs)
                inserted_total += per_kind_counts[cohort]["assertions"]
            else:
                print(f"⚠ No assertions/status file found for {cohort}")

        # Commit inserts
        conn.commit()

        # Sanity prints
        cur.execute("""
            SELECT
              COUNT(*) AS total,
              COUNT(*) FILTER (WHERE domain IS NOT NULL) AS have_domain,
              COUNT(*) FILTER (WHERE outcome IS NOT NULL) AS have_outcome,
              COUNT(*) FILTER (WHERE score IS NOT NULL)  AS have_score,
              COUNT(*) FILTER (WHERE assertion IS NOT NULL) AS have_assertion
            FROM clingen.actionability_assertions
        """)
        totals = cur.fetchone()

        mv_rows = refresh_materialized(cur)
        conn.commit()

    print(
        "✓ Adult: loaded {scores} score rows, {assertions} assertion/status rows".format(
            **per_kind_counts["Adult"]
        )
    )
    print(
        "✓ Pediatric: loaded {scores} score rows, {assertions} assertion/status rows".format(
            **per_kind_counts["Pediatric"]
        )
    )
    print(
        "Sanity (actionability_assertions): "
        f"{tuple(int(x) for x in totals)}"
    )
    print(f"v_actionability_latest rows: {mv_rows}")
    print(f"✅ Loaded {inserted_total} actionability rows (scores + assertions)")


if __name__ == "__main__":
    main()
