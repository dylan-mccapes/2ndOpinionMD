#!/usr/bin/env python3
import os, sys, time, csv, requests, itertools, math, signal
from typing import List

# ---- Config via env (with sensible defaults) ----
BASE      = os.environ.get("DISGENET_API_BASE", "https://api.disgenet.com/api/v1")
ENDPOINT  = os.environ.get("DISGENET_ENDPOINT", "gda/summary")
TOKEN     = os.environ.get("DISGENET_TOKEN", "")
AUTH_MODE = os.environ.get("DISGENET_AUTH_MODE", "bare")   # bare|bearer|x-api-key
FLTK      = os.environ.get("DISGENET_FILTER_KEY", "source")
FLTV      = os.environ.get("DISGENET_FILTER_VALUE", "CURATED")
OUT_TSV   = os.environ.get("DISGENET_TSV", "data/disgenet_curated.tsv")
GENES     = os.environ.get("GENES", "")
GENES_FILE= os.environ.get("GENES_FILE", "")

BATCH_SIZE    = int(os.environ.get("BATCH_SIZE", "10"))       # 10 is trial max
THROTTLE_SECS = int(os.environ.get("THROTTLE_SECS", "0"))     # 0=disabled; try 70 if rate limited
RETRY_MAX     = int(os.environ.get("RETRY_MAX", "5"))         # 0=infinite retry
RETRY_BASE    = float(os.environ.get("RETRY_BASE", "10"))     # base backoff seconds
TIMEOUT       = float(os.environ.get("HTTP_TIMEOUT", "60"))

DONE_IDS_FILE = os.environ.get("DONE_IDS_FILE", "data/disgenet_done.ids")
os.makedirs(os.path.dirname(OUT_TSV), exist_ok=True)
os.makedirs(os.path.dirname(DONE_IDS_FILE), exist_ok=True)

def auth_header():
    if AUTH_MODE == "bearer":
        return {"Authorization": f"Bearer {TOKEN}"}
    elif AUTH_MODE == "x-api-key":
        return {"x-api-key": TOKEN}
    else:
        return {"Authorization": TOKEN}

def load_ids() -> List[str]:
    ids = []
    if GENES_FILE:
        with open(GENES_FILE) as fh:
            ids = [ln.strip() for ln in fh if ln.strip()]
    elif GENES:
        ids = [x.strip() for x in GENES.split(",") if x.strip()]
    else:
        print("ERROR: provide GENES or GENES_FILE", file=sys.stderr); sys.exit(2)
    # resume: subtract already-seen from master TSV and from done file
    seen = set()
    if os.path.exists(OUT_TSV):
        with open(OUT_TSV, newline="") as fh:
            rd = csv.reader(fh, delimiter="\t")
            hdr = next(rd, None)
            if hdr:
                try:
                    gene_idx = hdr.index("geneNcbiID".strip('"'))
                except ValueError:
                    # handle quoted headers like "geneNcbiID"
                    try:
                        gene_idx = hdr.index('"geneNcbiID"')
                    except ValueError:
                        gene_idx = None
                if gene_idx is not None:
                    for row in rd:
                        if len(row) > gene_idx and row[gene_idx].isdigit():
                            seen.add(row[gene_idx])
    if os.path.exists(DONE_IDS_FILE):
        with open(DONE_IDS_FILE) as fh:
            for ln in fh:
                s = ln.strip()
                if s:
                    seen.add(s)
    todo = [g for g in ids if g not in seen]
    return todo

