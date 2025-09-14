#!/usr/bin/env python3
# server/scripts/extract_ap_pairs_from_mimic.py
import os
import re
import sys
import argparse
import psycopg2
import psycopg2.extras as extras
from datetime import datetime
from typing import List, Tuple, Optional

# ----------------------------
# Helpers: DB
# ----------------------------
def get_conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        # fall back to local
        dsn = "postgresql://localhost/2ndopinionmd"
    return psycopg2.connect(dsn)

def safe_span_text(note_text: str | None, start, end) -> str | None:
    if note_text is None:
        return None
    try:
        s = int(start)
        e = int(end)
    except (TypeError, ValueError):
        return None
    if s < 0:
        s = 0
    if e is None or e <= s:
        return None
    n = len(note_text)
    if s >= n:
        return None
    e = min(e, n)
    chunk = note_text[s:e].strip()
    return chunk if chunk else None

# ----------------------------
# Heuristics: A&P parsing
# ----------------------------
HDR_ASSESS = re.compile(
    r"(?mi)^\s*(assessment(?:\s*and\s*plan)?|a\s*/\s*p|a\s*&\s*p)\s*:?\s*$"
)
HDR_PLAN = re.compile(
    r"(?mi)^\s*(plan|plans)\s*:?\s*$"
)

# starts of plan items (bullets, numbers, lettered, "Problem:" headings, etc.)
PLAN_SPLIT = re.compile(
    r"(?m)^(?=\s*(?:[-*]\s+|\d+[\.\)]\s+|\([a-zA-Z]\)\s+|[A-Z][A-Za-z0-9/ &\-]{2,40}:\s+))"
)

def find_headers(text: str) -> Tuple[Optional[re.Match], Optional[re.Match]]:
    a = None
    p = None
    for m in HDR_ASSESS.finditer(text):
        a = m
        break
    for m in HDR_PLAN.finditer(text):
        # first plan that comes after assessment if assessment exists; else the first plan
        if a is None or m.start() > a.start():
            p = m
            break
    return a, p

def split_plan_items(plan_body: str) -> List[Tuple[int, int]]:
    """
    Return list of (start,end) spans (relative to plan_body) for plan items.
    """
    spans = []
    starts = [m.start() for m in PLAN_SPLIT.finditer(plan_body)]
    if not starts:
        # treat entire plan as one item if non-empty
        stripped = plan_body.strip()
        if stripped:
            return [(0, len(plan_body))]
        return []
    starts.append(len(plan_body))
    for i in range(len(starts) - 1):
        s, e = starts[i], starts[i + 1]
        # trim whitespace at both ends
        while s < e and plan_body[s].isspace():
            s += 1
        while e > s and plan_body[e - 1].isspace():
            e -= 1
        if e > s:
            spans.append((s, e))
    return spans

# ----------------------------
# Extract one note
# ----------------------------
def extract_note_ap_pairs(note_text: str) -> Tuple[Optional[Tuple[int,int]], List[Tuple[int,int]]]:
    """
    Returns:
      assessment_span (start,end) in original text or None,
      plan_item_spans  list of (start,end) in original text
    """
    if not note_text or len(note_text) < 200:
        return None, []

    a_hdr, p_hdr = find_headers(note_text)
    if not a_hdr and not p_hdr:
        return None, []

    # Determine assessment region
    if a_hdr:
        a_start = a_hdr.end()
        # end where plan header begins, or next header, or until blank gap then plan header
        a_end = len(note_text)
        if p_hdr and p_hdr.start() > a_start:
            a_end = p_hdr.start()
        # trim
        while a_start < a_end and note_text[a_start].isspace():
            a_start += 1
        while a_end > a_start and note_text[a_end - 1].isspace():
            a_end -= 1
        assessment_span = (a_start, a_end) if a_end > a_start else None
    else:
        assessment_span = None

    # Determine plan region
    plan_spans: List[Tuple[int,int]] = []
    if p_hdr:
        p_start = p_hdr.end()
        p_end = len(note_text)
        # try to stop at common next major header (e.g., "Discharge:", "Hospital Course:")
        NEXT_HDR = re.compile(r"(?mi)^\s*[A-Z][A-Za-z ]{2,40}:\s*$")
        nxt = NEXT_HDR.search(note_text, p_start)
        if nxt:
            p_end = nxt.start()
        # tidy
        while p_start < p_end and note_text[p_start].isspace():
            p_start += 1
        while p_end > p_start and note_text[p_end - 1].isspace():
            p_end -= 1
        if p_end > p_start:
            local = note_text[p_start:p_end]
            for s_rel, e_rel in split_plan_items(local):
                plan_spans.append((p_start + s_rel, p_start + e_rel))

    return assessment_span, plan_spans

