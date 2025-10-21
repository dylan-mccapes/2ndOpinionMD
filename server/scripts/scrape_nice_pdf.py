#!/usr/bin/env python3
import os, sys, argparse, pathlib, urllib.parse, time
import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
TIMEOUT = 25

def default_url(doc: str, src: str) -> str:
    if src == "cks":
        return f"https://cks.nice.org.uk/topics/{doc.lower()}/"
    return f"https://www.nice.org.uk/guidance/{doc.lower()}/resources"

def _headers(referer=None):
    h = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "DNT": "1",
    }
    if referer:
        h["Referer"] = referer
    return h

def fetch(url, referer=None, method="GET", allow_redirects=True):
    fn = requests.get if method == "GET" else requests.head
    r = fn(url, headers=_headers(referer), timeout=TIMEOUT, allow_redirects=allow_redirects)
    r.raise_for_status()
    return r

def is_pdf_url(url, base):
    try:
        # quick check: suffix
        if url.lower().endswith(".pdf"):
            return True
        # HEAD check: does it serve PDF?
        r = fetch(urllib.parse.urljoin(base, url), method="HEAD")
        ctype = r.headers.get("Content-Type","").lower()
        return "application/pdf" in ctype
    except Exception:
        return False

def pick_pdf(soup, doc: str, base: str):
    # 1) obvious .pdf
    links = soup.find_all("a")
    candidates = []
    doc_lower = doc.lower()

    for a in links:
        href = (a.get("href") or "").strip()
        text = (a.get_text() or "").strip().lower()
        if not href:
            continue

        score = 0
        if href.lower().endswith(".pdf"):
            score += 5
        if "full guideline" in text or "nice guideline" in text or "pdf" in text:
            score += 3
        if doc_lower in href.lower() or doc_lower in text:
            score += 2
        if "/evidence/" in href.lower() or "/guidance/" in href.lower():
            score += 1

        # If the URL doesn't end with .pdf, try a HEAD to see if it's a PDF.
        if not href.lower().endswith(".pdf"):
            if is_pdf_url(href, base):
                score += 4

        if score > 0:
            candidates.append((score, href))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return urllib.parse.urljoin(base, candidates[0][1])

    # 2) last resort: any link that actually returns PDF via HEAD
    for a in links:
        href = (a.get("href") or "").strip()
        if href and is_pdf_url(href, base):
            return urllib.parse.urljoin(base, href)

    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", required=True)
    ap.add_argument("--src", default="nice", choices=["nice","cks"])
    ap.add_argument("--out", default="data/nice")
    ap.add_argument("--url")
    args = ap.parse_args()

    url = args.url or default_url(args.doc, args.src)
    os.makedirs(args.out, exist_ok=True)
    out_path = pathlib.Path(args.out) / f"{args.doc}.pdf"

    print(f"[info] GET {url}")
    try:
        html = fetch(url).text
    except Exception as e:
        # CKS sometimes returns 403 to non-browsers; try a print-view fallback.
        if args.src == "cks" and "403" in str(e):
            alt = url.rstrip("/") + "/?view=print"
            print(f"[warn] 403; retrying {alt}")
            html = fetch(alt, referer=url).text
        else:
            print(f"[error] failed to fetch landing page: {e}", file=sys.stderr)
            sys.exit(2)

    soup = BeautifulSoup(html, "html.parser")
    pdf_url = pick_pdf(soup, args.doc, url)
    if not pdf_url:
        print("[error] no PDF link found on the page", file=sys.stderr)
        sys.exit(3)

    print(f"[info] downloading {pdf_url}")
    try:
        r = fetch(pdf_url, referer=url)
    except Exception as e:
        print(f"[error] failed to fetch PDF: {e}", file=sys.stderr)
        sys.exit(4)

    with open(out_path, "wb") as f:
        f.write(r.content)
    print(f"✅ saved {out_path} ({out_path.stat().st_size:,} bytes)")

if __name__ == "__main__":
    main()
