#!/usr/bin/env python3
"""
Pull DisGeNET GDA summary in small, trial-friendly batches and append to a TSV,
deduplicating by assocID. Resumable via a ledger of completed IDs.

Usage (env):
  DISGENET_TOKEN=... python server/scripts/disgenet_pull_batches.py \
    --ids-file data/autoimmune_gene_ids.txt \
    --out-tsv data/disgenet_curated.tsv \
    --batch-size 10 \
    --filter-key source --filter-value CURATED \
    --endpoint gda/summary \
    --auth-mode bare \
    --sleep 0

Auth modes:
  bare   -> Authorization: <TOKEN>
  bearer -> Authorization: Bearer <TOKEN>
  x-api-key -> X-API-KEY: <TOKEN>
"""
import argparse, os, sys, time, textwrap
from pathlib import Path
import requests

def chunked(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

def read_ids(path):
    ids = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            # keep only digits (NCBI Gene IDs are numeric)
            if s.isdigit():
                ids.append(s)
            else:
                # tolerate accidental symbols etc. but skip
                pass
    return ids

def load_associds_from_master(master_path):
    assoc = set()
    p = Path(master_path)
    if not p.exists() or p.stat().st_size == 0:
        return assoc
    with p.open('r', encoding='utf-8', errors='ignore') as f:
        first = True
        for line in f:
            if first:
                first = False
                continue
            parts = line.rstrip('\n').split('\t')
            if len(parts) >= 3:
                a = parts[2].strip('"')
                if a:
                    assoc.add(a)
    return assoc

def append_unique(master_path, tmp_path, assoc_seen):
    wrote = 0
    mp = Path(master_path)
    with open(tmp_path, 'r', encoding='utf-8', errors='ignore') as src, \
         open(master_path, 'a', encoding='utf-8') as out:
        first = True
        # ensure header present once
        if not mp.exists() or mp.stat().st_size == 0:
            header = src.readline()
            if header:
                out.write(header)
        else:
            # skip header
            _ = src.readline()
        # stream rows and dedupe by assocID (3rd column)
        for line in src:
            parts = line.rstrip('\n').split('\t')
            if len(parts) < 3:
                continue
            assoc_id = parts[2].strip('"')
            if assoc_id and assoc_id not in assoc_seen:
                out.write(line)
                assoc_seen.add(assoc_id)
                wrote += 1
    try:
        os.remove(tmp_path)
    except FileNotFoundError:
        pass
    return wrote

def main():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="DisGeNET batch puller (trial-safe) -> TSV (dedup by assocID)",
        epilog=textwrap.dedent(__doc__)
    )
    ap.add_argument("--ids-file", required=True, help="File with one NCBI Gene ID per line")
    ap.add_argument("--out-tsv", default="data/disgenet_curated.tsv")
    ap.add_argument("--done-ledger", help="Where to log fetched IDs (default: alongside out-tsv as .done.ids)")
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--sleep", type=float, default=0.0, help="Seconds to sleep between successful batches")
    ap.add_argument("--base-url", default=os.environ.get("DISGENET_API_BASE", "https://api.disgenet.com/api/v1"))
    ap.add_argument("--endpoint", default=os.environ.get("DISGENET_ENDPOINT", "gda/summary"))
    ap.add_argument("--filter-key", default=os.environ.get("DISGENET_FILTER_KEY", "source"))
    ap.add_argument("--filter-value", default=os.environ.get("DISGENET_FILTER_VALUE", "CURATED"))
    ap.add_argument("--accept", default=os.environ.get("DISGENET_ACCEPT", "application/csv"))
    ap.add_argument("--auth-mode", choices=["bare","bearer","x-api-key"], default=os.environ.get("DISGENET_AUTH_MODE","bare"))
    ap.add_argument("--resume", action="store_true", help="Skip IDs already present in ledger (default if ledger exists)")
    ap.add_argument("--max-retries", type=int, default=5, help="Retries per batch on non-OK/429")
    args = ap.parse_args()

    token = os.environ.get("DISGENET_TOKEN")
    if not token:
        print("ERROR: DISGENET_TOKEN env not set", file=sys.stderr)
        sys.exit(2)

    ids = read_ids(args.ids_file)
    if not ids:
        print(f"ERROR: No numeric IDs in {args.ids_file}", file=sys.stderr)
        sys.exit(2)

    out_tsv = Path(args.out_tsv)
    out_tsv.parent.mkdir(parents=True, exist_ok=True)
    done_path = Path(args.done_ledger) if args.done_ledger else out_tsv.with_suffix(".done.ids")

    # Load ledger (resume)
    done = set()
    if done_path.exists():
        with done_path.open('r', encoding='utf-8') as f:
            for line in f:
                s = line.strip()
                if s.isdigit():
                    done.add(s)

    # Pending while preserving order
    pending = [i for i in ids if i not in done]
    if not pending:
        print("Nothing to do: all IDs in ledger.")
        sys.exit(0)

    # Prepare HTTP
    headers = {"accept": args.accept}
    if args.auth_mode == "bare":
        headers["Authorization"] = token
    elif args.auth_mode == "bearer":
        headers["Authorization"] = f"Bearer {token}"
    else:
        headers["X-API-KEY"] = token

    base = args.base_url.rstrip("/")
    endpoint = args.endpoint.lstrip("/")
    url = f"{base}/{endpoint}"

    # Preload assocID set to avoid rewriting TSV each time
    assoc_seen = load_associds_from_master(out_tsv)

    total_appended = 0
    session = requests.Session()

    try:
        for batch in chunked(pending, args.batch_size):
            genes = ",".join(batch)
            params = {
                "gene_ncbi_id": genes,
                "page_number": "0",
            }
            if args.filter_key and args.filter_value:
                params[args.filter_key] = args.filter_value

            attempt = 0
            while True:
                attempt += 1
                try:
                    r = session.get(url, params=params, headers=headers, timeout=60)
                except requests.RequestException as e:
                    print(f"!! Network error for {genes}: {e}", file=sys.stderr)
                    if attempt < args.max_retries:
                        time.sleep(5 * attempt)
                        continue
                    else:
                        print("!! Giving up batch", file=sys.stderr)
                        break

                if r.status_code == 429:
                    retry_after = r.headers.get("x-rate-limit-retry-after-seconds")
                    wait_s = int(retry_after) if (retry_after and retry_after.isdigit()) else 60
                    print(f"!! 429 rate limit for {genes}. Sleeping {wait_s}s...", file=sys.stderr)
                    time.sleep(wait_s)
                    if attempt < args.max_retries:
                        continue
                    else:
                        print("!! Giving up batch after retries", file=sys.stderr)
                        break

                if not r.ok:
                    # Show small body snippet for context
                    body = r.text[:200].replace("\n"," ")
                    print(f"!! HTTP {r.status_code} for {genes}: {body}", file=sys.stderr)
                    if attempt < args.max_retries:
                        time.sleep(3 * attempt)
                        continue
                    else:
                        print("!! Giving up batch", file=sys.stderr)
                        break

                # OK
                tmp = Path(f"{out_tsv}.tmp.{os.getpid()}")
                tmp.write_bytes(r.content)

                appended = append_unique(str(out_tsv), str(tmp), assoc_seen)
                total_appended += appended
                # mark IDs as done only on success
                with done_path.open('a', encoding='utf-8') as ld:
                    for g in batch:
                        ld.write(g + "\n")
                print(f">>> {genes} -> +{appended} rows (total {total_appended})")
                if args.sleep > 0:
                    time.sleep(args.sleep)
                break

        print(f"Done. Wrote {total_appended} new rows to {out_tsv}")
    finally:
        session.close()

if __name__ == "__main__":
    main()

