#!/usr/bin/env python3
"""
Ingest the full EoH Canon (V5.2 + V6) into rag_corpus.

Parses EoH_Complete_Canon_V5.2_V6_For_Dylan.md by module boundaries,
chunks large modules into semantic sections, and upserts into Postgres
rag_corpus with source='eoh_canon_v6'.

Supports:
  --dry-run     Preview what would be inserted
  --jsonl-out   Write chunks to a JSONL file (for offline / session-only use)
  --db          Upsert into Postgres rag_corpus (default)

Run from repo root:
    python server/scripts/ingest_eoh_canon.py
    python server/scripts/ingest_eoh_canon.py --dry-run
    python server/scripts/ingest_eoh_canon.py --jsonl-out artifacts/eoh_canon_chunks.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env", override=False)
load_dotenv(REPO_ROOT / "server" / ".env", override=True)

SOURCE = "eoh_canon_v6"
CANON_PATH = REPO_ROOT / "EoH_Complete_Canon_V5.2_V6_For_Dylan.md"
MAX_CHUNK_CHARS = 6000

_MODULE_HEADER_RE = re.compile(
    r"^(?:\\?#\s*(?:\\?\*\\?\*)?)"
    r"(?:V[56](?:\.\d)?\s+)?"
    r"(?:Module\s+)?"
    r"(M\d+[A-Za-z]?)\s*[-—]\s*(.+?)(?:\\?\*\\?\*)?$",
    re.IGNORECASE,
)

_SECTION_HEADER_RE = re.compile(
    r"^(?:#{2,4}|\\?#\\?#)\s*(?:\\?\*\\?\*)?(.+?)(?:\\?\*\\?\*)?$"
)


def _clean_markdown(text: str) -> str:
    text = text.replace("\\#", "#").replace("\\*", "*")
    text = re.sub(r"\*{2,}", "", text)
    return text.strip()


def _extract_module_id(line: str) -> Optional[Tuple[str, str]]:
    cleaned = line.replace("\\#", "#").replace("\\*", "*").replace("**", "")
    cleaned = cleaned.strip().rstrip()

    m = re.match(
        r"^#\s*(?:V[56](?:\.\d)?\s+)?"
        r"(?:Module\s+(\d+[A-Za-z]?)|"   # "Module 55" -> group(1) = "55"
        r"(M\d+[A-Za-z]?))"              # "M55"       -> group(2) = "M55"
        r"\s*[-—]\s*(.+)",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        if m.group(1):
            mid = "M" + m.group(1).upper()
        else:
            mid = m.group(2).upper()
        name = m.group(3).strip()
        return mid, name
    return None


def parse_canon(path: Path) -> List[Dict[str, Any]]:
    """Parse the canon markdown into module chunks."""
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    modules: List[Dict[str, Any]] = []
    current_id: Optional[str] = None
    current_name: Optional[str] = None
    current_lines: List[str] = []
    current_version: str = "v5.2"

    def _flush():
        nonlocal current_id, current_name, current_lines
        if current_id and current_lines:
            body = "\n".join(current_lines).strip()
            if body:
                modules.append({
                    "module_id": current_id,
                    "module_name": current_name or current_id,
                    "version": current_version,
                    "body": body,
                })
        current_id = None
        current_name = None
        current_lines = []

    for line in lines:
        if "PART II" in line and "V6" in line:
            current_version = "v6"

        parsed = _extract_module_id(line)
        if parsed:
            _flush()
            current_id, current_name = parsed
            current_lines = [line]
        elif current_id is not None:
            current_lines.append(line)

    _flush()

    # Deduplicate: if the same module_id appears more than once, keep the last
    seen: Dict[str, int] = {}
    for i, m in enumerate(modules):
        seen[m["module_id"]] = i
    modules = [modules[i] for i in sorted(seen.values())]

    return modules


def _split_into_sections(body: str) -> List[Tuple[str, str]]:
    """Split a module body into (section_name, section_text) pairs."""
    section_patterns = [
        r"(?:^|\n)(?:#{2,4}|\\?#\\?#)\s*(?:\\?\*\\?\*)?(.+?)(?:\\?\*\\?\*)?(?:\n|$)",
        r"(?:^|\n)(Purpose|Scope|Inputs?|Outputs?|Process|Logic|Governance|Constraints?|"
        r"Metrics|Tests?|Acceptance|Implementation|Checklist|Roadmap)"
        r"(?:\s*[\(/]|:|\n)",
    ]

    splits: List[Tuple[int, str]] = []
    for pat in section_patterns:
        for m in re.finditer(pat, body, re.IGNORECASE | re.MULTILINE):
            name = m.group(1).strip().rstrip("*").strip()
            if len(name) < 80:
                splits.append((m.start(), name))

    if not splits:
        return [("full", body)]

    splits.sort(key=lambda x: x[0])
    seen_positions = set()
    deduped = []
    for pos, name in splits:
        if pos not in seen_positions:
            seen_positions.add(pos)
            deduped.append((pos, name))
    splits = deduped

    sections: List[Tuple[str, str]] = []
    for i, (pos, name) in enumerate(splits):
        end = splits[i + 1][0] if i + 1 < len(splits) else len(body)
        chunk = body[pos:end].strip()
        if chunk:
            sections.append((name, chunk))

    if splits and splits[0][0] > 100:
        preamble = body[:splits[0][0]].strip()
        if preamble:
            sections.insert(0, ("overview", preamble))

    return sections


def chunk_modules(modules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert parsed modules into sized chunks for rag_corpus."""
    chunks: List[Dict[str, Any]] = []

    for mod in modules:
        mid = mod["module_id"]
        name = mod["module_name"]
        version = mod["version"]
        body = _clean_markdown(mod["body"])

        if len(body) <= MAX_CHUNK_CHARS:
            chunks.append({
                "source_id": f"{SOURCE}:{mid.lower()}",
                "title": f"EoH {version.upper()} {mid} — {name}",
                "text": body,
                "meta": {
                    "guideline_source": SOURCE,
                    "ethos_module_id": mid,
                    "version": version,
                    "topic": "ethos_of_health",
                    "kind": "ethos_module",
                    "section": "full",
                    "module_label": f"EoH {version.upper()} {mid} — {name}",
                },
            })
        else:
            sections = _split_into_sections(body)
            for sec_idx, (sec_name, sec_text) in enumerate(sections):
                sec_text_clean = _clean_markdown(sec_text)
                if not sec_text_clean:
                    continue

                if len(sec_text_clean) > MAX_CHUNK_CHARS:
                    sub_chunks = [
                        sec_text_clean[i:i + MAX_CHUNK_CHARS]
                        for i in range(0, len(sec_text_clean), MAX_CHUNK_CHARS)
                    ]
                    for sub_idx, sub in enumerate(sub_chunks):
                        sec_label = f"{sec_name}_part{sub_idx + 1}"
                        chunks.append({
                            "source_id": f"{SOURCE}:{mid.lower()}_s{sec_idx}p{sub_idx}",
                            "title": f"EoH {version.upper()} {mid} — {name} ({sec_label})",
                            "text": sub,
                            "meta": {
                                "guideline_source": SOURCE,
                                "ethos_module_id": mid,
                                "version": version,
                                "topic": "ethos_of_health",
                                "kind": "ethos_module",
                                "section": sec_label,
                                "module_label": f"EoH {version.upper()} {mid} — {name}",
                            },
                        })
                else:
                    chunks.append({
                        "source_id": f"{SOURCE}:{mid.lower()}_s{sec_idx}",
                        "title": f"EoH {version.upper()} {mid} — {name} ({sec_name})",
                        "text": sec_text_clean,
                        "meta": {
                            "guideline_source": SOURCE,
                            "ethos_module_id": mid,
                            "version": version,
                            "topic": "ethos_of_health",
                            "kind": "ethos_module",
                            "section": sec_name,
                            "module_label": f"EoH {version.upper()} {mid} — {name}",
                        },
                    })

    return chunks


