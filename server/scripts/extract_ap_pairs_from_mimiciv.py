#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract Assessment & Plan (A&P) pairs from clinical notes and store them in:
  - text.n2c2_notes
  - text.n2c2_ap_sections
  - text.n2c2_ap_relations

Sources:
  --source m3 -> reads text.v_mimic3_progress_notes
  --source m4 -> reads text.v_mimiciv_progress_notes

Expected source views (create beforehand):
  CREATE OR REPLACE VIEW text.v_mimic3_progress_notes AS
  SELECT row_id AS ext_note_id, subject_id, hadm_id, charttime,
         COALESCE(category,'Unknown') AS category, text AS note_text
  FROM text.mimic3_notes
  WHERE text IS NOT NULL AND length(text) > 200
    AND (lower(category) LIKE '%physician%' OR lower(category) LIKE '%discharge%');

  -- For MIMIC-IV, point to your unified notes table/view:
  -- ext_note_id TEXT/INT, subject_id INT, hadm_id INT, charttime TIMESTAMP,
  -- category TEXT (or domain), note_text TEXT
  CREATE OR REPLACE VIEW text.v_mimiciv_progress_notes AS
  SELECT note_id AS ext_note_id, subject_id, hadm_id, charttime,
         COALESCE(domain,'Unknown') AS category, note_text
  FROM text.mimiciv_notes
  WHERE note_text IS NOT NULL AND length(note_text) > 200
    AND (lower(domain) IN ('discharge','radiology') OR lower(category) LIKE '%physician%');

Notes:
  - Requires psycopg2.
  - Uses idempotent inserts:
      * Sections: ON CONFLICT (note_id, section_name, span_start, span_end) ... UPDATE "text"
      * Relations: ON CONFLICT (note_id, assess_id, plan_id, label) DO NOTHING
  - We deliberately SELECT (track, external_id) to get-or-create the note_id so this works
    even if text.n2c2_notes lacks a unique constraint on that pair.
