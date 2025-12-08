# server/scripts/ingest_eoh_gold_2025_from_pdf.py

import re
import textwrap
from pathlib import Path
from typing import List, Tuple

import psycopg2
from pypdf import PdfReader


PDF_PATH = Path("data/guidelines/eoh_gold_2025.pdf")
SOURCE = "eoh_gold_2025"

# Adjust for your DSN
PG_DSN = "dbname=2ndopinionmd"


def extract_modules_from_pdf() -> List[Tuple[str, str, str]]:
    """
    Returns list of (module_id, title, text) tuples.
    module_id will be like '1', '2', '3A', '49B', '49C'.
    """

    reader = PdfReader(str(PDF_PATH))
    full_text = ""

    for page in reader.pages:
        full_text += page.extract_text() + "\n\n"

    # Split on "Module X" headings
    # Matches lines like "Module 1", "Module 3A", "Module 49B", etc.
    pattern = re.compile(r"(Module\s+(\d+[A-Z]?)[^\n]*?)\n", re.IGNORECASE)

    chunks: List[Tuple[str, str, str]] = []

    matches = list(pattern.finditer(full_text))
    for i, m in enumerate(matches):
        heading = m.group(1).strip()
        mod_id = m.group(2).strip()  # "1", "3A", "49B" etc.

        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        body = full_text[start:end].strip()

        # Derive a title: use heading line
        title = heading

        chunks.append((mod_id, title, body))

    return chunks


def ingest_modules(modules: List[Tuple[str, str, str]]) -> None:
    conn = psycopg2.connect(PG_DSN)
    conn.autocommit = True
    cur = conn.cursor()

    # 🔥 Intentional: we now rebuild the ENTIRE eoh_gold_2025 source
    # If you're nervous, comment this out and inspect first.
    #cur.execute("DELETE FROM rag_corpus WHERE source = %s;", (SOURCE,))

    insert_sql = """
        INSERT INTO rag_corpus (
            source,
            source_id,
            title,
            text
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (source_id) DO UPDATE
        SET title = EXCLUDED.title,
            text  = EXCLUDED.text;
    """

    for mod_id, title, body in modules:
        source_id = f"{SOURCE}:mod_{mod_id.lower()}"  # e.g. eoh_gold_2025:mod_49b
        text = textwrap.dedent(body).strip()

        cur.execute(
            insert_sql,
            (SOURCE, source_id, title, text),
        )
        print("Upserted", source_id)

    cur.close()
    conn.close()


def main():
    modules = extract_modules_from_pdf()
    print(f"Extracted {len(modules)} modules from {PDF_PATH}")
    for m in modules:
        print(" -", m[0], m[1][:60])

    ingest_modules(modules)


if __name__ == "__main__":
    main()
