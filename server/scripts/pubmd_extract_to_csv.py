#!/usr/bin/env python3
import sys, re, csv, gzip, argparse
from lxml import etree

def norm(s: str) -> str:
    if not s: return ""
    return re.sub(r"\s+", " ", s).strip()

def extract_article(pm):
    # PMID
    pmid_el = pm.find(".//PMID")
    pmid = pmid_el.text.strip() if pmid_el is not None else None
    if not pmid: return None

    # Title
    title = norm("".join(pm.xpath(".//ArticleTitle//text()")))

    # Abstract (all sections)
    abstract = norm(" ".join(pm.xpath(".//Abstract/AbstractText//text()")))

    # Journal
    journal = norm("".join(pm.xpath(".//Journal/Title//text()")))

    # Year (best-effort)
    year = None
    y = "".join(pm.xpath(".//PubDate/Year/text()"))
    if y.isdigit():
        year = int(y)
    else:
        md = "".join(pm.xpath(".//PubDate/MedlineDate/text()"))
        m = re.search(r"(19|20|21)\d{2}", md)
        year = int(m.group()) if m else None

    # Mesh terms (text)
    mesh = [norm("".join(mh.xpath(".//DescriptorName//text()"))) for mh in pm.xpath(".//MeshHeading")]
    mesh = "|".join([m for m in mesh if m])

    # RAG text (fallback to title if abstract missing)
    text = (title + "\n\n" + abstract).strip() or title

    return [pmid, title, abstract, year, journal, mesh, text]

def write_csv(out_path, rows):
    with gzip.open(out_path, "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pmid","title","abstract","year","journal","mesh","text"])
        for r in rows: w.writerow(r)

def iter_pubmed_files(paths):
    for p in paths:
        with gzip.open(p, "rb") as fh:
            # Stream parse PubmedArticle elements only
            ctx = etree.iterparse(fh, events=("end",), tag="PubmedArticle", recover=True, huge_tree=True)
            for _, elem in ctx:
                rec = extract_article(elem)
                if rec: yield rec
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]
            del ctx

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("inputs", nargs="+")
    args = ap.parse_args()

    # Stream straight to gzip’d CSV to keep disk I/O low
    with gzip.open(args.out, "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["pmid","title","abstract","year","journal","mesh","text"])
        for rec in iter_pubmed_files(args.inputs):
            w.writerow(rec)

