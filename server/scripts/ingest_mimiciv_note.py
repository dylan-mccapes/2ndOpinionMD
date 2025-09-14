#!/usr/bin/env python3
# server/scripts/ingest_mimiciv_note.py
import argparse, csv, gzip, os, sys
from pathlib import Path
from typing import Optional, List, Tuple
import psycopg2
from psycopg2.extras import execute_values

CAND_TEXT   = ["text", "note_text", "report", "report_text", "notes", "note"]
CAND_TIME   = ["charttime", "note_time", "note_datetime", "report_time", "chart_date", "chart_datetime", "studydatetime"]
CAND_STUDY  = ["study_id", "parent_study_id", "report_id"]
REQUIRED    = ["note_id", "subject_id"]  # hadm_id may be null for some radiology rows

def open_reader(p: Path) -> csv.DictReader:
    f = gzip.open(p, "rt", encoding="utf-8", newline="") if p.suffix == ".gz" else open(p, "r", encoding="utf-8", newline="")
    return csv.DictReader(f)

def pick_key(fieldnames: List[str], candidates: List[str]) -> Optional[str]:
    fset = {fn.lower(): fn for fn in (fieldnames or [])}
    for k in candidates:
        if k in fset:
            return fset[k]
    return None

def upsert_batch(cur, rows: List[Tuple]):
    sql = """
    INSERT INTO text.mimiciv_notes (note_id, domain, subject_id, hadm_id, study_id, charttime, note_text)
    VALUES %s
    ON CONFLICT (note_id) DO UPDATE SET
      domain     = EXCLUDED.domain,
      subject_id = COALESCE(EXCLUDED.subject_id, text.mimiciv_notes.subject_id),
      hadm_id    = COALESCE(EXCLUDED.hadm_id, text.mimiciv_notes.hadm_id),
      study_id   = COALESCE(EXCLUDED.study_id, text.mimiciv_notes.study_id),
      charttime  = COALESCE(EXCLUDED.charttime, text.mimiciv_notes.charttime),
      note_text  = COALESCE(NULLIF(EXCLUDED.note_text,''), text.mimiciv_notes.note_text);
    """
    execute_values(cur, sql, rows, page_size=1000)

def load_one(conn, path: Path, domain: str) -> int:
    if not path.exists():
        return 0
    n = 0
    with conn, conn.cursor() as cur:
        reader = open_reader(path)
        fns = reader.fieldnames or []
        # Validate required columns
        for rk in REQUIRED:
            if rk not in [x.lower() for x in fns]:
                raise RuntimeError(f"{path} missing required column '{rk}'; headers={fns}")

        # Map canonical keys (case-insensitive)
        fset = {fn.lower(): fn for fn in fns}
        note_id_k = fset["note_id"]
        subj_k    = fset["subject_id"]
        hadm_k    = fset.get("hadm_id")
        text_k    = pick_key(fns, CAND_TEXT)
        time_k    = pick_key(fns, CAND_TIME)
        study_k   = pick_key(fns, CAND_STUDY)

        batch = []
        for row in reader:
            note_id = row.get(note_id_k)
            if not note_id:
                continue
            subj    = row.get(subj_k)
            hadm    = row.get(hadm_k) if hadm_k else None
            study   = row.get(study_k) if study_k else None
            ctime   = row.get(time_k) if time_k else None
            text    = row.get(text_k) or ""

            # Casts (safely ignore errors -> store as NULL)
            try:    subj = int(subj) if subj else None
            except: subj = None
            try:    hadm = int(hadm) if hadm else None
            except: hadm = None
            try:    study = int(study) if study else None
            except: study = None
            # ctime stays as string; Postgres will cast if ISO-like; else NULL
            if ctime and ctime.strip() == "":
                ctime = None

            batch.append((note_id, domain, subj, hadm, study, ctime, text))
            if len(batch) >= 5000:
                upsert_batch(cur, batch); n += len(batch); batch.clear()

        if batch:
            upsert_batch(cur, batch); n += len(batch)

    return n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True,
                    help="Root of mimic-iv-note/2.2 (e.g., physionet.org/files/mimic-iv-note/2.2). Will also look under ./note/")
    ap.add_argument("--dsn", default="dbname=2ndopinionmd")
    args = ap.parse_args()

    root = Path(args.dir)
    base = root / "note" if (root / "note").exists() else root

    discharge  = base / "discharge.csv"
    discharge_gz = base / "discharge.csv.gz"
    radiology  = base / "radiology.csv"
    radiology_gz = base / "radiology.csv.gz"

    conn = psycopg2.connect(args.dsn)
    total = 0
    total += load_one(conn, discharge_gz if discharge_gz.exists() else discharge, "discharge")
    total += load_one(conn, radiology_gz if radiology_gz.exists() else radiology, "radiology")
    conn.close()
    print(f"Imported/updated {total} MIMIC-IV notes.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ingest_mimiciv_note] ERROR: {e}", file=sys.stderr)
        sys.exit(1)