def get_database_url() -> str:
    sync_url = os.getenv("SYNC_DATABASE_URL")
    if sync_url:
        return sync_url
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        for driver in ("+asyncpg", "+psycopg"):
            db_url = db_url.replace(driver, "")
        return db_url
    return "postgresql://localhost/2ndopinionmd"


def upsert_to_db(chunks: List[Dict[str, Any]]) -> None:
    import psycopg2
    from psycopg2.extras import execute_values

    url = get_database_url()
    print(f"[EOH_CANON] Connecting to: {url}")

    conn = psycopg2.connect(url)
    values = []
    for ch in chunks:
        values.append((
            SOURCE,
            ch["source_id"],
            ch["title"],
            ch["text"],
            json.dumps(ch["meta"], separators=(",", ":")),
        ))

    sql = """
        INSERT INTO public.rag_corpus (source, source_id, title, text, meta, ts)
        SELECT
            v.source, v.source_id, v.title, v.text,
            v.meta::jsonb,
            to_tsvector('english', v.title || ' ' || v.text)
        FROM (VALUES %s) AS v(source, source_id, title, text, meta)
        ON CONFLICT (source, source_id) DO UPDATE
        SET title = EXCLUDED.title,
            text  = EXCLUDED.text,
            meta  = EXCLUDED.meta,
            ts    = EXCLUDED.ts;
    """

    with conn.cursor() as cur:
        execute_values(cur, sql, values)
    conn.commit()
    conn.close()
    print(f"[EOH_CANON] Upserted {len(chunks)} chunks into rag_corpus (source='{SOURCE}').")


