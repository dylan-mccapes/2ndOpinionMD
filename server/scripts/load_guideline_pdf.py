# server/scripts/load_guideline_pdf.py
import hashlib, json, os, sys, subprocess
from pathlib import Path
import psycopg
from psycopg.rows import dict_row

try:
    from dotenv import load_dotenv
    ROOT = Path(__file__).resolve().parents[2]  # project root
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / "server/.env")  # second chance
except Exception:
    pass

DB_URL = os.environ.get("SYNC_DATABASE_URL") or os.environ.get("DATABASE_URL")
assert DB_URL, "Set SYNC_DATABASE_URL or DATABASE_URL in your environment or .env"

SRC_KEY = os.environ.get("SRC_KEY", "nice")
DOC_KEY = os.environ.get("DOC_KEY", "NG220")
TITLE   = os.environ.get("TITLE", "NICE Guideline NG220 (Multiple Sclerosis)")
URL     = os.environ.get("URL", "")
PDF     = Path(os.environ["PDF"])

def sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()

def run(*cmd):
    subprocess.run(cmd, check=True)

def extract_text(pdf: Path) -> str:
    txt = pdf.with_suffix(".txt")
    # Try direct; fallback to OCR+extract
    try:
        run("pdftotext", "-layout", "-enc", "UTF-8", str(pdf), str(txt))
        if txt.exists() and txt.stat().st_size > 0:
            return txt.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        pass
    ocr_pdf = pdf.with_name(pdf.stem + ".ocr.pdf")
    run("ocrmypdf", "--skip-text", "--force-ocr", "--output-type", "pdf", str(pdf), str(ocr_pdf))
    run("pdftotext", "-layout", "-enc", "UTF-8", str(ocr_pdf), str(txt))
    return txt.read_text(encoding="utf-8", errors="ignore")

def split_sections(text: str):
    # naive splitter: headings lines with ### markers (preprocessed) or big gaps
    import re
    chunks, cur = [], []
    for line in text.splitlines():
        if re.match(r'^\s*[A-Z0-9][A-Z0-9\s\.\-:]{6,}$', line.strip()):
            if cur:
                chunks.append(("\n".join(cur[:1])[:200], "\n".join(cur)))
                cur = []
        cur.append(line)
    if cur:
        chunks.append(("\n".join(cur[:1])[:200], "\n".join(cur)))
    # Ensure at least one big section
    if not chunks:
        chunks = [("Full document", text)]
    return chunks

with psycopg.connect(DB_URL, row_factory=dict_row) as conn, conn.cursor() as cur:
    # Ensure source exists
    cur.execute("INSERT INTO guidelines.sources (key,name) VALUES (%s,%s) ON CONFLICT (key) DO NOTHING",
                (SRC_KEY, SRC_KEY.upper()))
    # Insert doc
    text_full = extract_text(PDF)
    b = PDF.read_bytes()
    sh = sha256(PDF)
    cur.execute("""
        INSERT INTO guidelines.docs (source_key, doc_key, title, url, version, sha256, mime_type, bytes, text_full)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (source_key, doc_key, version) DO UPDATE SET title=EXCLUDED.title
        RETURNING id
    """, (SRC_KEY, DOC_KEY, TITLE, URL, None, sh, "application/pdf", psycopg.Binary(b), text_full))
    doc_id = cur.fetchone()["id"]

    # Sections
    sections = split_sections(text_full)
    for i, (heading, sect_text) in enumerate(sections, 1):
        cur.execute("""
            INSERT INTO guidelines.sections (doc_id, ord, heading, text)
            VALUES (%s,%s,%s,%s) RETURNING id
        """, (doc_id, i, heading, sect_text))
        sect_id = cur.fetchone()["id"]

        # Stage to RAG
        title = f"{DOC_KEY}  {heading or TITLE}"
        meta = json.dumps({
            "source_key": SRC_KEY, "doc_key": DOC_KEY, "url": URL,
            "section_ord": i, "section_heading": heading
        })
        cur.execute("""
            INSERT INTO public.rag_corpus (source, title, text, meta, doc_id, sect_id)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (SRC_KEY, title, sect_text, meta, doc_id, sect_id))
    conn.commit()

print(f"Loaded {len(sections)} sections for {DOC_KEY}")

