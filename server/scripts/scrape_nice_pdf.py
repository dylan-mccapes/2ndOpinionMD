#!/usr/bin/env python3
import os, sys, argparse, pathlib, urllib.parse
import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
TIMEOUT = 25

def default_url(doc: str, src: str) -> str:
    return f"https://www.nice.org.uk/guidance/{doc.lower()}/resources" if src=="nice" else f"https://cks.nice.org.uk/topics/{doc.lower()}/"

def _headers(ref=None):
    h = {"User-Agent": UA, "Accept":"*/*", "Accept-Language":"en-US,en;q=0.9"}
    if ref: h["Referer"]=ref
    return h

def head(url, ref=None):
    r = requests.head(url, headers=_headers(ref), timeout=TIMEOUT, allow_redirects=True)
    r.raise_for_status(); return r

def get(url, ref=None):
    r = requests.get(url, headers=_headers(ref), timeout=TIMEOUT, allow_redirects=True)
    r.raise_for_status(); return r

def is_pdf_response(resp):
    return "application/pdf" in (resp.headers.get("Content-Type","").lower())

def absolutize(base, href):
    return urllib.parse.urljoin(base, href)

def find_pdf_link(soup, base, doc_lower):
    # 1) direct .pdf links
    for a in soup.find_all("a"):
        href = (a.get("href") or "").strip()
        if not href: continue
        if href.lower().endswith(".pdf"):
            return absolutize(base, href)
    # 2) links that contain "-pdf-" pattern (NICE resources)
    for a in soup.find_all("a"):
        href = (a.get("href") or "").strip().lower()
        if not href: continue
        if "-pdf-" in href or "/download?" in href or "resources" in href:
            cand = absolutize(base, href)
            try:
                r = head(cand, ref=base)
                if is_pdf_response(r): return cand
            except: pass
    # 3) try “Download PDF” text
    for a in soup.find_all("a"):
        text = (a.get_text() or "").strip().lower()
        href = (a.get("href") or "").strip()
        if "download pdf" in text and href:
            cand = absolutize(base, href)
            try:
                r = head(cand, ref=base)
                if is_pdf_response(r): return cand
            except: pass
    return None

def resolve_to_pdf(url):
    # If URL already serves PDF, done
    try:
        r = head(url)
        if is_pdf_response(r): return url
    except: pass
    # else fetch HTML and look inside for PDF link
    html = get(url).text
    soup = BeautifulSoup(html, "html.parser")
    doc_lower = url.split("/")[-2].lower() if "/guidance/" in url else ""
    link = find_pdf_link(soup, url, doc_lower)
    if not link:
        # sometimes resources page link points to a landing page; open that and find the .pdf
        for a in soup.find_all("a"):
            href = (a.get("href") or "").strip()
            if not href: continue
            page = absolutize(url, href)
            try:
                h = head(page, ref=url)
                if is_pdf_response(h): return page
                if "text/html" in h.headers.get("Content-Type","").lower():
                    inner = get(page, ref=url).text
                    inner_soup = BeautifulSoup(inner, "html.parser")
                    link = find_pdf_link(inner_soup, page, doc_lower)
                    if link: return link
            except: pass
    return link

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", required=True)
    ap.add_argument("--src", default="nice", choices=["nice","cks"])
    ap.add_argument("--out", default="data/nice")
    ap.add_argument("--url")
    args = ap.parse_args()

    landing = args.url or default_url(args.doc, args.src)
    print(f"[info] GET {landing}")

    pdf_url = resolve_to_pdf(landing)
    if not pdf_url:
        print("[error] no PDF link found on the page", file=sys.stderr); sys.exit(3)

    r = get(pdf_url, ref=landing)
    if not is_pdf_response(r):
        print(f"[error] resolved URL is not a PDF (Content-Type={r.headers.get('Content-Type')})", file=sys.stderr); sys.exit(4)

    os.makedirs(args.out, exist_ok=True)
    # name using last path segment
    fname = urllib.parse.unquote(urllib.parse.urlparse(pdf_url).path.split("/")[-1]) or f"{args.doc}.pdf"
    if not fname.lower().endswith(".pdf"):
        fname = f"{fname}.pdf"
    out_path = pathlib.Path(args.out) / fname

    with open(out_path, "wb") as f: f.write(r.content)
    print(f"✅ saved {out_path} ({out_path.stat().st_size:,} bytes)")

if __name__ == "__main__":
    main()