def write_jsonl(chunks: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for ch in chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")
    print(f"[EOH_CANON] Wrote {len(chunks)} chunks to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest EoH Canon into rag_corpus")
    parser.add_argument("--dry-run", action="store_true", help="Preview chunks without writing")
    parser.add_argument("--jsonl-out", type=Path, default=None, help="Write chunks to JSONL file")
    parser.add_argument("--canon-path", type=Path, default=CANON_PATH, help="Path to canon markdown")
    parser.add_argument("--db", action="store_true", default=False, help="Upsert into Postgres rag_corpus")
    args = parser.parse_args()

    canon_path = args.canon_path.expanduser().resolve()
    if not canon_path.is_file():
        print(f"[EOH_CANON] Canon file not found: {canon_path}")
        sys.exit(1)

    print(f"[EOH_CANON] Parsing: {canon_path}")
    modules = parse_canon(canon_path)
    print(f"[EOH_CANON] Found {len(modules)} modules")

    for m in modules:
        print(f"  {m['module_id']:6s} {m['version']:4s}  {m['module_name'][:60]:60s}  ({len(m['body']):,} chars)")

    chunks = chunk_modules(modules)
    print(f"\n[EOH_CANON] Generated {len(chunks)} chunks")

    total_chars = sum(len(c["text"]) for c in chunks)
    print(f"[EOH_CANON] Total text: {total_chars:,} chars across {len(chunks)} chunks")
    print(f"[EOH_CANON] Avg chunk: {total_chars // max(1, len(chunks)):,} chars")
    print(f"[EOH_CANON] Max chunk: {max(len(c['text']) for c in chunks):,} chars")

    if args.dry_run:
        print("\n[DRY RUN] Would write these chunks:")
        for ch in chunks:
            print(f"  {ch['source_id']:40s}  {len(ch['text']):5,} chars  {ch['title'][:60]}")
        return

    if args.jsonl_out:
        write_jsonl(chunks, args.jsonl_out)

    if args.db:
        upsert_to_db(chunks)

    if not args.jsonl_out and not args.db:
        print("\n[EOH_CANON] No output target specified. Use --db, --jsonl-out, or both.")
        print("[EOH_CANON] Re-run with --dry-run to preview, or --jsonl-out <path> to write JSONL.")


if __name__ == "__main__":
    main()
