#!/usr/bin/env python
import sys, os, csv, time
import mygene

IN = sys.argv[1] if len(sys.argv) > 1 else "data/autoimmune_genes_ranked.tsv"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/autoimmune_gene_ids.tsv"

mg = mygene.MyGeneInfo()
symbols = []
with open(IN, newline="") as f:
    for row in csv.reader(f, delimiter="\t"):
        if not row: continue
        sym = row[0].strip()
        if sym and sym != "gene_symbol":
            symbols.append(sym)

# batch query
res = mg.querymany(symbols, scopes="symbol", fields="entrezgene", species="human", as_dataframe=False)
seen = set()
ok = 0
with open(OUT, "w", newline="") as out:
    w = csv.writer(out, delimiter="\t")
    w.writerow(["gene_symbol","entrez_id"])
    for r in res:
        sym = r.get("query")
        eg  = r.get("entrezgene")
        if sym and eg and (sym,eg) not in seen:
            w.writerow([sym, eg])
            ok += 1
            seen.add((sym,eg))
print(f"Wrote {OUT} ({ok} mapped of {len(symbols)})")

