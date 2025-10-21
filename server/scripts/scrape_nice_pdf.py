#!/usr/bin/env python3
"""
Download a primary PDF for a NICE Guidance or CKS entry.

Examples:
  python server/scripts/scrape_nice_pdf.py --doc NG220 --src nice --out data/nice
  python server/scripts/scrape_nice_pdf.py --doc hypertension --src cks --out data/nice
"""
import os, re, sys, argparse, pathlib, urllib.parse, time
import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (compatible; 2ndOpinionMD-NICE-Scraper/1.0)"
TIMEOUT = 20

def default_url(doc: str, src: str) -> str:
    if src == "cks":
        # CKS entries are pages; PDFs may be per-topic PDFs
        return f"https://cks.nice.org.uk/topics/{doc.lower()}/"
    # Guidance "resources" page
    return f"https://www.nice.org.uk/guidance/{doc.lower()}/resources"

def pick_pdf(links, doc):
    """
    Heuristics:
      1) Any link text mentioning 'full guideline' or 'NICE guideline' or endswith .pdf
      2) Prefer links containing the doc key (case-insensitive)
      3) Otherwise, first .pdf
    """
    pdfs = []
    doc_lower = doc.lower()
    for a in links:
        href = a.get("href") or ""
        text = (a.get_text() or "").strip().lower()
        if not href.lower().endswith(".pdf"):
            continue
        score = 0
        if "full guideline" in text or "nice guideline" in text or "pdf" == href[-3:].lower():
            score += 5
        if doc_lower in href.lower() or doc_lower in text:
            score += 3
        if "guidance" in href.lower():
            score += 1
        pdfs.append((score, href, text))
    pdfs.sort(key=lambda x: x[0], reverse=True)
    return pdfs[0][1] if pdfs else None

def resolve(url, base):
    return urllib.parse.urljoin(base, url)

def fetch(url):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    return r

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", required=True, help="NG220, CG173, QS214, etc. For CKS use the topic slug (e.g., hypertension).")
    ap.add_argument("--src", default="nice", choices=["nice","cks"])
    ap.add_argument("--out", default="data/nice")
    ap.add_argument("--url", help="Override landing/resources URL")
    args = ap.parse_args()

    url = args.url or default_url(args.doc, args.src)
    os.makedirs(args.out, exist_ok=True)
    out_path = pathlib.Path(args.out) / f"{args.doc}.pdf"

    print(f"[info] GET {url}")
    try:
        html = fetch(url).text
    except Exception as e:
        print(f"[error] failed to fetch landing page: {e}", file=sys.stderr)
        sys.exit(2)

    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a")
    pdf_rel = pick_pdf(links, args.doc)
    if not pdf_rel:
        # fallback: any .pdf on the page
        for a in links:
            href = a.get("href") or ""
            if href.lower().endswith(".pdf"):
                pdf_rel = href
                break
    if not pdf_rel:
        print("[error] no PDF link found on the page", file=sys.stderr)
        sys.exit(3)

    pdf_url = resolve(pdf_rel, url)
    print(f"[info] downloading {pdf_url}")
    try:
        r = fetch(pdf_url)
    except Exception as e:
        print(f"[error] failed to fetch PDF: {e}", file=sys.stderr)
        sys.exit(4)

    with open(out_path, "wb") as f:
        f.write(r.content)
    sz = out_path.stat().st_size
    print(f"✅ saved {out_path} ({sz:,} bytes)")

if __name__ == "__main__":
    main()

