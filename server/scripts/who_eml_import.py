#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WHO EML 2025 importer
- Robust to eEML header variations (e.g., medicine_name/eml_section/atc_codes/…)
- Uses python-calamine if present (fewer openpyxl quirks), falls back to openpyxl
- Writes into guidelines.who_eml_* tables
"""
import os, re, json, hashlib
import pandas as pd
import psycopg2

EDITION_EML = 24
YEAR = 2025

# ---------- DSN helpers ----------
def get_dsn():
    dsn = os.environ.get("SYNC_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("Set SYNC_DATABASE_URL or DATABASE_URL")
    return dsn.replace("+asyncpg", "")

# ---------- parsing helpers ----------
def norm_cols(cols):
    out = []
    for c in cols:
        c = "" if c is None else str(c)
        c = c.strip().lower()
        c = re.sub(r"[^a-z0-9]+", "_", c)
        out.append(c.strip("_"))
    return out

def split_multi(val):
    if not isinstance(val, str) or not val.strip():
        return []
    return [p.strip() for p in re.split(r"[;\n\|,]", val) if p.strip()]

def parse_formulations(val: str):
    if not isinstance(val, str) or not val.strip():
        return []
    items = []
    for chunk in split_multi(val):
        # try "route: form strength" pattern loosely
        route, rest = (chunk.split(":", 1) + [None])[:2] if ":" in chunk else (None, chunk)
        route = (route or "").strip() or None
        rest = (rest or chunk).strip()
        m = re.search(r"(\d+(?:\.\d+)?\s*(?:mg|g|mcg|µg|iu|units|ml|mL))", rest, re.I)
        items.append({"route": route, "dose_form": rest, "strength": m.group(1) if m else None})
    return items

def md5_key(*parts: str) -> str:
    return hashlib.md5("|".join([p or "" for p in parts]).encode("utf-8")).hexdigest()

# ---------- IO ----------
def read_eml_df(path: str) -> pd.DataFrame:
    # Prefer calamine; fallback to openpyxl
    try:
        xls = pd.ExcelFile(path, engine="calamine")
        # Pick first non-empty sheet
        for sn in xls.sheet_names:
            df = xls.parse(sn, dtype=str)
            if df.shape[0] and df.shape[1]:
                df.columns = norm_cols(df.columns)
                df = df.dropna(how="all").dropna(axis=1, how="all")
                return df
        raise RuntimeError("No usable sheet found in XLSX (calamine).")
    except Exception:
        df = pd.read_excel(path, engine="openpyxl", dtype=str)
        df.columns = norm_cols(df.columns)
        df = df.dropna(how="all").dropna(axis=1, how="all")
        return df

# ---------- DB upserts (no ON CONFLICT assumptions) ----------
def get_or_create_medicine(cur, *, inn, list_type, section_path, notes, raw):
    cur.execute(
        """SELECT med_id FROM guidelines.who_eml_medicines
           WHERE inn=%s AND list_type=%s AND edition=%s AND year=%s
           LIMIT 1""",
        (inn, list_type, EDITION_EML, YEAR)
    )
    row = cur.fetchone()
    if row:
        med_id = row[0]
        cur.execute(
            """UPDATE guidelines.who_eml_medicines
               SET section_path=COALESCE(%s, section_path),
                   notes=%s,
                   raw=%s
               WHERE med_id=%s""",
            (section_path, notes, json.dumps(raw), med_id)
        )
        return med_id
    # insert
    cur.execute(
        """INSERT INTO guidelines.who_eml_medicines
           (med_key, inn, list_type, section_path, edition, year, notes, raw)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
           RETURNING med_id""",
        (md5_key(str(EDITION_EML), inn, list_type), inn, list_type, section_path,
         EDITION_EML, YEAR, notes, json.dumps(raw))
    )
    return cur.fetchone()[0]

def ensure_child(cur, table, wheres, where_vals, insert_cols, insert_vals):
    # existence check
    cur.execute(f"SELECT 1 FROM {table} WHERE " + " AND ".join(wheres) + " LIMIT 1", where_vals)
    if cur.fetchone():
        return
    cur.execute(
        f"INSERT INTO {table} (" + ",".join(insert_cols) + ") VALUES (" +
        ",".join(["%s"] * len(insert_cols)) + ")",
        insert_vals
    )

# ---------- main import ----------
def import_eml(xlsx_path: str):
    df = read_eml_df(xlsx_path)

    # Map your sheet headers to canonical fields
    # Known variants seen in eEML exports
    col_inn     = next((c for c in df.columns if c in ("inn","medicine","name","generic_name","medicine_name")), None)
    col_section = next((c for c in df.columns if c in ("eml_section","section","section_path")), None)
    col_atc     = next((c for c in df.columns if c in ("atc","atc_code","atc_codes")), None)
    col_icd     = next((c for c in df.columns if c in ("icd11","icd_11","icd_11_codes","icd11_codes")), None)  # often absent
    col_ind     = next((c for c in df.columns if "indication" in c), None)
    col_forms   = next((c for c in df.columns if c in ("formulations","formulation","pharmaceutical_form")), None)
    col_alts    = next((c for c in df.columns if "therapeutic_alternative" in c or "alternative" in c), None)
    col_comb    = next((c for c in df.columns if c in ("combined_with","combination_with","partner_medicines")), None)
    col_foot    = next((c for c in df.columns if "footnote" in c), None)
    col_just    = next((c for c in df.columns if "justification" in c or "decision" in c), None)
    col_list    = next((c for c in df.columns if c in ("list_type","list")), None)
    col_status  = next((c for c in df.columns if c == "status"), None)  # present in your sheet
    col_aware   = next((c for c in df.columns if "aware" in c and "group" in c), None)

    if not col_inn:
        raise RuntimeError(f"Could not detect INN column; columns={list(df.columns)}")

    with psycopg2.connect(get_dsn()) as conn:
        with conn.cursor() as cur:
            for _, r in df.iterrows():
                inn = (r.get(col_inn) or "").strip() if col_inn else ""
                if not inn:
                    continue

                section     = (r.get(col_section) or "").strip() if col_section else None
                atc_list    = split_multi(str(r.get(col_atc) or "")) if col_atc else []
                icd_list    = split_multi(str(r.get(col_icd) or "")) if col_icd else []
                indication  = (r.get(col_ind) or "")
                forms       = parse_formulations(str(r.get(col_forms) or "")) if col_forms else []
                alts        = split_multi(str(r.get(col_alts) or "")) if col_alts else []
                combs       = split_multi(str(r.get(col_comb) or "")) if col_comb else []
                foots       = split_multi(str(r.get(col_foot) or "")) if col_foot else []
                just        = (r.get(col_just) or "")
                list_raw    = (r.get(col_list) or "")
                status_raw  = (r.get(col_status) or "").lower()
                aware_group = (r.get(col_aware) or "").strip() if col_aware else None

                # Decide list type
                list_type = (list_raw or "").strip().upper()
                if not list_type:
                    list_type = "EMLc" if ("child" in status_raw or "emlc" in status_raw) else "EML"

                # notes (keep status)
                notes = status_raw or None

                # raw record (preserve original columns)
                raw_record = {k: (None if (pd.isna(v) if isinstance(v, float) else False) else v) for k, v in r.items()}

                med_id = get_or_create_medicine(
                    cur, inn=inn, list_type=list_type, section_path=section, notes=notes, raw=raw_record
                )

                # Optional AWaRe flag
                if aware_group:
                    cur.execute("UPDATE guidelines.who_eml_medicines SET antibiotic_group=%s WHERE med_id=%s",
                                (aware_group, med_id))

                # Children
                for code in atc_list:
                    code = code.upper().strip()
                    if code:
                        ensure_child(cur,
                                     "guidelines.who_eml_atc",
                                     ["med_id=%s","atc_code=%s"],
                                     (med_id, code),
                                     ["med_id","atc_code"],
                                     (med_id, code))
                for code in icd_list:
                    code = code.upper().strip()
                    if code:
                        ensure_child(cur,
                                     "guidelines.who_eml_icd11",
                                     ["med_id=%s","icd11_code=%s","COALESCE(indication_text,'')=%s"],
                                     (med_id, code, indication or ""),
                                     ["med_id","icd11_code","indication_text"],
                                     (med_id, code, indication or None))
                for f in forms:
                    ensure_child(cur,
                                 "guidelines.who_eml_formulations",
                                 ["med_id=%s","COALESCE(route,'')=%s","COALESCE(dose_form,'')=%s","COALESCE(strength,'')=%s"],
                                 (med_id, f.get("route") or "", f.get("dose_form") or "", f.get("strength") or ""),
                                 ["med_id","route","dose_form","strength"],
                                 (med_id, f.get("route"), f.get("dose_form"), f.get("strength")))
                for alt in alts + combs:
                    alt = alt.strip()
                    if alt:
                        ensure_child(cur,
                                     "guidelines.who_eml_alternatives",
                                     ["med_id=%s","alt_inn=%s"],
                                     (med_id, alt),
                                     ["med_id","alt_inn"],
                                     (med_id, alt))
                for i, t in enumerate(foots, start=1):
                    ensure_child(cur,
                                 "guidelines.who_eml_footnotes",
                                 ["med_id=%s","n=%s"],
                                 (med_id, str(i)),
                                 ["med_id","n","text"],
                                 (med_id, str(i), t))
                if just and str(just).strip():
                    ensure_child(cur,
                                 "guidelines.who_eml_justifications",
                                 ["med_id=%s","COALESCE(text,'')=%s"],
                                 (med_id, str(just).strip()),
                                 ["med_id","text"],
                                 (med_id, str(just).strip()))

    print(f"[who_eml_import] Done: {xlsx_path}")

# ---------- CLI ----------
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="data/who/eml_2025.xlsx")
    args = ap.parse_args()
    import_eml(args.file)
