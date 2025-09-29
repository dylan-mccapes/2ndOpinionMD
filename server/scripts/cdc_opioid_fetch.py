# server/scripts/cdc_opioid_fetch.py
import argparse, hashlib, requests, time
from urllib.parse import urlparse
CDC_PAGES = [
  ("mmwr_2022_full", "https://www.cdc.gov/mmwr/volumes/71/rr/rr7103a1.htm"),
  ("mmwr_2022_pdf",  "https://stacks.cdc.gov/view/cdc/122248/cdc_122248_DS1.pdf"),
  ("recommendations","https://www.cdc.gov/overdose-prevention/hcp/clinical-guidance/recommendations-and-principles.html"),
  ("pdmp",           "https://www.cdc.gov/overdose-prevention/hcp/clinical-guidance/prescription-drug-monitoring-programs.html"),
  ("whats_different","https://www.cdc.gov/overdose-prevention/hcp/clinical-guidance/whats-different.html"),
  ("admin_apply",    "https://www.cdc.gov/overdose-prevention/hcp/clinical-guidance/healthcare-admin-applying-guidelines.html"),
  ("linkage_to_care","https://www.cdc.gov/overdose-prevention/hcp/clinical-guidance/linkage-to-care.html"),
]

def fetch(url):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.content

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    import os, json
    os.makedirs(args.out, exist_ok=True)
    manifest = []
    for slug, url in CDC_PAGES:
        data = fetch(url)
        ext = ".pdf" if url.lower().endswith(".pdf") else ".html"
        fn  = f"{args.out}/{slug}{ext}"
        open(fn, "wb").write(data)
        sha = hashlib.sha256(data).hexdigest()
        manifest.append({"slug": slug, "url": url, "file": fn, "sha256": sha})
        time.sleep(0.8)
    open(f"{args.out}/manifest.json", "w").write(json.dumps(manifest, indent=2))
    print("Fetched", len(manifest), "files")

