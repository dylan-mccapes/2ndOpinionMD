#!/usr/bin/env python3
import os, csv, argparse, psycopg2
from psycopg2.extras import execute_values

FIELDS = [
    "loinc_num","component","property","time_aspct","system","scale_typ","method_typ",
    "class","classtype","long_common_name","shortname","external_copyright_notice",
    "status","version_first_released","version_last_changed","src_version"
]

def batched(iterable, n=5000):
    batch = []
    for row in iterable:
        batch.append(row)
        if len(batch) >= n:
            yield batch
            batch = []
    if batch:
        yield batch

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--dsn", required=True)
    args = ap.parse_args()

    core = os.path.join(args.dir, "LoincTableCore.csv")
    if not os.path.exists(core):
        raise SystemExit(f"Missing {core}")

    conn = psycopg2.connect(args.dsn)
    conn.autocommit = False
    cur = conn.cursor()

    with open(core, newline='', encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        def row_to_tuple(r):
            def g(k): return (r.get(k) or "").strip()
            def to_int(x):
                try: return int(x)
                except Exception: return None
            return (
                g("LOINC_NUM"),
                g("COMPONENT"), g("PROPERTY"), g("TIME_ASPCT"), g("SYSTEM"),
                g("SCALE_TYP"), g("METHOD_TYP"), g("CLASS"),
                to_int(g("CLASSTYPE")),
                g("LONG_COMMON_NAME"), g("SHORTNAME"),
                g("EXTERNAL_COPYRIGHT_NOTICE"),
                g("STATUS"), g("VersionFirstReleased"),
                g("VersionLastChanged"), g("SOURCE_VERSION")
            )

        tmpl = "(" + ",".join(["%s"] * len(FIELDS)) + ")"
        for chunk in batched((row_to_tuple(r) for r in rdr), n=4000):
            execute_values(cur, f"""
                INSERT INTO ontology.loinc_terms ({",".join(FIELDS)})
                VALUES %s
                ON CONFLICT (loinc_num) DO UPDATE SET
                  component=EXCLUDED.component,
                  property=EXCLUDED.property,
                  time_aspct=EXCLUDED.time_aspct,
                  system=EXCLUDED.system,
                  scale_typ=EXCLUDED.scale_typ,
                  method_typ=EXCLUDED.method_typ,
                  class=EXCLUDED.class,
                  classtype=EXCLUDED.classtype,
                  long_common_name=EXCLUDED.long_common_name,
                  shortname=EXCLUDED.shortname,
                  external_copyright_notice=EXCLUDED.external_copyright_notice,
                  status=EXCLUDED.status,
                  version_first_released=EXCLUDED.version_first_released,
                  version_last_changed=EXCLUDED.version_last_changed,
                  src_version=EXCLUDED.src_version
            """, chunk, template=tmpl)
            conn.commit()

    cur.close(); conn.close()
    print("LOINC load: done.")

if __name__ == "__main__":
    main()
