#!/usr/bin/env python
"""
One-off ingester for EoH Gold 2025 module text into rag_corpus.

This bypasses PDF parsing and just stuffs the module text directly,
so it can be embedded like any other guideline source.

Run from repo root:

    python server/scripts/ingest_eoh_gold_modules.py

Assumes:
  - DB DSN via SYNC_DATABASE_URL (or falls back to postgresql://localhost/2ndopinionmd)
  - EoH Gold 2025 was previously ingested as source='eoh_gold_2025'
  - server/eoh/module_49b_policy.py and module_49c_policy.py exist
  - Each module exposes a string constant with the policy text
    (e.g., MODULE_TEXT or POLICY_TEXT)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import psycopg

# ---------------------------------------------------------------------
# Ensure repo root (containing "server/") is on sys.path
# ---------------------------------------------------------------------

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]  # .../2ndOpinionMD-MVP

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Now this import should work
from server.eoh import module_49b_policy, module_49c_policy  # type: ignore

# Use same DSN pattern as ingest_guideline_pdf
DSN = os.getenv("SYNC_DATABASE_URL", "postgresql://localhost/2ndopinionmd")
SOURCE = "eoh_gold_2025"  # must match what you already used in rag_corpus


def _extract_policy_text(mod: object, module_name: str) -> str:
    """
    Try to find a string constant on the policy module that holds the full
    policy text. If you named it differently, add that name to the list below.
    """
    candidate_attrs = (
        "MODULE_TEXT",
        "POLICY_TEXT",
        "TEXT",
        "BODY",
        "DOC",
    )

    for attr in candidate_attrs:
        if hasattr(mod, attr):
            val = getattr(mod, attr)
            if isinstance(val, str) and val.strip():
                print(f"[EOH_INGEST] Using {module_name}.{attr} for policy text")
                return val.strip()

    raise SystemExit(
        f"[EOH_INGEST] Could not find policy text on {module_name}. "
        f"Add a string constant like MODULE_TEXT = \"...\" to that module."
    )


def build_rows() -> List[Dict[str, Any]]:
    """
    Build a small list of rows to insert into rag_corpus.
    For v1 we treat each module as a single 'page'-like document.
    """
    rows: List[Dict[str, Any]] = []

    # 49B
    text_49b = _extract_policy_text(module_49b_policy, "module_49b_policy")
    if text_49b:
        meta_49b: Dict[str, Any] = {
            "guideline_source": SOURCE,
            "ethos_module_id": "49b",
            "year": 2025,
            "topic": "ethos_of_health",
            "disease": "multimorbidity",
            "society": "EoH",
            "kind": "ethos_module",
            "module_label": "EoH Gold 2025 – Module 49B Diagnostic Consistency Sentinel",
        }
        rows.append(
            {
                "source_id": f"{SOURCE}:mod_49b",
                "title": "EoH Gold 2025 – Module 49B Diagnostic Consistency Sentinel Policy",
                "text": text_49b,
                "meta": json.dumps(meta_49b),
            }
        )

    # 49C
    text_49c = _extract_policy_text(module_49c_policy, "module_49c_policy")
    if text_49c:
        meta_49c: Dict[str, Any] = {
            "guideline_source": SOURCE,
            "ethos_module_id": "49c",
            "year": 2025,
            "topic": "ethos_of_health",
            "disease": "multimorbidity",
            "society": "EoH",
            "kind": "ethos_module",
            "module_label": "EoH Gold 2025 – Module 49C Diagnostic Update Reactor",
        }
        rows.append(
            {
                "source_id": f"{SOURCE}:mod_49c",
                "title": "EoH Gold 2025 – Module 49C Diagnostic Update Reactor Policy",
                "text": text_49c,
                "meta": json.dumps(meta_49c),
            }
        )

    return rows


def main() -> None:
    rows = build_rows()
    if not rows:
        raise SystemExit("[EOH_INGEST] No module text found; check module_49b/49c policy modules.")

    dsn = DSN
    print(f"[EOH_INGEST] Connecting to DB: {dsn}")
    conn = psycopg.connect(dsn)
    cur = conn.cursor()

    print(f"[EOH_INGEST] Upserting {len(rows)} rows into rag_corpus for source={SOURCE}")

    cur.executemany(
        """
        INSERT INTO rag_corpus (source, source_id, title, text, meta)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (source, source_id) DO UPDATE
          SET title = EXCLUDED.title,
              text  = EXCLUDED.text,
              meta  = EXCLUDED.meta
        """,
        [
            (SOURCE, row["source_id"], row["title"], row["text"], row["meta"])
            for row in rows
        ],
    )
    conn.commit()
    cur.close()
    conn.close()

    print(f"[EOH_INGEST] Done. Upserted {len(rows)} rows for source={SOURCE}.")


if __name__ == "__main__":
    main()