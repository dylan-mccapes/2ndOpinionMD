#!/usr/bin/env python
import os, json, argparse
import psycopg2, psycopg2.extras

DSN = os.getenv("SYNC_DATABASE_URL", "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd")

def q(conn, sql, params=None):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with psycopg2.connect(DSN) as conn:
        # base ICD-10-CM counts (tolerate empty base table)
        icd10cm_codes   = q(conn, "SELECT COALESCE((SELECT COUNT(*) FROM ontology.icd10cm),0) AS c")[0]["c"]
        icd10cm_targets = q(conn, "SELECT COALESCE((SELECT COUNT(*) FROM public.icd10cm_targets),0) AS c")[0]["c"]

        rag_rows    = q(conn, "SELECT COUNT(*) c FROM public.rag_corpus WHERE source='icd10cm'")[0]["c"]
        rag_missing = q(conn, "SELECT COUNT(*) c FROM public.rag_corpus WHERE source='icd10cm' AND embedding IS NULL")[0]["c"]

        # SNOMED -> ICD map coverage (your “extended map” numbers live here)
        rows_all         = q(conn, "SELECT COUNT(*) c FROM ontology.snomed_map_icd10cm")[0]["c"]
        rows_with_target = q(conn, "SELECT COUNT(*) c FROM ontology.snomed_map_icd10cm WHERE NULLIF(trim(map_target),'') IS NOT NULL")[0]["c"]
        distinct_codes   = q(conn, "SELECT COUNT(DISTINCT NULLIF(trim(map_target),'')) c FROM ontology.snomed_map_icd10cm")[0]["c"]
        valid_plain      = q(conn, """
            SELECT COUNT(*) c
            FROM ontology.snomed_map_icd10cm
            WHERE position('X' IN map_target)=0
              AND position('?' IN map_target)=0
              AND trim(map_target) <> ''
        """)[0]["c"]
        valid_with_ph    = q(conn, """
            SELECT COUNT(*) c
            FROM ontology.snomed_map_icd10cm
            WHERE (position('X' IN map_target)>0 OR position('?' IN map_target)>0)
              AND trim(map_target) <> ''
        """)[0]["c"]
        truly_invalid    = q(conn, "SELECT COUNT(*) c FROM ontology.snomed_map_icd10cm WHERE trim(map_target) = ''")[0]["c"]

    out = {
        "icd10cm_codes": icd10cm_codes,
        "icd10cm_targets": icd10cm_targets,
        "rag_rows": rag_rows,
        "rag_missing": rag_missing,
        "rag_embedded": rag_rows - rag_missing,
        "map_rows_all": rows_all,
        "map_rows_with_target": rows_with_target,
        "map_distinct_icd10cm_codes": distinct_codes,
        "map_valid_plain": valid_plain,
        "map_valid_with_placeholders": valid_with_ph,
        "map_truly_invalid": truly_invalid,
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)

    # print single-line JSON for logs
    print(json.dumps(out, separators=(", ", " : ")))

if __name__ == "__main__":
    main()
