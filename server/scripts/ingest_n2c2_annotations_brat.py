#!/usr/bin/env python3
import os, re, argparse, psycopg2
from psycopg2.extras import execute_batch

ENTITY_RE   = re.compile(r'^(T\d+)\t([^\s]+)\s+(\d+)\s+(\d+)\t(.*)$')
RELATION_RE = re.compile(r'^(R\d+)\t([^\s]+)\s+Arg1:(T\d+)\s+Arg2:(T\d+)\s*$')
ATTR_RE     = re.compile(r'^(A\d+)\t([^\s]+)\s+(T\d+)(?:\s+(.*))?$')

def get_db_url():
    return (os.getenv("DATABASE_URL") or "postgresql:///2ndopinionmd").replace("+asyncpg","")

def derive_note_id_from_path(path: str) -> str:
    """
    Map an .ann file to the note_id used in text.n2c2_notes.
    Typical layouts use sibling .txt with the same stem.
    If your notes table stores full filenames, keep the stem only,
    and align during ingest of notes.
    """
    stem = os.path.splitext(os.path.basename(path))[0]
    return stem  # adjust if your note_id is track+stem, etc.

def rows_from_ann(path: str):
    note_id = derive_note_id_from_path(path)
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            m = ENTITY_RE.match(line)
            if m:
                ann_id, label, s, e, txt = m.groups()
                rows.append((ann_id, note_id, "entity", label, int(s), int(e), txt, None, None, None, None, path))
                continue
            m = RELATION_RE.match(line)
            if m:
                ann_id, label, a1, a2 = m.groups()
                rows.append((ann_id, note_id, "relation", label, None, None, None, a1, a2, None, None, path))
                continue
            m = ATTR_RE.match(line)
            if m:
                ann_id, label, target, value = m.groups()
                rows.append((ann_id, note_id, "attribute", label, None, None, None, None, None, target, (value or "").strip(), path))
                continue
            # Non-standard line → store as attribute blob (fallback)
            ann_id = f"X{abs(hash(line))}"
            rows.append((ann_id, note_id, "attribute", "RAW", None, None, line, None, None, None, None, path))
    return rows

def iter_ann_files(root: str):
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if fn.lower().endswith(".ann"):
                yield os.path.join(dirpath, fn)

def main():
    ap = argparse.ArgumentParser(description="Ingest BRAT .ann annotations into text.n2c2_annotations")
    ap.add_argument("--dir", required=True, help="Directory containing *.ann files")
    args = ap.parse_args()

    url = get_db_url()
    conn = psycopg2.connect(url)
    try:
        with conn, conn.cursor() as cur:
            sql = """
            INSERT INTO text.n2c2_annotations
              (ann_id, note_id, kind, label, span_start, span_end, span_text, arg1, arg2, attr_target, attr_value, source_file)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (ann_id) DO NOTHING
            """
            batch = []
            for path in iter_ann_files(args.dir):
                batch.extend(rows_from_ann(path))
                if len(batch) >= 5000:
                    execute_batch(cur, sql, batch, page_size=1000)
                    batch.clear()
            if batch:
                execute_batch(cur, sql, batch, page_size=1000)
        print("✅ Annotations import complete.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()

