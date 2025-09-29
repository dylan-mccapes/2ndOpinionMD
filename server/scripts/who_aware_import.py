#!/usr/bin/env python3
import argparse, os, sys, re, json
import pandas as pd
import psycopg2

DSN = os.environ.get("SYNC_DATABASE_URL") or os.environ.get("DATABASE_URL")
if not DSN:
    print("DATABASE_URL or SYNC_DATABASE_URL not set", file=sys.stderr); sys.exit(2)

GROUP_ALIASES = {
    "a":"Access","access":"Access",
    "w":"Watch","watch":"Watch",
    "r":"Reserve","reserve":"Reserve",
}

def norm_group(v):
    if v is None: return None
    s = re.sub(r"[^A-Za-z]", "", str(v)).lower()
    return GROUP_ALIASES.get(s) or (s.title() if s in ("access","watch","reserve") else None)

J01_RE = re.compile(r"\bJ01[A-Z0-9]{3,5}\b", re.I)

def _excel_file(path):
    try:
        return pd.ExcelFile(path, engine="openpyxl")
    except Exception:
        return pd.ExcelFile(path, engine="calamine")

def _sheet_group(sheet_name: str) -> str|None:
    s = sheet_name.lower()
    if "access" in s:  return "Access"
    if "watch" in s:   return "Watch"
    if "reserve" in s: return "Reserve"
    return None

def _row_group(rowvals) -> str|None:
    t = " ".join(str(v) for v in rowvals if pd.notna(v)).lower()
    if "access" in t:  return "Access"
    if "reserve" in t: return "Reserve"
    if "watch" in t:   return "Watch"
    return None

def _codes_in_row(rowvals):
    text = " | ".join(str(v) for v in rowvals if pd.notna(v))
    return [c.upper() for c in J01_RE.findall(text)]

def load_mapping(path: str, sheet: str|None = None):
    xls = _excel_file(path)
    wanted = [sheet] if sheet else [s for s in xls.sheet_names
                                    if any(k in s.lower() for k in
                                           ("aware", "access", "watch", "reserve"))]
    mapping: dict[str,str] = {}
    counts = {"Access":0,"Watch":0,"Reserve":0}
    parsed_sheets = []

    for sh in wanted:
        try:
            df = xls.parse(sh, header=None, dtype=str)
        except Exception as e:
            print(f"[who_aware_import] WARN: failed to read sheet {sh}: {e}", file=sys.stderr)
            continue

        sheet_grp = _sheet_group(sh)
        got_codes = 0
        for _, row in df.iterrows():
            codes = _codes_in_row(row.values.tolist())
            if not codes: continue
            grp = sheet_grp or _row_group(row.values.tolist())
            grp = norm_group(grp)
            if not grp: continue
            for code in codes:
                mapping[code] = grp
                counts[grp] += 1
                got_codes += 1

        parsed_sheets.append((sh, got_codes, sheet_grp or "mixed"))

    return mapping, counts, parsed_sheets

def ensure_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS guidelines.who_aware_map (
          atc_code   text PRIMARY KEY,
          group_name text,
          src        text,
          raw        jsonb,
          updated_at timestamptz DEFAULT now()
        );
        """)
        # Ensure columns exist even if table predated new schema
        cur.execute("ALTER TABLE guidelines.who_aware_map ADD COLUMN IF NOT EXISTS src text;")
        cur.execute("ALTER TABLE guidelines.who_aware_map ADD COLUMN IF NOT EXISTS raw jsonb;")
        cur.execute("ALTER TABLE guidelines.who_aware_map ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now();")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS who_aware_map_atc_code_uidx ON guidelines.who_aware_map(atc_code);")
        cur.execute("CREATE INDEX IF NOT EXISTS who_aware_group_idx ON guidelines.who_aware_map(group_name);")
    conn.commit()

def upsert_map(conn, items):
    n=0
    with conn.cursor() as cur:
        for atc, grp in items:
            cur.execute("""
              INSERT INTO guidelines.who_aware_map(atc_code, group_name, src, raw)
              VALUES (%s,%s,'xlsx',%s)
              ON CONFLICT (atc_code) DO UPDATE
                SET group_name=EXCLUDED.group_name,
                    src='xlsx',
                    raw=EXCLUDED.raw,
                    updated_at=now()
            """, (atc, grp, json.dumps({"source":"xlsx"})))
            n+=1
    conn.commit()
    return n

def main(path: str, sheet: str|None):
    mapping, counts, parsed = load_mapping(path, sheet)
    if not mapping:
        print(f"[who_aware_import] No mappings found. Sheets considered: {parsed}", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(DSN)
    try:
        ensure_table(conn)
        n = upsert_map(conn, mapping.items())
        print(f"[who_aware_import] Upserted {n} rows from {path}")
        print(f"[who_aware_import] A:{counts['Access']} W:{counts['Watch']} R:{counts['Reserve']}")
        for sh, got, mode in parsed:
            print(f"[who_aware_import]  - {sh} ({mode}) -> rows with codes: {got}")
    finally:
        conn.close()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="Path to WHO AWaRe XLSX (2025)")
    ap.add_argument("--sheet", default=None, help="Optional: Access | Watch | Reserve | AWaRe classification 2025")
    args = ap.parse_args()
    main(args.file, args.sheet)
