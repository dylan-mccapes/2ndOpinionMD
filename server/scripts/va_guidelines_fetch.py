#!/usr/bin/env python3
import os, re, argparse, time, hashlib, urllib.parse
import requests, psycopg2, bs4
from psycopg2.extras import execute_values

VA_PAGES = [
    "https://www.healthquality.va.gov/guidelines/pain/cot/",
    "https://www.healthquality.va.gov/guidelines/mh/mdd/",
]
DIRECT_PDFS = [
    "https://www.va.gov/painmanagement/docs/OSI_6_Toolkit_Taper_Benzodiazepines_Clinicians.pdf",
    "https://www.pbm.va.gov/PBM/AcademicDetailingService/Documents/Academic_Detailing_Educational_Material_Catalog/59_PTSD_NCPTSD_Provider_Helping_Patients_Taper_BZD.pdf",
]

def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    return re.sub(r'_+', '_', s).strip('_')

def get_sync_dsn():
    dsn = os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL")
    if dsn and "+asyncpg" in dsn:
        dsn = dsn.replace("+asyncpg", "")
    return dsn or "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd"

def scrape_pdf_links(page_url: str) -> list[str]:
    r = requests.get(page_url, timeout=30)
    r.raise_for_status()
    soup = bs4.BeautifulSoup(r.text, "html.parser")
    links = []
    for a in soup.select("a[href]"):
        href = urllib.parse.urljoin(page_url, a["href"])
        if href.lower().endswith(".pdf"):
            links.append(href)
    return sorted(set(links))

def fetch_pdf(url: str) -> tuple[str, bytes, str]:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    pdf_bytes = r.content
    path = urllib.parse.urlparse(url).path
    fname = os.path.basename(path) or hashlib.sha1(url.encode()).hexdigest() + ".pdf"
    title = os.path.splitext(fname)[0].replace("_", " ").title()
    slug = slugify(os.path.splitext(fname)[0])
    return slug, pdf_bytes, title

def upsert_docs(conn, rows):
    # rows: list of (slug, url, title, raw_pdf)
    with conn, conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO guidelines.va_docs(slug, url, title, raw_pdf)
            VALUES %s
            ON CONFLICT (slug) DO UPDATE
              SET url = EXCLUDED.url,
                  title = COALESCE(EXCLUDED.title, guidelines.va_docs.title),
                  raw_pdf = COALESCE(EXCLUDED.raw_pdf, guidelines.va_docs.raw_pdf),
                  updated_at = now()
        """, rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/va", help="folder to stash PDFs")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    all_pdf_urls = set(DIRECT_PDFS)
    for page in VA_PAGES:
        try:
            all_pdf_urls.update(scrape_pdf_links(page))
        except Exception as e:
            print(f"[warn] failed scrape: {page} -> {e}")

    print(f"Discovered {len(all_pdf_urls)} PDF links")

    rows = []
    for url in sorted(all_pdf_urls):
        try:
            slug, pdf_bytes, title = fetch_pdf(url)
            outpath = os.path.join(args.out, f"{slug}.pdf")
            with open(outpath, "wb") as f:
                f.write(pdf_bytes)
            rows.append((slug, url, title, psycopg2.Binary(pdf_bytes)))
            print(f"Fetched: {slug} ({len(pdf_bytes)} bytes)")
            time.sleep(0.3)
        except Exception as e:
            print(f"[warn] fetch failed: {url} -> {e}")

    if not rows:
        print("No rows to upsert.")
        return

    conn = psycopg2.connect(get_sync_dsn())
    upsert_docs(conn, rows)
    conn.close()
    print(f"Upserted {len(rows)} docs into guidelines.va_docs")

if __name__ == "__main__":
    main()

