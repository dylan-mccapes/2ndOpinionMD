#!/usr/bin/env python3
import argparse, csv, gzip, os, sys
from pathlib import Path
from datetime import datetime
import psycopg2
import psycopg2.extras as pxe

def open_any(path: Path):
    if not path or not path.exists(): return None
    return gzip.open(path, "rt", encoding="utf-8", newline="") if path.suffix == ".gz" \
           else open(path, "r", encoding="utf-8", newline="")

def parse_charttime(row, fields_lower):
    t = None
    for k in ("charttime","chart_time","chartdate","chart_date"):
        if k in fields_lower:
            t = row.get(k) or None; break
    if not t: return None
    t = t.strip()
    if not t: return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try: return datetime.strptime(t, fmt)
        except ValueError: pass
    try:
        return datetime.fromisoformat(t.replace("Z","+00:00")).replace(tzinfo=None)
    except Exception:
        return None

def get_note_text(row, fields_lower):
    for k in ("text","note_text","report","radiology_report","TEXT"):
        if k in fields_lower: return row.get(k) or ""
    return ""

def _upsert(cur, batch):
    sql = """
        INSERT INTO text.mimiciv_notes
          (note_id, domain, subject_id, hadm_id, charttime, note_text)
        VALUES %s
        ON CONFLICT (note_id) DO UPDATE SET
          domain     = EXCLUDED.domain,
          subject_id = EXCLUDED.subject_id,
          hadm_id    = EXCLUDED.hadm_id,
          charttime  = COALESCE(EXCLUDED.charttime, text.mimiciv_notes.charttime),
          note_text  = EXCLUDED.note_text
    """
    pxe.execute_values(cur, sql, batch, page_size=2000)
    return len(batch)

def load_domain(conn, domain: str, csv_path: Path, min_len: int, limit: int | None):
    f = open_any(csv_path)
    if not f:
        print(f"  {domain}: not found -> {csv_path}", file=sys.stderr)
        return 0, 0
    reader = csv.DictReader(f)
    fields = [c.strip() for c in (reader.fieldnames or [])]
    fields_lower = [c.lower() for c in fields]

    ins, skipped, batch = 0, 0, []
    with conn, conn.cursor() as cur:
        for i, row in enumerate(reader, start=1):
            note_id = row.get("note_id") or row.get("NOTE_ID") or ""
            if not note_id:
                skipped += 1
                if limit and i >= limit: break
                continue
            try: subject_id = int(row.get("subject_id") or 0) or None
            except Exception: subject_id = None
            try: hadm_id = int(row.get("hadm_id") or 0) or None
            except Exception: hadm_id = None
            charttime = parse_charttime(row, set(fields_lower))
            note_text = get_note_text(row, set(fields_lower))
            if min_len and (not note_text or len(note_text) < min_len):
                if limit and i >= limit: break
                continue
            batch.append((note_id, domain, subject_id, hadm_id, charttime, note_text))
            if len(batch) >= 2000:
                ins += _upsert(cur, batch); batch.clear()
            if limit and i >= limit: break
        if batch:
            ins += _upsert(cur, batch)
    f.close()
    return ins, skipped

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="Root of mimic-iv-note (e.g., physionet.org/files/mimic-iv-note/2.2)")
    ap.add_argument("--min-length", type=int, default=0)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dbname", default=os.getenv("PGDATABASE","2ndopinionmd"))
    ap.add_argument("--dbuser", default=os.getenv("PGUSER",None))
    ap.add_argument("--dbhost", default=os.getenv("PGHOST",None))
    ap.add_argument("--dbport", default=os.getenv("PGPORT",None))
    args = ap.parse_args()

    root = Path(args.dir)
    note_dir = root / "note"
    files = {
        "discharge": next((p for p in [note_dir/"discharge.csv.gz", note_dir/"discharge.csv"] if p.exists()), None),
        "radiology": next((p for p in [note_dir/"radiology.csv.gz", note_dir/"radiology.csv"] if p.exists()), None),
    }
    print(" Looking for files:")
    for k, v in files.items():
        print(f"  - {k}: {v if v else '(missing)'}")

    dsn = [f"dbname={args.dbname}"]
    if args.dbuser: dsn.append(f"user={args.dbuser}")
    if args.dbhost: dsn.append(f"host={args.dbhost}")
    if args.dbport: dsn.append(f"port={args.dbport}")
    conn = psycopg2.connect(" ".join(dsn))

    total = 0
    for domain, p in files.items():
        if not p: continue
        print(f"  Importing {domain} from {p} ...")
        ins, skipped = load_domain(conn, domain, p, args.min_length, args.limit)
        total += ins
        print(f"   {domain}: upserted {ins} rows (skipped {skipped} without note_id).")

    conn.close()
    print(f" Imported/updated {total} MIMIC-IV notes.")

if __name__ == "__main__":
    main()

