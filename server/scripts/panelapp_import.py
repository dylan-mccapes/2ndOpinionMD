import os, sys, json, time, re, requests, psycopg2
from psycopg2.extras import execute_values
from urllib.parse import urlencode
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.exceptions import SSLError, ConnectionError, ReadTimeout

# -------- Config --------
PANELAPP_BASE = os.getenv("PANELAPP_BASE", "https://panelapp.genomicsengland.co.uk")
# Mirror to try if GEL flakes
PANELAPP_MIRROR_BASE = os.getenv("PANELAPP_MIRROR_BASE", "https://panelapp.agha.umccr.org")
PINNED_PANEL_IDS = os.getenv("PANELAPP_IDS", "")
API_SIGNEDOFF = "/api/v1/panels/signedoff/"
API_PANELS    = "/api/v1/panels/"

DATABASE_URL   = os.environ.get("SYNC_DATABASE_URL", "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd")
DEBUG          = bool(int(os.getenv("PANELAPP_DEBUG", "0")))
VERIFY_SSL     = bool(int(os.getenv("PANELAPP_VERIFY", "1")))  # set 0 to bypass verify as last resort

# Canonical targets (accept env override)
ENV_PANELS = os.getenv("PANELAPP_PANELS", "")
if ENV_PANELS.strip():
    TARGET_PANELS = [p.strip() for p in ENV_PANELS.split(",") if p.strip()]
else:
    TARGET_PANELS = [
        # Motor neurone disease (UK spelling is canonical)
        "Motor Neurone Disease",
        # Multiple sclerosis susceptibility
        "Multiple sclerosis susceptibility",
    ]

UA = {"Accept": "application/json", "User-Agent": "2ndOpinionMD PanelApp Importer/1.0"}

# Silence TLS warnings only if VERIFY_SSL=0
if not VERIFY_SSL:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def _as_text_array(v):
    """
    Convert a possibly mixed list (strings/dicts/ints) to a list[str] suitable for Postgres text[].
    - If v is None -> []
    - If v is a scalar -> [str(v)]
    - If v is list/tuple -> [str or json] for each element
    - Dict elements are json.dumps(...) to preserve info.
    """
    if v is None:
        return []
    if isinstance(v, (str, int, float, bool)):
        return [str(v)]
    if isinstance(v, (list, tuple)):
        out = []
        for x in v:
            if isinstance(x, (str, int, float, bool)):
                out.append(str(x))
            elif isinstance(x, dict):
                out.append(json.dumps(x, ensure_ascii=False))
            else:
                out.append(str(x))
        return out
    if isinstance(v, dict):
        # rare, but make it a single JSON string
        return [json.dumps(v, ensure_ascii=False)]
    return [str(v)]

