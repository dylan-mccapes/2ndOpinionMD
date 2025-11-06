#!/usr/bin/env python3
import os, argparse, psycopg2

def normalize_ndc(s: str) -> str | None:
    if not s: return None
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) == 11: return digits
    if len(digits) == 10: return "0" + digits  # simple pad; segmentation-specific zero-pad is optional here
    return None

def read_rrf(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line: continue
            # RRF is pipe-delimited and ends with a trailing '|'
            parts = line.rstrip("\n").split("|")
            yield parts

def load_rxnconso(cur, path):
    # RXNCONSO: [0 RXCUI,1 LAT,2 TS,3 LUI,4 STT,5 SUI,6 ISPREF,7 RXAUI,8 SAUI,9 SCUI,10 SDUI,11 SAB,12 TTY,13 CODE,14 STR,15 SRL,16 SUPPRESS,17 CVF]
    rows = []
    for p in read_rrf(path):
        if len(p) < 15: continue
        rxcui = p[0]
        sab   = p[11]
        tty   = p[12]
        ispref= p[6]
        s     = p[14]
        if not rxcui or not sab or not tty or not s: continue
        rows.append((int(rxcui), sab, tty, s, ispref))
        if len(rows) >= 10000:
            cur.executemany("""
                INSERT INTO ontology.rxnorm_conso (rxcui, sab, tty, str, ispref)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT DO NOTHING
            """, rows)
            rows.clear()
    if rows:
        cur.executemany("""
            INSERT INTO ontology.rxnorm_conso (rxcui, sab, tty, str, ispref)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT DO NOTHING
        """, rows)

def load_rxnsat_ndc(cur, path):
    # RXNSAT: [0 RXCUI,1 LUI,2 SUI,3 RXAUI,4 STYPE,5 CODE,6 ATUI,7 SATUI,8 ATN,9 SAB,10 ATV,11 SUPPRESS,12 CVF]
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS rxnorm_ndc_uidx ON ontology.rxnorm_ndc (rxcui, ndc_norm)")
    rows = []
    for p in read_rrf(path):
        if len(p) < 11: continue
        rxcui = p[0]; atn = p[8]; sab = p[9]; atv = p[10]
        if atn not in ("NDC","NDC11"): continue
        ndc_norm = normalize_ndc(atv)
        if not (rxcui and ndc_norm): continue
        rows.append((int(rxcui), ndc_norm, atv, atn, sab))
        if len(rows) >= 10000:
            cur.executemany("""
                INSERT INTO ontology.rxnorm_ndc (rxcui, ndc_norm, ndc, atn, sab)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (rxcui, ndc_norm) DO UPDATE SET
                  ndc = EXCLUDED.ndc,
                  atn = EXCLUDED.atn,
                  sab = EXCLUDED.sab
            """, rows)
            rows.clear()
    if rows:
        cur.executemany("""
            INSERT INTO ontology.rxnorm_ndc (rxcui, ndc_norm, ndc, atn, sab)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (rxcui, ndc_norm) DO UPDATE SET
              ndc = EXCLUDED.ndc,
              atn = EXCLUDED.atn,
              sab = EXCLUDED.sab
        """, rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--dsn", required=True)
    args = ap.parse_args()

    conso = os.path.join(args.dir, "RXNCONSO.RRF")
    sat   = os.path.join(args.dir, "RXNSAT.RRF")  # optional; needed for NDCs

    if not os.path.exists(conso):
        raise SystemExit(f"Missing {conso}")

    conn = psycopg2.connect(args.dsn); conn.autocommit = False
    cur = conn.cursor()

    load_rxnconso(cur, conso)
    if os.path.exists(sat):
        load_rxnsat_ndc(cur, sat)

    conn.commit()
    cur.close(); conn.close()
    print("RxNorm load: done.")

if __name__ == "__main__":
    main()