def dedupe_associd_inplace(path: str):
    """Keep header; dedupe by assocID (col 3, 1-based in CSV sample)."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return
    out = path + ".dedup"
    seen = set()
    with open(path, newline="") as fh, open(out, "w", newline="") as fo:
        rd = csv.reader(fh, delimiter="\t")
        wr = csv.writer(fo, delimiter="\t", lineterminator="\n")
        hdr = next(rd, None)
        if hdr:
            wr.writerow(hdr)
            # resolve index for assocID (handle quoted)
            idx = None
            for cand in ("assocID", '"assocID"'):
                try:
                    idx = hdr.index(cand)
                    break
                except ValueError:
                    pass
            if idx is None:
                # fallback: assume 3rd col
                idx = 2
            for row in rd:
                if len(row) > idx:
                    key = row[idx]
                    if key not in seen:
                        seen.add(key)
                        wr.writerow(row)
    os.replace(out, path)

def fetch_batch(genes_csv: str) -> str:
    url = f"{BASE.rstrip('/')}/{ENDPOINT.lstrip('/')}"
    params = {"page_number": "0", FLTK: FLTV, "gene_ncbi_id": genes_csv}
    headers = {"accept": "application/csv", **auth_header()}
    r = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
    if r.status_code == 429:
        raise requests.HTTPError("429", response=r)
    r.raise_for_status()
    return r.text

def append_csv_text(text: str):
    # append to TSV while preserving header only once
    if not os.path.exists(OUT_TSV) or os.path.getsize(OUT_TSV) == 0:
        with open(OUT_TSV, "w") as fo:
            fo.write(text)
    else:
        # skip header
        nl = text.splitlines(True)
        body = "".join(nl[1:]) if len(nl) > 1 else ""
        with open(OUT_TSV, "a") as fo:
            fo.write(body)

def main():
    if not TOKEN:
        print("ERROR: DISGENET_TOKEN not set", file=sys.stderr); sys.exit(2)

    all_ids = load_ids()
    if not all_ids:
        print("Nothing to do (all IDs already present)."); return

    print(f"Total IDs to fetch: {len(all_ids)}")
    # graceful Ctrl-C
    stop = False
    def _sigint(_s, _f):  # noqa
        nonlocal stop; stop = True
        print("\n!! Received Ctrl-C, will stop after current batch.")
    signal.signal(signal.SIGINT, _sigint)

    for i in range(0, len(all_ids), BATCH_SIZE):
        batch = all_ids[i:i+BATCH_SIZE]
        genes_csv = ",".join(batch)
        attempt = 0
        while True:
            if stop: break
            try:
                print(f">>> Fetch {i//BATCH_SIZE+1}/{math.ceil(len(all_ids)/BATCH_SIZE)}: {genes_csv}")
                text = fetch_batch(genes_csv)
                append_csv_text(text)
                dedupe_associd_inplace(OUT_TSV)
                with open(DONE_IDS_FILE, "a") as fo:
                    for g in batch: fo.write(g + "\n")
                print(f"Appended ~{len(text)} bytes")
                break  # success
            except requests.HTTPError as e:
                code = e.response.status_code if e.response is not None else None
                if code == 429:
                    attempt += 1
                    if RETRY_MAX > 0 and attempt > RETRY_MAX:
                        print("!! 429 persists; reaching RETRY_MAX. Will NOT mark this batch as done.", file=sys.stderr)
                        # do NOT write to done; leave batch in todo for next run
                        # throttle a bit before moving on (or bail if you prefer)
                        time.sleep(THROTTLE_SECS or RETRY_BASE)
                        break
                    # backoff
                    sleep_for = THROTTLE_SECS or (RETRY_BASE * (2 ** (attempt - 1)))
                    print(f"429 rate-limited; sleeping {int(sleep_for)}s (attempt {attempt}{'' if RETRY_MAX==0 else f'/{RETRY_MAX}'})")
                    time.sleep(sleep_for)
                    continue
                else:
                    print(f"HTTP {code} fetching {genes_csv}; will skip this batch for now.", file=sys.stderr)
                    break
            except Exception as ex:
                attempt += 1
                if RETRY_MAX > 0 and attempt > RETRY_MAX:
                    print(f"!! Error {ex}; giving up on this batch for now.", file=sys.stderr)
                    break
                sleep_for = THROTTLE_SECS or (RETRY_BASE * (2 ** (attempt - 1)))
                print(f"Error {ex}; sleeping {int(sleep_for)}s then retrying...")
                time.sleep(sleep_for)
        if stop: break
        if THROTTLE_SECS and not stop:
            time.sleep(THROTTLE_SECS)

if __name__ == "__main__":
    main()

