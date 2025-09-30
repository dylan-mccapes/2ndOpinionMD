#!/usr/bin/env python3
import os, re, argparse
import psycopg2
from psycopg2.extras import execute_values

# Use pdfminer.six (pip install pdfminer.six)
from pdfminer.high_level import extract_text

KEY_TAGS = [
    ("taper", "tapering"),
    ("benzodiazep", "benzodiazepine"),
    ("diazepam", "benzodiazepine"),
    ("clonazepam", "benzodiazepine"),
    ("alprazolam", "benzodiazepine"),
    ("opioid", "opioid"),
    ("depress", "mdd"),
    ("major depressive", "mdd"),
    ("ptsd", "ptsd"),
    ("pain", "pain"),
]

def get_sync_dsn():
    dsn = os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL")
    if dsn and "+asyncpg" in dsn:
        dsn = dsn.replace("+asyncpg", "")
    return dsn or "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd"

def chunk_text(txt: str, max_chars=1800, overlap=200):
    txt = re.sub(r'\s+', ' ', txt).strip()
    if not txt:
        return []
    chunks = []
    i = 0
    n = len(txt)
    while i < n:
        j = min(n, i + max_chars)
        # try to break at a sentence end if possible
        k = txt.rfind('. ', i, j)
        if k == -1 or k < i + 600:
            k = j
        else:
            k += 1
        chunks.append(txt[i:k].strip())
        i = max(k - overlap, i + 1)
    return chunks

def infer_tags(text):
    tags = set()
    lt = text.lower()
    for needle, tag in KEY_TAGS:
        if needle in lt:
            tags.add(tag)
    return sorted(tags)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="indir", default="data/va", help="where PDFs were saved")
    args = ap.parse_args()

    conn = psycopg2.connect(get_sync_dsn())
    cur = conn.cursor()

    cur.execute("SELECT slug, title, raw_pdf FROM guidelines.va_docs ORDER BY slug")
    docs = cur.fetchall()

    total_sections = 0
    for slug, title, raw in docs:
        if not raw:
            print(f"[skip] no PDF in DB for {slug}")
            continue
        # stash to tmp and parse
        tmp = os.path.join(args.indir, f"{slug}.pdf")
        if not os.path.exists(tmp):
            with open(tmp, "wb") as f:
                f.write(raw.tobytes() if hasattr(raw, "tobytes") else raw)
        try:
            full_text = extract_text(tmp)
        except Exception as e:
            print(f"[warn] pdf extract failed {slug}: {e}")
            continue

        chunks = chunk_text(full_text, max_chars=2000, overlap=250)
        rows = []
        for idx, ch in enumerate(chunks, start=1):
            h = f"{title or slug.replace('_',' ').title()} — Chunk {idx}"
            tags = infer_tags(ch)
            rows.append((slug, h, ch, tags))

        if not rows:
            continue

        # Clear existing sections for this doc_slug then insert
        cur.execute("DELETE FROM guidelines.va_sections WHERE doc_slug = %s", (slug,))
        execute_values(cur, """
            INSERT INTO guidelines.va_sections (doc_slug, heading, text_plain, tags, ts)
            VALUES %s
        """, [ (r[0], r[1], r[2], r[3], r[2]) for r in rows ],
            template="(%s,%s,%s,%s,to_tsvector('english', %s))")
        total_sections += len(rows)
        print(f"Upserted {len(rows)} sections for {slug}")

    conn.commit()
    conn.close()
    print(f"Done. Total VA sections: {total_sections}")

if __name__ == "__main__":
    main()