"""

import argparse
import re
import sys
from typing import List, Tuple, Optional

import psycopg2


# ---------- Config / Heuristics ----------

# Track names well write into text.n2c2_notes.track to distinguish sources
TRACK_M3 = "MIII-AP"
TRACK_M4 = "MIV-AP"

# Regexes to find Assessment/Plan headers and plan bullets
RE_ASSESS_HDR = re.compile(r'(?im)^\s*assessment\s*[:\-]\s*$')
RE_PLAN_HDR   = re.compile(r'(?im)^\s*plan\s*[:\-]\s*$')
RE_AP_BLOCK   = re.compile(r'(?im)^\s*(assessment\s*(?:and)?\s*plan|a\s*/\s*p)\s*[:\-]?\s*$')

# Plan item: list markers (#, -, , digits., (a) ) or a headline-like line ending with ":".
RE_PLAN_ITEM = re.compile(
    r'(?m)^\s*(?:[#*\-\u2022]|\d+\.|\([a-zA-Z0-9]\)|[A-Z][A-Za-z0-9 \-/]{2,80}:)\s*(.*?)(?:$)',
)

# Heads that are almost always administrative/non-clinical  label "Not Relevant"
NONCLIN_HEADS = [
    "code status", "diet", "dvt prophylaxis", "ppi prophylaxis", "gi prophylaxis",
    "dispo", "disposition", "case management", "communication", "family communication",
    "lines", "drains", "tubes", "devices", "access", "fluids", "electrolytes",
    "glucose", "precautions", "isolation", "nursing", "activity", "nutrition",
    "ppx", "prn", "prophylaxis",
]


# ---------- Helpers ----------

def find_sections(note: str) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
    """
    Return (a_start, a_end, p_start, p_end) character offsets in note.
    Strategy:
      1) Prefer explicit "Assessment:" + "Plan:" headers.
      2) Fall back to an "Assessment/Plan" block (AP) if present.
    """
    a = RE_ASSESS_HDR.search(note)
    p = RE_PLAN_HDR.search(note)
    if a and p:
        a_start = a.end()
        a_end = p.start()
        p_start = p.end()
        p_end = len(note)
        if a_end <= a_start:  # degenerate weirdness
            a_end = min(len(note), a_start + 1)
        return a_start, a_end, p_start, p_end

    ap = RE_AP_BLOCK.search(note)
    if ap:
        a_start = ap.end()
        a_end = len(note)
        # No explicit plan header. We'll treat "plan" as everything after the assessment text,
        # and split plan items from that trailing region.
        return a_start, a_end, None, None

    return None, None, None, None


def extract_plan_items(plan_text: str) -> List[Tuple[int, int, str]]:
    """
    Split PLAN text into items based on bullets / numbered lists / headline lines.
    Returns list of (local_start, local_end, head_text).
    If nothing matches, return single item with entire plan_text.
    """
    items: List[Tuple[int, int, str]] = []
    last_end = 0
    for m in RE_PLAN_ITEM.finditer(plan_text):
        s, e = m.span()
        # push previous chunk if any content between markers
        if s > last_end:
            # previous free text chunk  ignore as head, but keep span as item if sizable
            pass
        head = (m.group(0) or "").strip()
        # local item span: from marker start to next marker or end; here naive line span
        # Well treat the line itself as the item; many plans are one-line heads w/ trailing details.
        items.append((s, e, head))
        last_end = e

    if not items and plan_text.strip():
        items = [(0, len(plan_text), plan_text.splitlines()[0][:120])]

    return items


def is_nonclinical(head: str) -> bool:
    h = head.lower()
    return any(h.startswith(k) or f" {k}" in h for k in NONCLIN_HEADS)


def direct_overlap(assessment: str, head: str) -> bool:
    """
    Extremely simple lexical overlap heuristic:
      - exact substring OR
      - any token of length >= 5 appears in assessment
    """
    a = assessment.lower()
    h = head.lower()
    if h and h in a:
        return True
    for tok in re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{4,}", h):
        if tok in a:
            return True
    return False


def clamp(s: int, e: int, n: int) -> Tuple[int, int]:
    """Clamp [s,e) to [0,n]."""
    s2 = max(0, min(s, n))
    e2 = max(0, min(e, n))
    if e2 < s2:
        e2 = s2
    return s2, e2


# ---------- Core ----------

def upsert_note_and_get_id(cur, track: str, ext_id: str, category: str, text: str) -> int:
    """
    Get-or-create a note row in text.n2c2_notes, keyed by (track, external_id).
    We SELECT first to avoid dup inserts when no unique constraint exists.
    """
    cur.execute(
        "SELECT note_id FROM text.n2c2_notes WHERE track=%s AND external_id=%s LIMIT 1",
        (track, ext_id),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute(
        """
        INSERT INTO text.n2c2_notes(track, split, source_system, external_id, filename, note_text)
        VALUES (%s, 'all', %s, %s, %s, %s)
        RETURNING note_id
        """,
        (track, "MIMIC-IV" if track == TRACK_M4 else "MIMIC-III", ext_id, category or "note", text or ""),
    )
    return cur.fetchone()[0]


def upsert_section_and_get_id(cur, note_id: int, name: str, s: int, e: int, txt: str) -> int:
    """
    Insert section; on conflict, update "text" only if the incoming text is non-empty.
    Requires a unique index on (note_id, section_name, span_start, span_end).
    """
    cur.execute(
        """
        INSERT INTO text.n2c2_ap_sections (note_id, section_name, span_start, span_end, "text")
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (note_id, section_name, span_start, span_end)
        DO UPDATE SET "text" = COALESCE(NULLIF(EXCLUDED."text", ''), text.n2c2_ap_sections."text")
        RETURNING section_id
        """,
        (note_id, name, s, e, txt or ""),
    )
    return cur.fetchone()[0]


def insert_relation(cur, note_id: int, assess_id: int, plan_id: int, label: str) -> None:
    """
    Insert relation; ignore duplicates.
    Requires unique index on (note_id, assess_id, plan_id, label).
    """
    cur.execute(
        """
        INSERT INTO text.n2c2_ap_relations (note_id, assess_id, plan_id, label)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (note_id, assess_id, plan_id, label) DO NOTHING
        """,
        (note_id, assess_id, plan_id, label),
    )


def process_rows(cur, rows, track: str, limit: int) -> Tuple[int, int, int]:
    """
    rows: iterable of (ext_note_id, subject_id, hadm_id, charttime, category, note_text)
    Returns counts (notes, sections, relations).
    """
    insN = insS = insR = 0

    for i, (ext_id, _subj, _hadm, _ct, category, note_text) in enumerate(rows):
        if limit and i >= limit:
            break
        if not note_text:
            continue

        # 1) get/create note
        note_id = upsert_note_and_get_id(cur, track, str(ext_id), category, note_text)
        insN += 1

        # 2) find A/P regions
        a_s, a_e, p_s, p_e = find_sections(note_text)
        if a_s is None:
            # no A/P detected; skip
            continue

        # clamp to avoid OOB on substr() later
        a_s, a_e = clamp(a_s, a_e, len(note_text))

        # 3) upsert ASSESSMENT section
        assess_txt = note_text[a_s:a_e]
        assess_id = upsert_section_and_get_id(cur, note_id, "ASSESSMENT", a_s, a_e, assess_txt)
        insS += 1

        # 4) plan region
        if p_s is not None:
            p_region = note_text[p_s:p_e]
            base = p_s
        else:
            p_region = note_text[a_e:]
            base = a_e

        # 5) split into plan items and classify
        for s_loc, e_loc, head in extract_plan_items(p_region):
            g_s, g_e = clamp(base + s_loc, base + e_loc, len(note_text))
            plan_txt = note_text[g_s:g_e]

            # initial silver label
            if is_nonclinical(head):
                label = "Not Relevant"
            elif direct_overlap(assess_txt, head):
                label = "Direct"
            else:
                # We dont try to auto-emit "Indirect" in the baseline heuristic.
                label = "Neither"

            plan_id = upsert_section_and_get_id(cur, note_id, "PLAN_ITEM", g_s, g_e, plan_txt)
            insS += 1

            insert_relation(cur, note_id, assess_id, plan_id, label)
            insR += 1

    return insN, insS, insR


# ---------- Entry Point ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default="dbname=2ndopinionmd", help="psycopg2 DSN, e.g., 'dbname=2ndopinionmd'")
    ap.add_argument("--source", choices=["m3", "m4"], default="m3",
                    help="m3 = MIMIC-III view text.v_mimic3_progress_notes; m4 = MIMIC-IV view text.v_mimiciv_progress_notes")
    ap.add_argument("--limit", type=int, default=20000, help="max notes to process (0 = no limit)")
    args = ap.parse_args()

    track = TRACK_M3 if args.source == "m3" else TRACK_M4
    src_view = "text.v_mimic3_progress_notes" if args.source == "m3" else "text.v_mimiciv_progress_notes"

    conn = psycopg2.connect(args.dsn)
    conn.autocommit = False
    cur = conn.cursor()

    # Pull rows from the chosen view
    if args.limit and args.limit > 0:
        cur.execute(f"SELECT ext_note_id, subject_id, hadm_id, charttime, category, note_text FROM {src_view} LIMIT %s", (args.limit,))
    else:
        cur.execute(f"SELECT ext_note_id, subject_id, hadm_id, charttime, category, note_text FROM {src_view}")

    rows = cur.fetchall()
    n, s, r = process_rows(cur, rows, track, args.limit or 0)
    conn.commit()
    cur.close()
    conn.close()

    print(f"Inserted/updated notes {n}, sections {s}, relations {r} (track={track}, source={src_view})")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[extract_ap_pairs_from_mimiciv] ERROR: {e}", file=sys.stderr)
        sys.exit(1)

