#!/usr/bin/env python3
import csv, argparse, psycopg2, pathlib, sys, re

TRACK = "2022-T3"

# ---------- helpers ----------
def pick(fieldnames, cands):
    lower = {c.lower(): c for c in fieldnames}
    for k in cands:
        if k.lower() in lower:
            return lower[k.lower()]
    return None

CANON = {
    "direct":"Direct", "indirect":"Indirect", "neither":"Neither",
    "not relevant":"Not Relevant", "not_relevant":"Not Relevant", "notrelevant":"Not Relevant",
}

def canon_label(s):
    if not s: return None
    return CANON.get(s.strip().lower(), s.strip().title())

def to_int(x):
    try: return int(re.sub(r"[^0-9]", "", (x or "")))
    except: return None

# ---------- load raw notes (optional) ----------
def load_raw_notes(conn, raw_path, split="sample"):
    inserted = 0
    idx = {}

    with open(raw_path, newline='', encoding='utf-8-sig') as f, conn, conn.cursor() as cur:
        r = csv.DictReader(f)
        if not r.fieldnames: return 0, {}

        rowid_col = pick(r.fieldnames, ["row id","rowid","row_id","id"])
        note_col  = pick(r.fieldnames, ["note","note_text","text","raw_note","rawtext"])
        if not (rowid_col and note_col): return 0, {}

        for row in r:
            rid = (row.get(rowid_col) or "").strip()
            txt = (row.get(note_col) or "").strip()
            if not rid or not txt: continue

            # get-or-create note by external_id
            cur.execute("SELECT note_id, note_text FROM text.n2c2_notes WHERE track=%s AND external_id=%s LIMIT 1",
                        (TRACK, rid))
            found = cur.fetchone()
            if found:
                note_id, note_text = found
                if not note_text:
                    cur.execute("UPDATE text.n2c2_notes SET note_text=%s WHERE note_id=%s",
                                (txt, note_id))
            else:
                cur.execute("""
                    INSERT INTO text.n2c2_notes(track,split,source_system,external_id,filename,note_text)
                    VALUES(%s,%s,%s,%s,%s,%s) RETURNING note_id
                """, (TRACK, split, "N2C2-SAMPLE", rid, pathlib.Path(raw_path).name, txt))
                note_id = cur.fetchone()[0]
            idx[rid] = (note_id, txt)
            inserted += 1

    return inserted, idx

