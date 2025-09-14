import json, random, argparse, pathlib
from collections import Counter

rng = random.Random(42)

LABELS_4 = ["Direct","Indirect","Neither","Not Relevant"]

def load_jsonl(p):
    import json, sys
    bad = 0
    with open(p, "r") as f:
        for ln,no in enumerate(f,1):
            s = ln.strip()
            if not s: continue
            try:
                yield json.loads(s)
            except Exception:
                bad += 1
    if bad:
        print(f"[prepare_ap_data] Skipped {bad} malformed lines in {p}", file=sys.stderr)

def write_jsonl(path, rows):
    with open(path, "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False)+"\n")

def split_gold(gold_path, out_dir, train=0.7, dev=0.15, test=0.15):
    rows = list(load_jsonl(gold_path))
    # stratified-ish by label
    buckets = {k: [] for k in LABELS_4}
    for r in rows:
        buckets[r["label"]].append(r)
    tr, dv, te = [], [], []
    for k, bucket in buckets.items():
        rng.shuffle(bucket)
        n = len(bucket)
        ntr, ndv = int(n*train), int(n*dev)
        tr += bucket[:ntr]
        dv += bucket[ntr:ntr+ndv]
        te += bucket[ntr+ndv:]
    rng.shuffle(tr); rng.shuffle(dv); rng.shuffle(te)
    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
    write_jsonl(f"{out_dir}/gold_train.jsonl", tr)
    write_jsonl(f"{out_dir}/gold_dev.jsonl", dv)
    write_jsonl(f"{out_dir}/gold_test.jsonl", te)
    print("Gold counts:", {k: len(buckets[k]) for k in LABELS_4})

def balance_silver(silver_path, out_path, neg_ratio=3):
    # Keep all positives (label=='related'), subsample negatives (label=='not') to ratio
    pos, neg = [], []
    for r in load_jsonl(silver_path):
        (pos if r["label"]=="related" else neg).append(r)
    rng.shuffle(pos); rng.shuffle(neg)
    keep_neg = neg[:min(len(neg), neg_ratio*len(pos))]
    out = pos + keep_neg
    rng.shuffle(out)
    write_jsonl(out_path, out)
    print("Silver kept:", Counter([r["label"] for r in out]))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default="data/gold_pairs.jsonl")
    ap.add_argument("--silver", default="data/silver_pairs.jsonl")
    ap.add_argument("--outdir", default="data")
    ap.add_argument("--neg_ratio", type=int, default=3)
    args = ap.parse_args()
    split_gold(args.gold, args.outdir)
    balance_silver(args.silver, f"{args.outdir}/silver_balanced.jsonl", args.neg_ratio)
