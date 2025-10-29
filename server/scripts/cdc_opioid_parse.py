# server/scripts/cdc_opioid_parse.py
import os, argparse, json, datetime, re
from pathlib import Path
import bs4
import psycopg2

TAG_RULES = {
  "pdmp": ["pdmp","prescription drug monitoring"],
  "linkage_to_care": ["linkage","medication for opioid use disorder","moud","buprenorphine","methadone"],
  "tapering": ["taper","tapering"],
  "naloxone": ["naloxone"],
  "nonopioid_preferred": ["nonopioid","non-opioid"],
}

REC_RE = re.compile(r'(?i)\brecommendation(?:s)?\s*(?:#|No\.|Number\s*)?([1-9][0-9]?)\b')

def heur_tags(text: str):
    t = (text or "").lower()
    tags = []
    for tag, kws in TAG_RULES.items():
        if any(k in t for k in kws):
            tags.append(tag)
    return tags

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="indir", required=True)
    args = ap.parse_args()

    manifest = json.loads(open(Path(args.indir)/"manifest.json").read())
    conn = psycopg2.connect(dsn=os.environ["SYNC_DATABASE_URL"])
    cur = conn.cursor()

    for item in manifest:
        p = Path(item["file"])
        slug = item["slug"]
        url  = item["url"]

        if p.suffix.lower() == ".pdf":
            # Store PDF as a doc row; not sectioned
            cur.execute("""
                INSERT INTO guidelines.cdc_docs (source_key, slug, url, title, raw_pdf, checksum)
                VALUES ('cdc_opioid', %s, %s, %s, %s, %s)
                ON CONFLICT (source_key, slug)
                  DO UPDATE SET raw_pdf = EXCLUDED.raw_pdf, checksum = EXCLUDED.checksum
                RETURNING doc_id
            """, (slug, url, "CDC Opioid Guideline (PDF)", p.read_bytes(), item["sha256"]))
            cur.fetchone()
            continue

        # HTML: parse and shard into sections
        html = open(p, "rb").read()
        soup = bs4.BeautifulSoup(html, "html.parser")
        title = soup.title.text.strip() if soup.title else slug

        cur.execute("""
            INSERT INTO guidelines.cdc_docs (source_key, slug, url, title, raw_html, checksum)
            VALUES ('cdc_opioid', %s, %s, %s, %s, %s)
            ON CONFLICT (source_key, slug)
              DO UPDATE SET raw_html = EXCLUDED.raw_html, checksum = EXCLUDED.checksum
            RETURNING doc_id
        """, (slug, url, title, html.decode("utf-8", "ignore"), item["sha256"]))
        doc_id = cur.fetchone()[0]

        # Make re-parses idempotent for this doc
        cur.execute("DELETE FROM guidelines.cdc_sections WHERE doc_id = %s;", (doc_id,))

        # h2/h3/h4 — CDC uses h4 for some Recommendation headings (e.g., R1, R2)
        secs = soup.select("h2, h3, h4")
        order = 0
        for h in secs:
            body_nodes = []
            sib = h.find_next_sibling()
            steps = 0
            while sib and sib.name not in ["h2","h3","h4"]:
                body_nodes.append(sib)
                sib = sib.find_next_sibling()   # <-- advance from sib
                steps += 1
                if steps > 1000: break          # safety valve to prevent any future runaway

            heading_txt = h.get_text(" ", strip=True)
            # Gather a short body preview to assist rec extraction if not in heading
            body_preview_txt = " ".join(x.get_text(" ", strip=True) for x in body_nodes[:2])
            text_plain = " ".join(x.get_text(" ", strip=True) for x in body_nodes)[:20000]
            text_html  = str(h) + "".join(str(n) for n in body_nodes)

            rec_number = None
            m = REC_RE.search(heading_txt) or REC_RE.search(body_preview_txt)
            if m:
                n = int(m.group(1))
                if 1 <= n <= 12:
                    rec_number = f"R{n}"

            cur.execute("""
                INSERT INTO guidelines.cdc_sections
                    (doc_id, anchor, heading, section_order, text_plain, text_html, rec_number, tags)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (doc_id, None, heading_txt, order, text_plain, text_html, rec_number, heur_tags(heading_txt + " " + text_plain)))
            order += 1

    conn.commit()
    cur.close(); conn.close()