# ---------- load offset/label pairs ----------
def load_pairs_with_offsets(conn, pairs_path, rid_index, split="sample"):
    insN = insS = insR = 0

    with open(pairs_path, newline='', encoding='utf-8-sig') as f, conn, conn.cursor() as cur:
        r = csv.DictReader(f)
        if not r.fieldnames: return 0,0,0

        rowid_col = pick(r.fieldnames, ["row id","rowid","row_id","id"])
        a_beg     = pick(r.fieldnames, ["assessment begin","assessment_begin","a begin","a_begin"])
        a_end     = pick(r.fieldnames, ["assessment end","assessment_end","a end","a_end"])
        p_beg     = pick(r.fieldnames, ["plansubsection begin","plan begin","plan_subsection begin","plansubsection_begin","plan_subsection_begin","p begin","p_begin"])
        p_end     = pick(r.fieldnames, ["plansubsection end","plan end","plan_subsection end","plansubsection_end","plan_subsection_end","p end","p_end"])
        lab_col   = pick(r.fieldnames, ["relation","label"])
        if not (rowid_col and a_beg and a_end and p_beg and p_end and lab_col):
            return 0,0,0

        for row in r:
            rid   = (row.get(rowid_col) or "").strip()
            label = canon_label(row.get(lab_col))
            if not rid or label not in CANON.values(): continue

            # get-or-create note by external_id
            if rid in rid_index:
                note_id, note_text = rid_index[rid]
            else:
                cur.execute("SELECT note_id, note_text FROM text.n2c2_notes WHERE track=%s AND external_id=%s LIMIT 1",
                            (TRACK, rid))
                found = cur.fetchone()
                if found:
                    note_id, note_text = found
                else:
                    cur.execute("""
                        INSERT INTO text.n2c2_notes(track,split,source_system,external_id,filename,note_text)
                        VALUES(%s,%s,%s,%s,%s,%s) RETURNING note_id
                    """, (TRACK, split, "N2C2-SAMPLE", rid, pathlib.Path(pairs_path).name, ""))
                    note_id = cur.fetchone()[0]
                    note_text = ""
                rid_index[rid] = (note_id, note_text)
                insN += 1  # counted as "created note placeholder"

            a_s, a_e = to_int(row.get(a_beg)), to_int(row.get(a_end))
            p_s, p_e = to_int(row.get(p_beg)), to_int(row.get(p_end))
            if a_s is None or a_e is None or p_s is None or p_e is None:
                continue

            def slice_or_empty(txt, s, e):
                return txt[s:e] if txt and 0 <= s < e <= len(txt) else ""

            a_txt = slice_or_empty(note_text, a_s, a_e)
            p_txt = slice_or_empty(note_text, p_s, p_e)

            # -- ASSESSMENT section (UPSERT)
            cur.execute("""
              INSERT INTO text.n2c2_ap_sections (note_id, section_name, span_start, span_end, "text")
              VALUES (%s, 'ASSESSMENT', %s, %s, %s)
              ON CONFLICT (note_id, section_name, span_start, span_end)
              DO UPDATE SET "text" = COALESCE(NULLIF(EXCLUDED."text", ''), text.n2c2_ap_sections."text")
              RETURNING section_id
            """, (note_id, a_s, a_e, a_txt))
            assess_id = cur.fetchone()[0]

            # -- PLAN_ITEM section (UPSERT)
            cur.execute("""
              INSERT INTO text.n2c2_ap_sections (note_id, section_name, span_start, span_end, "text")
              VALUES (%s, 'PLAN_ITEM', %s, %s, %s)
              ON CONFLICT (note_id, section_name, span_start, span_end)
              DO UPDATE SET "text" = COALESCE(NULLIF(EXCLUDED."text", ''), text.n2c2_ap_sections."text")
              RETURNING section_id
            """, (note_id, p_s, p_e, p_txt))
            plan_id = cur.fetchone()[0]
            insS += 2

            # Idempotent relation
            cur.execute("""
              INSERT INTO text.n2c2_ap_relations (note_id, assess_id, plan_id, label)
              VALUES (%s, %s, %s, %s)
              ON CONFLICT (note_id, assess_id, plan_id, label) DO NOTHING
            """, (note_id, assess_id, plan_id, label))
            insR += 1

    return insN, insS, insR

# ---------- main ----------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="dir containing n2c2_sample_raw.csv and/or offsets CSVs")
    ap.add_argument("--dsn", default="dbname=2ndopinionmd")
    ap.add_argument("--split", default="sample")
    args = ap.parse_args()

    base = pathlib.Path(args.base)
    if not base.exists():
        print(f"Base dir not found: {base}", file=sys.stderr); sys.exit(1)

    conn = psycopg2.connect(args.dsn)

    # 1) raw notes (optional)
    rid_index = {}
    raw = base / "n2c2_sample_raw.csv"
    if raw.exists():
        _, rid_index = load_raw_notes(conn, raw, split=args.split)

    # 2) pairs/offsets
    candidates = []
    p0 = base / "n2c2_sample.csv"
    if p0.exists(): candidates.append(p0)
    candidates += sorted([p for p in base.glob("*.csv")
                          if p.name.lower() != "n2c2_sample_raw.csv"
                          and "rowid_updated" not in p.name.lower()])
    if not candidates:
        print(f"No candidate pair CSVs found in {base}", file=sys.stderr); sys.exit(1)

    totalN = totalS = totalR = 0
    for pc in candidates:
        n, s, r = load_pairs_with_offsets(conn, pc, rid_index, split=args.split)
        totalN += n; totalS += s; totalR += r

    print(f"Loaded: notes+{totalN} sections+{totalS} relations+{totalR}. Raw notes loaded: {len(rid_index)}")

