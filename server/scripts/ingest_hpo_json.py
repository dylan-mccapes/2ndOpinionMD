#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, json, argparse, re
import psycopg2, psycopg2.extras

def connect():
    dsn = os.environ.get("SYNC_DATABASE_URL", "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd")
    return psycopg2.connect(dsn)

def detect_id_col(conn, schema, table, candidates=("hpo_id","term_id","id")) -> str:
    with conn.cursor() as cur:
        cur.execute("""SELECT column_name FROM information_schema.columns
                       WHERE table_schema=%s AND table_name=%s""", (schema, table))
        cols = {r[0] for r in cur.fetchall()}
    for c in candidates:
        if c in cols: return c
    raise RuntimeError(f"No known ID column found on {schema}.{table}")

def iri_to_curie(x: str) -> str | None:
    if not x: return None
    s = x.strip()
    if s.startswith("http://purl.obolibrary.org/obo/HP_") or s.startswith("https://purl.obolibrary.org/obo/HP_"):
        frag = s.rsplit("/", 1)[-1]  # HP_0000118
        return frag.replace("HP_", "HP:")
    return None

def curie_to_iri(curie: str) -> str:
    return f"http://purl.obolibrary.org/obo/{curie.replace(':','_')}"

def norm_to_curie(x: str | None) -> str | None:
    if not x: return None
    x = x.strip()
    iri = iri_to_curie(x)
    if iri: return iri
    s = x.upper().replace("HP_", "HP:")
    return s if s.startswith("HP:") else None

def terms_use_iri(conn, schema, terms, id_col) -> bool:
    with conn.cursor() as cur:
        cur.execute(f"SELECT EXISTS (SELECT 1 FROM {schema}.{terms} WHERE {id_col} ~ '^https?://' LIMIT 1)")
        return bool(cur.fetchone()[0])

def edge_rel_label(pred: str) -> str:
    if not pred: return ""
    p = pred.strip(); low = p.lower()
    if low.endswith("subclassof") or p == "rdfs:subClassOf" or p == "is_a": return "is_a"
    if low.endswith("bfo_0000050") or low.endswith("part_of"): return "part_of"
    if "#" in p: return p.rsplit("#",1)[-1]
    if "/" in p: return p.rsplit("/",1)[-1]
    return p

# --- new: normalization matching your unique index ---
_WS = re.compile(r"[ \t\r\n\f\v]+")
def norm_syn(s: str) -> str:
    return _WS.sub(" ", s).strip().lower()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--schema", default="ontology")
    ap.add_argument("--terms", default="hpo_terms")
    ap.add_argument("--edges", default="hpo_edges")
    ap.add_argument("--synonyms", default="hpo_synonyms")
    ap.add_argument("--truncate", action="store_true")
    args = ap.parse_args()

    d = json.load(open(args.json))
    g = (d.get("graphs") or [None])[0] or {}
    nodes = g.get("nodes") or []
    edges = g.get("edges") or []

    print(f"[ingest_hpo_json] file={args.json} nodes={len(nodes)} edges={len(edges)}")

    conn = connect(); conn.autocommit = False
    id_col = detect_id_col(conn, args.schema, args.terms)
    use_iri = terms_use_iri(conn, args.schema, args.terms, id_col)
    print(f"[ingest_hpo_json] terms.id_col={id_col} use_iri={use_iri}")

    try:
        with conn.cursor() as cur:
            if args.truncate:
                cur.execute(f"TRUNCATE {args.schema}.{args.edges}")
                cur.execute(f"TRUNCATE {args.schema}.{args.synonyms}")

            # -------- EDGES (HPO→HPO only) --------
            edge_rows = []
            for e in edges:
                sub_c = norm_to_curie(e.get("sub")); obj_c = norm_to_curie(e.get("obj"))
                if not (sub_c and obj_c): continue
                if not (sub_c.startswith("HP:") and obj_c.startswith("HP:")): continue
                rel = edge_rel_label(e.get("pred") or "")
                sub, obj = (curie_to_iri(sub_c), curie_to_iri(obj_c)) if use_iri else (sub_c, obj_c)
                props = json.dumps({k:v for k,v in e.items() if k not in ("sub","pred","obj")})
                edge_rows.append((sub, obj, rel, "hpo", props))

            if edge_rows:
                psycopg2.extras.execute_batch(
                    cur,
                    ("INSERT INTO {s}.{e} (child_id,parent_id,rel_type,source,props) "
                     "VALUES (%s,%s,%s,%s,%s) "
                     "ON CONFLICT (child_id,parent_id,rel_type) DO NOTHING").format(s=args.schema,e=args.edges),
                    edge_rows, page_size=2000)

            # -------- SYNONYMS (dedup BEFORE insert using normalized key) --------
            syn_rows = []
            seen = set()  # (hpo_id, norm_synonym)
            for n in nodes:
                nid_c = norm_to_curie(n.get("id"))
                if not (nid_c and nid_c.startswith("HP:")): continue
                nid = curie_to_iri(nid_c) if use_iri else nid_c
                meta = n.get("meta") or {}

                # 1) meta.synonyms
                for s in meta.get("synonyms") or []:
                    val = (s.get("val") or "").strip()
                    if not val: continue
                    key = (nid, norm_syn(val))
                    if key in seen: continue
                    seen.add(key)
                    raw = (s.get("pred") or "")
                    scope = raw.split("#")[-1].lower() if raw else None
                    lang  = s.get("lang")
                    xrefs = s.get("xrefs") or None
                    syn_rows.append((nid, val, scope, lang, xrefs, "hpo"))

                # 2) basicPropertyValues with synonym preds
                for bpv in meta.get("basicPropertyValues") or []:
                    val = (bpv.get("val") or "").strip()
                    if not val: continue
                    pred = (bpv.get("pred") or "").lower()
                    if "synonym" not in pred: continue
                    key = (nid, norm_syn(val))
                    if key in seen: continue
                    seen.add(key)
                    if   "exact"   in pred: scope = "exact"
                    elif "broad"   in pred: scope = "broad"
                    elif "narrow"  in pred: scope = "narrow"
                    elif "related" in pred: scope = "related"
                    else: scope = None
                    syn_rows.append((nid, val, scope, None, None, "hpo"))

            if syn_rows:
                psycopg2.extras.execute_batch(
                    cur,
                    ("INSERT INTO {s}.{y} (hpo_id,synonym,scope,lang,xrefs,source) "
                     "VALUES (%s,%s,%s,%s,%s,%s) "
                     "ON CONFLICT (hpo_id,synonym) DO NOTHING").format(s=args.schema,y=args.synonyms),
                    syn_rows, page_size=2000)

        print(f"[ingest_hpo_json] inserted edges={len(edge_rows)} synonyms={len(syn_rows)}")
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
