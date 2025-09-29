# server/scripts/cdc_opioid_parse.py
import os
import argparse, json, bs4, psycopg2, datetime
from pathlib import Path

TAG_RULES = {
  "pdmp": ["pdmp","prescription drug monitoring"],
  "linkage_to_care": ["linkage","medication for opioid use disorder","moud","buprenorphine","methadone"],
  "tapering": ["taper","tapering"],
  "naloxone": ["naloxone"],
  "nonopioid_preferred": ["nonopioid","non-opioid"],
}

def heur_tags(text):
    t = text.lower()
    tags = []
    for tag, kws in TAG_RULES.items():
        if any(k in t for k in kws):
            tags.append(tag)
    return tags

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="indir", required=True)
    args = ap.parse_args()

    m = json.loads(open(Path(args.indir)/"manifest.json").read())
    conn = psycopg2.connect(dsn=os.environ["SYNC_DATABASE_URL"])
    cur = conn.cursor()

    for item in m:
        p = Path(item["file"])
        if p.suffix == ".pdf":
            # store in docs as binary; we do not section it
            cur.execute("""
                INSERT INTO guidelines.cdc_docs (source_key, slug, url, title, raw_pdf, checksum)
                VALUES ('cdc_opioid', %s, %s, %s, %s, %s)
                ON CONFLICT (source_key, slug) DO UPDATE SET raw_pdf = EXCLUDED.raw_pdf, checksum=EXCLUDED.checksum
                RETURNING doc_id
            """, (item["slug"], item["url"], "CDC Opioid Guideline (PDF)", p.read_bytes(), item["sha256"]))
            cur.fetchone()
        else:
            html = open(p, "rb").read()
            soup = bs4.BeautifulSoup(html, "html.parser")
            title = soup.title.text.strip() if soup.title else item["slug"]
            cur.execute("""
                INSERT INTO guidelines.cdc_docs (source_key, slug, url, title, raw_html, checksum)
                VALUES ('cdc_opioid', %s, %s, %s, %s, %s)
                ON CONFLICT (source_key, slug) DO UPDATE SET raw_html=EXCLUDED.raw_html, checksum=EXCLUDED.checksum
                RETURNING doc_id
            """, (item["slug"], item["url"], title, html.decode("utf-8", "ignore"), item["sha256"]))
            doc_id = cur.fetchone()[0]
            # shard into sections by h2/h3
            secs = soup.select("h2, h3")
            order = 0
            for h in secs:
                body_nodes = []
                sib = h.find_next_sibling()
                while sib and sib.name not in ["h2","h3"]:
                    body_nodes.append(sib)
                    sib = sib.find_next_sibling()
                text_plain = " ".join(x.get_text(" ", strip=True) for x in body_nodes)[:20000]
                rec_num = None
                if "recommendation" in h.get_text(" ", strip=True).lower():
                    # naive capture like "Recommendation 2"
                    rec_num = next((w for w in h.get_text().split() if w.isdigit()), None)
                    if rec_num:
                        rec_num = f"R{rec_num}"
                cur.execute("""
                  INSERT INTO guidelines.cdc_sections (doc_id, anchor, heading, section_order, text_plain, text_html, rec_number, tags)
                  VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (doc_id, None, h.get_text(" ", strip=True), order, text_plain, str(h)+ "".join(str(n) for n in body_nodes), rec_num, heur_tags(text_plain)))
                order += 1

    conn.commit()
    cur.close(); conn.close()