# ----------------------------
# Insert helpers
# ----------------------------
def upsert_note(cur, track, external_id, subject_id, hadm_id, charttime, note_text,
                split=None, filename=None):
    cur.execute(
        """
        INSERT INTO text.n2c2_notes
          (track, split, filename, external_id, note_text, token_ct, created_at,
           subject_id, hadm_id, charttime)
        VALUES
          (%s, COALESCE(%s, 0), %s, %s, %s, length(%s), NOW(),
           %s, %s, %s)
        ON CONFLICT (track, external_id) DO UPDATE SET
          note_text = EXCLUDED.note_text,
          token_ct  = EXCLUDED.token_ct,
          subject_id= EXCLUDED.subject_id,
          hadm_id   = EXCLUDED.hadm_id,
          charttime = EXCLUDED.charttime
        RETURNING note_id;
        """,
        (track, split, filename, external_id, note_text, note_text,
         subject_id, hadm_id, charttime)
    )
    return cur.fetchone()[0]

def insert_section(cur, note_id, section_name, span_start, span_end, note_text):
    txt = safe_span_text(note_text, span_start, span_end)
    if not txt:
        return None
    cur.execute(
        """
        INSERT INTO text.n2c2_ap_sections
            (note_id, section_name, span_start, span_end, text)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (note_id, section_name, span_start, span_end)
        DO UPDATE SET text = EXCLUDED.text
        RETURNING section_id;
        """,
        (note_id, section_name, span_start, span_end, txt),
    )
    return cur.fetchone()[0]

def insert_relation(cur, note_id: int, assess_id: int, plan_id: int, track: str, label: str | None = None):
    # default everything auto-mined to Silver unless you pass a gold label
    lbl = label or "Silver"
    cur.execute(
        """
        INSERT INTO text.n2c2_ap_relations (note_id, assess_id, plan_id, label)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (note_id, assess_id, plan_id)
        DO UPDATE SET label = COALESCE(EXCLUDED.label, text.n2c2_ap_relations.label)
        RETURNING rel_id;
        """,
        (note_id, assess_id, plan_id, lbl),
    )
    return cur.fetchone()[0]

# ----------------------------
# Sources
# ----------------------------
# --- MIMIC-III (discharge summaries) ---
# --- MIMIC-III (discharge summaries) ---
# --- MIMIC-III (discharge summaries) ---
M3_SQL = """
SELECT
  row_id::text  AS external_id,
  subject_id,
  hadm_id,
  charttime,
  text         AS note_text
FROM text.mimic3_notes
WHERE category = 'Discharge summary'
ORDER BY random()
LIMIT %s;
"""

# --- MIMIC-IV-Note (default to discharge) ---
MIV_SQL = """
SELECT
  note_id             AS external_id,
  subject_id,
  hadm_id,
  charttime,
  note_text
FROM text.mimiciv_notes
WHERE domain = %s
ORDER BY random()
LIMIT %s;
"""

def fetch_notes(cur, source, limit, domain=None):
    if source == "m3":
        cur.execute(M3_SQL, (limit,))
        return cur.fetchall()
    elif source == "miv":
        cur.execute(MIV_SQL, ((domain or "discharge"), limit))
        return cur.fetchall()
    else:
        raise ValueError("source must be 'm3' or 'miv'")

# ----------------------------
# Main
# ----------------------------
def main():
    ap = argparse.ArgumentParser(description="Extract silver A&P pairs from MIMIC")
    ap.add_argument("--source", choices=["m3", "miv"], required=True, help="m3 for MIMIC-III, miv for MIMIC-IV-Note")
    ap.add_argument("--limit", type=int, default=20000, help="number of notes to sample")
    ap.add_argument("--track", type=str, default=None, help="track name to store (default: MIII-AP or MIV-AP)")
    ap.add_argument("--domain", type=str, default="discharge", help="MIMIC-IV domain filter (e.g., discharge)")
    args = ap.parse_args()

    track = args.track or ("MIII-AP" if args.source == "m3" else "MIV-AP")

    conn = get_conn()
    conn.autocommit = False
    cur = conn.cursor()

    notes = fetch_notes(cur, args.source, args.limit, args.domain if args.source == "miv" else None)

    n_notes = 0
    n_assess = 0
    n_plan = 0
    n_rels = 0

    for external_id, subject_id, hadm_id, charttime, note_text in notes:
        assessment_span, plan_spans = extract_note_ap_pairs(note_text)
        if not assessment_span or not plan_spans:
            continue

        n_notes += 1
        note_id = upsert_note(cur, track, external_id, subject_id, hadm_id, charttime, note_text)

        a_s, a_e = assessment_span
        assess_id = insert_section(cur, note_id, "ASSESSMENT", a_s, a_e, note_text)
        if not assess_id:
            continue
        n_assess += 1

        for p_s, p_e in plan_spans:
            plan_id = insert_section(cur, note_id, "PLAN_ITEM", p_s, p_e, note_text)
            if not plan_id:
                continue
            n_plan += 1
            insert_relation(cur, note_id, assess_id, plan_id, track, label="Silver")
            n_rels += 1

        # commit per note to keep memory/locks low
        conn.commit()

    print(f"Processed notes: {n_notes}")
    print(f"Assessments:    {n_assess}")
    print(f"Plan items:     {n_plan}")
    print(f"Relations:      {n_rels}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()