# -------- HTTP session with retries + fallback --------
def _build_session():
    s = requests.Session()
    retry = Retry(
        total=6, connect=6, read=6,
        backoff_factor=0.8,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s

SESSION_PRIMARY = _build_session()
SESSION_MIRROR  = _build_session()

def _get_json_full(base, path, params=None):
    url = f"{base}{path}"
    try:
        r = SESSION_PRIMARY.get(url, params=params, headers=UA, timeout=60, verify=VERIFY_SSL)
        r.raise_for_status()
        return r.json()
    except (SSLError, ConnectionError, ReadTimeout) as e:
        if DEBUG: print(f"[DEBUG] primary failed {url}: {e}", file=sys.stderr)
        # try mirror once
        try:
            r = SESSION_MIRROR.get(f"{PANELAPP_MIRROR_BASE}{path}", params=params, headers=UA, timeout=60, verify=VERIFY_SSL)
            r.raise_for_status()
            if DEBUG: print(f"[DEBUG] mirror succeeded for {path}", file=sys.stderr)
            return r.json()
        except Exception as e2:
            if DEBUG: print(f"[DEBUG] mirror failed {path}: {e2}", file=sys.stderr)
            raise

def _paged(base, path, params=None):
    payload = _get_json_full(base, path, params=params)
    while True:
        yield payload
        nxt = payload.get("next")
        if not nxt:
            break
        # 'next' is absolute; route via same function (primary then mirror)
        try:
            r = SESSION_PRIMARY.get(nxt, headers=UA, timeout=60, verify=VERIFY_SSL)
            r.raise_for_status()
            payload = r.json()
        except (SSLError, ConnectionError, ReadTimeout):
            # rewrite next to mirror base
            if nxt.startswith(PANELAPP_BASE):
                nxt_m = nxt.replace(PANELAPP_BASE, PANELAPP_MIRROR_BASE, 1)
            else:
                nxt_m = nxt
            r = SESSION_MIRROR.get(nxt_m, headers=UA, timeout=60, verify=VERIFY_SSL)
            r.raise_for_status()
            payload = r.json()

# -------- Panel fetch helpers --------
def fetch_signedoff_index():
    panels = []
    for page in _paged(PANELAPP_BASE, API_SIGNEDOFF):
        panels.extend(page.get("results", []))
    return panels

def get_panel_latest(panel_id):
    # GET /api/v1/panels/{id}/  -> returns a single panel with "version"
    return _get_json_full(PANELAPP_BASE, f"{API_PANELS}{panel_id}/")

def pick_best_any_for_panel(panel_id):
    # try signed-off first; if none and env allows, return latest from /panels/{id}/
    so = pick_best_signedoff_for_panel(panel_id)
    if so:
        return so
    if os.getenv("PANELAPP_ALLOW_UNSIGNED", "0") not in ("1","true","TRUE","yes","YES"):
        return None
    latest = get_panel_latest(panel_id)
    # shape shim to look like signed-off payload keys
    return {
        "id": latest.get("id"),
        "hash_id": latest.get("hash_id"),
        "name": latest.get("name"),
        "version": latest.get("version"),
        "disease_group": latest.get("disease_group"),
        "disease_sub_group": latest.get("disease_sub_group"),
        "relevant_disorders": latest.get("relevant_disorders") or [],
        "types": latest.get("types") or [],
    }

def search_panels(term):
    panels = []
    q = {"search": term}
    for page in _paged(PANELAPP_BASE, API_PANELS, params=q):
        panels.extend(page.get("results", []))
    return panels

def pick_best_signedoff_for_panel(panel_id):
    res = []
    for page in _paged(PANELAPP_BASE, API_SIGNEDOFF, params={"panel_id": panel_id}):
        res.extend(page.get("results", []))
    if not res: return None
    # pick highest dotted version lexicographically (PanelApp versions compare ok as strings)
    res.sort(key=lambda x: str(x.get("version", "0")), reverse=True)
    return res[0]

# -------- Name matching (stricter) --------
_ws = re.compile(r"\s+")
def _norm(s): return _ws.sub(" ", (s or "").lower()).strip()

def _tokenize(s):
    return set(re.findall(r"[a-z0-9]+", (s or "").lower()))

def _score_name(qname, pname):
    # prefer exact normalized match
    qn, pn = _norm(qname), _norm(pname)
    if qn == pn: return 1.0
    qt, pt = _tokenize(qname), _tokenize(pname)
    if not qt or not pt: return 0.0
    inter = len(qt & pt)
    jacc = inter / len(qt | pt)
    # bonus if critical tokens present (neurone|neuron, sclerosis, disease)
    bonus = 0.0
    if {"neurone","neuron"} & pt: bonus += 0.1
    if "sclerosis" in pt: bonus += 0.1
    if "disease" in pt: bonus += 0.05
    return jacc + bonus

def resolve_panels(target_terms):
    signed = fetch_signedoff_index()
    if DEBUG: print(f"[DEBUG] signedoff panels: {len(signed)}", file=sys.stderr)

    resolved = {}
    for term in target_terms:
        # 1) Rank signed-off names by score
        ranked = []
        for p in signed:
            nm = p.get("name","")
            sc = _score_name(term, nm)
            if sc >= 0.35:   # threshold to avoid unrelated panels (e.g., Arthrogryposis)
                ranked.append((sc, p))
        ranked.sort(key=lambda x: (x[0], str(x[1].get("version","0"))), reverse=True)

        # 2) If still empty, try search endpoint and lift to signed-off
        if not ranked:
            hits = search_panels(term)
            if DEBUG: print(f"[DEBUG] search '{term}' -> {len(hits)} candidates", file=sys.stderr)
            tmp = []
            for h in hits:
                pid = h.get("id")
                so = pick_best_any_for_panel(pid)
                if so:
                    sc = _score_name(term, so.get("name",""))
                    if sc >= 0.35:
                        tmp.append((sc, so))
            tmp.sort(key=lambda x: (x[0], str(x[1].get("version","0"))), reverse=True)
            ranked = tmp

        if not ranked:
            if DEBUG: print(f"[DEBUG] no match for '{term}'", file=sys.stderr)
            continue

        chosen = ranked[0][1]
        pid = chosen.get("id")
        resolved[chosen.get("name") or term] = {
            "panel_id": pid,
            "panel_hash_id": chosen.get("hash_id"),
            "name": chosen.get("name"),
            "version": str(chosen.get("version")),
            "disease_group": chosen.get("disease_group"),
            "disease_sub_group": chosen.get("disease_sub_group"),
            "relevant_disorders": chosen.get("relevant_disorders") or [],
            "panel_types": chosen.get("types") or [],
            "raw": chosen,
        }
        if DEBUG:
            sc = ranked[0][0]
            print(f"[DEBUG] resolved '{term}' -> id={pid}, name='{chosen.get('name')}', v={chosen.get('version')} (score={sc:.2f})", file=sys.stderr)
    return resolved

def fetch_panel_genes(panel_id, version):
    return _get_json_full(PANELAPP_BASE, f"{API_PANELS}{panel_id}/genes/", params={"version": str(version)})

# -------- DB upsert + entrypoint ----------------------------------------------

def upsert_rows(conn, rows):
    sql = """
    INSERT INTO molecular.gene_panels
    (panel_id, panel_hash_id, panel_name, panel_version, signed_off, source_instance,
     disease_group, disease_sub_group, relevant_disorders, panel_types,
     gene_symbol, hgnc_id, ensembl_gene_id_grch37, ensembl_gene_id_grch38,
     confidence_level, mode_of_inheritance, evidence, phenotypes, review_status,
     raw_panel_json, raw_gene_json)
    VALUES %s
    ON CONFLICT (panel_id, panel_version, gene_symbol)
    DO UPDATE SET
      panel_hash_id = EXCLUDED.panel_hash_id,
      panel_name = EXCLUDED.panel_name,
      signed_off = EXCLUDED.signed_off,
      disease_group = EXCLUDED.disease_group,
      disease_sub_group = EXCLUDED.disease_sub_group,
      relevant_disorders = EXCLUDED.relevant_disorders,
      panel_types = EXCLUDED.panel_types,
      hgnc_id = EXCLUDED.hgnc_id,
      ensembl_gene_id_grch37 = EXCLUDED.ensembl_gene_id_grch37,
      ensembl_gene_id_grch38 = EXCLUDED.ensembl_gene_id_grch38,
      confidence_level = EXCLUDED.confidence_level,
      mode_of_inheritance = EXCLUDED.mode_of_inheritance,
      evidence = EXCLUDED.evidence,
      phenotypes = EXCLUDED.phenotypes,
      review_status = EXCLUDED.review_status,
      raw_panel_json = EXCLUDED.raw_panel_json,
      raw_gene_json = EXCLUDED.raw_gene_json,
      imported_at = now();
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=500)
    conn.commit()

def main():
    conn = psycopg2.connect(DATABASE_URL)

    # Resolve target panels either by pinned IDs or by names
    wanted = {}
    if PINNED_PANEL_IDS.strip():
        if DEBUG: print(f"[DEBUG] using pinned IDs: {PINNED_PANEL_IDS}", file=sys.stderr)
        for raw in PINNED_PANEL_IDS.split(","):
            pid = raw.strip()
            if not pid:
                continue
            so = pick_best_any_for_panel(pid)
            if not so:
                print(f"[WARN] no signed-off version for panel id={pid}", file=sys.stderr)
                continue
            wanted[so.get("name") or pid] = {
                "panel_id": so.get("id"),
                "panel_hash_id": so.get("hash_id"),
                "name": so.get("name"),
                "version": str(so.get("version")),
                "disease_group": so.get("disease_group"),
                "disease_sub_group": so.get("disease_sub_group"),
                "relevant_disorders": so.get("relevant_disorders") or [],
                "panel_types": so.get("types") or [],
                "raw": so,
            }
            if DEBUG:
                print(f"[DEBUG] pinned id={pid} -> {so.get('name')} v{so.get('version')}", file=sys.stderr)
    else:
        wanted = resolve_panels(TARGET_PANELS)

    if not wanted:
        print("No matching panels found; set PANELAPP_PANELS or PANELAPP_IDS.", file=sys.stderr)
        sys.exit(2)

    all_rows = []
    for pname, meta in wanted.items():
        panel_id = meta["panel_id"]
        version = meta["version"]
        payload = fetch_panel_genes(panel_id, version)
        results = payload.get("results") or payload.get("genes") or []
        if DEBUG:
            print(f"[DEBUG] genes for id={panel_id} v={version} -> {len(results)}", file=sys.stderr)

        for rec in results:
            gd = rec.get("gene_data") or {}
            gene_symbol  = gd.get("gene_symbol") or rec.get("entity_name")
            # Cast scalar IDs to str for text columns
            hgnc_id      = gd.get("hgnc_id")
            if hgnc_id is not None: hgnc_id = str(hgnc_id)
            eg37         = gd.get("ensembl_gene_id_grch37")
            if eg37 is not None: eg37 = str(eg37)
            eg38         = gd.get("ensembl_gene_id_grch38")
            if eg38 is not None: eg38 = str(eg38)

            confidence   = rec.get("confidence_level")
            moi          = rec.get("mode_of_inheritance")

            # Normalize arrays to text[]
            phenos       = _as_text_array(rec.get("phenotypes"))
            evidence     = _as_text_array(rec.get("evidence"))
            rel_dis      = _as_text_array(meta["relevant_disorders"])
            ptypes       = _as_text_array(meta["panel_types"])

            all_rows.append((
                panel_id, meta["panel_hash_id"], meta["name"], version, True, "GEL",
                meta["disease_group"], meta["disease_sub_group"], rel_dis, ptypes,
                gene_symbol, hgnc_id, eg37, eg38,
                confidence, moi, evidence, phenos, rec.get("review_status"),
                json.dumps(meta["raw"]), json.dumps(rec),
            ))

    if all_rows:
        upsert_rows(conn, all_rows)
        print(f"Upserted {len(all_rows)} rows across {len(wanted)} panel(s).")
    else:
        print(f"Resolved {len(wanted)} panel(s) but 0 gene rows returned. "
              f"Try PANELAPP_VERIFY=0 or pin by IDs via PANELAPP_IDS.", file=sys.stderr)
    conn.close()

if __name__ == "__main__":
    main()

