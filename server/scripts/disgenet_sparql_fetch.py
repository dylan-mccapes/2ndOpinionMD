#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, sys, re, json, csv, time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SPARQL = """\
PREFIX sio:  <http://semanticscience.org/resource/>
PREFIX ncit: <http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?gda ?geneId ?symbol ?diseaseCUI ?diseaseName ?score
WHERE {
  VALUES ?gene { %GENES% }
  ?gda sio:SIO_000628 ?gene, ?disease .
  ?gene a ncit:C16612 ;
        rdfs:label ?symbol .
  ?disease rdfs:label ?diseaseName .
  OPTIONAL {
    ?gda sio:SIO_000216 ?scoreNode .
    ?scoreNode sio:SIO_000300 ?score .
  }
  BIND(REPLACE(STR(?gene), ".*/", "") AS ?geneId)
  BIND(REPLACE(STR(?disease), ".*/", "") AS ?diseaseCUI)
}
"""

def post_sparql(endpoint: str, query: str) -> list[dict]:
    data = urlencode({"query": query}).encode("utf-8")
    req = Request(endpoint, data=data, headers={
        "Accept": "application/sparql-results+json",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "2ndOpinionMD-SPARQL/1.0",
    })
    with urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    vars_ = payload["head"]["vars"]
    out = []
    for b in payload["results"]["bindings"]:
        row = {}
        for v in vars_:
            row[v] = b.get(v, {}).get("value")
        out.append(row)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--ids-file", required=True, help="file with one NCBI Gene ID per line")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    genes = []
    for line in open(args.ids_file):
        s = line.strip()
        if not s or not s.isdigit(): continue
        genes.append(f"<http://identifiers.org/ncbigene/{s}>")
    if not genes:
        open(args.out, "w").close()
        return

    q = SPARQL.replace("%GENES%", " ".join(genes))
    rows = post_sparql(args.endpoint, q)

    # Write TSV compatible with ingest_disgenet.py expected columns (subset)
    # Header matches your curated TSV vocabulary where possible
    cols = [
        "EI","EL","assocID","diseaseName","diseaseType","diseaseUMLSCUI",
        "geneNcbiID","symbolOfGene","score","yearFinal","yearInitial"
    ]
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(cols)
        for r in rows:
            gda_iri = r.get("gda","")
            # assocID: last path segment of GDA IRI
            assoc_id = re.sub(r".*/", "", gda_iri) if gda_iri else ""
            gene_id  = r.get("geneId") or ""
            symbol   = r.get("symbol") or ""
            cui      = r.get("diseaseCUI") or ""
            dname    = r.get("diseaseName") or ""
            score    = r.get("score") or ""
            w.writerow(["","","%s"%assoc_id, dname, "disease", cui, gene_id, symbol, score, "", ""])

if __name__ == "__main__":
    main()

