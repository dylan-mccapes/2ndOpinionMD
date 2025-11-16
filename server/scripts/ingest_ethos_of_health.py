#!/usr/bin/env python3
"""
Ethos of Health Ingestion Script

Purpose:
  - Upsert the Ethos of Health framework documents into public.rag_corpus
    as a first-class RAG source (source='ethos_model').

Behavior:
  - Inserts/updates a small set of conceptual documents describing:
      * Module 1: Original Healthy Baseline
      * Module 2: Chronic Baseline Mode
      * Module 3: Diagnosis-Specific Stability / Stack Levels (summary)
      * Model overview / glossary
  - Computes ts (tsvector) inside Postgres for BM25/hybrid search.
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Project root / .env loading
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)


# ---------------------------------------------------------------------------
# DB helpers (mirrors pattern from ingest_snomed)
# ---------------------------------------------------------------------------

def get_database_url() -> str:
    """
    Get a usable Postgres connection URL.

    Priority:
      1) SYNC_DATABASE_URL (psql / psycopg style)
      2) DATABASE_URL (strip +asyncpg/+psycopg if present)
      3) local hard-coded fallbacks (same spirit as ingest_snomed.py)
    """
    sync_url = os.getenv("SYNC_DATABASE_URL")
    if sync_url:
        return sync_url

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Strip SQLAlchemy async driver hints if present
        if "+asyncpg" in db_url:
            return db_url.replace("+asyncpg", "")
        if "+psycopg" in db_url:
            return db_url.replace("+psycopg", "")
        return db_url

    fallbacks = [
        "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd",
        "postgresql://postgres:postgres@localhost/2ndopinionmd",
        "host=localhost dbname=2ndopinionmd user=postgres password=postgres",
        "postgresql:///2ndopinionmd",
        "postgresql://localhost/2ndopinionmd",
    ]
    for url in fallbacks:
        try:
            conn = psycopg2.connect(url)
            conn.close()
            print(f"Using database URL: {url}")
            return url
        except Exception as e:
            print(f"Failed to connect with {url}: {e}")
            continue

    raise ValueError("Could not connect to database with any fallback URL")


# ---------------------------------------------------------------------------
# Ethos of Health documents
# ---------------------------------------------------------------------------

# NOTE:
# - This is intentionally compact. You can expand text as you iterate.
# - Each entry becomes a row in rag_corpus with source='ethos_model'.
ETHOS_DOCS: List[Dict[str, Any]] = [
    {
        "source_id": "overview",
        "title": "Ethos of Health – Model Overview",
        "text": (
            "The Ethos of Health model describes a layered view of a patient's health "
            "over time. It distinguishes the original healthy baseline, the chronic "
            "baseline state with long-term conditions, and higher stack levels that "
            "represent acute destabilization or complexity.\n\n"
            "Key constructs include:\n"
            "- Baseline Integrity Score (0–100): how much of the original healthy "
            "  baseline remains intact.\n"
            "- Baseline Zones: Healthy Baseline, Partially Compromised, Baseline Lost.\n"
            "- Chronic Baseline Mode: the patient's stable day-to-day state with "
            "  chronic illness, including expected symptoms and lab values.\n"
            "- Deviation Score: how far the current state deviates from chronic "
            "  baseline, used to determine whether the patient is still in baseline "
            "  mode or has entered an acute phase.\n"
            "- Stack Levels: each confirmed diagnosis adds its own stack level, and "
            "  each level has its own internal stability zone.\n\n"
            "The model is designed to help clinicians and decision-support tools "
            "separate: (1) long-term loss of health, (2) stable chronic baseline, "
            "and (3) acute deviations that require escalation."
        ),
        "meta": {
            "guideline": "EthosOfHealth",
            "module": 0,
            "section": "Overview",
            "domain": "framework",
            "version": "v2",
        },
    },
    {
        "source_id": "module_1_original_baseline",
        "title": "Ethos of Health – Module 1: Original Healthy Baseline",
        "text": (
            "Module 1 defines the Original Healthy Baseline, which captures the "
            "patient's best attainable health state before chronic or irreversible "
            "conditions. It uses historical data, prior records, and congenital factors "
            "to estimate what 'healthy' means for this individual.\n\n"
            "Outputs:\n"
            "- Baseline Integrity Score (0–100): starts at 100 and subtracts points for "
            "  each chronic condition or permanent health deficit, weighted by "
            "  severity and organ system damage.\n"
            "- Baseline Zone:\n"
            "  * Healthy Baseline Zone (~90–100): original baseline essentially intact.\n"
            "  * Partially Compromised Baseline (~60–89): meaningful but incomplete "
            "    loss of original health.\n"
            "  * Baseline Lost (<60): substantial, often irreversible shift away from "
            "    the original healthy state.\n"
            "- Stack Level: the model escalates from Stack Level 0 (baseline intact) "
            "  to Stack Level 1 when the baseline is considered lost.\n\n"
            "Clinically, Module 1 answers: 'How far is this patient from their original "
            "health baseline, and have we crossed a threshold where restoration is "
            "no longer realistic and we are instead preserving a new chronic baseline?'"
        ),
        "meta": {
            "guideline": "EthosOfHealth",
            "module": 1,
            "section": "Original Healthy Baseline",
            "domain": "framework",
            "version": "v2",
        },
    },
    {
        "source_id": "module_2_chronic_baseline_mode",
        "title": "Ethos of Health – Module 2: Chronic Baseline Mode",
        "text": (
            "Module 2 describes the Chronic Baseline Mode, sometimes called the "
            "patient's 'normal chronic day.' It assumes that chronic conditions are "
            "present and focuses on whether the patient is currently in their usual "
            "stable state or has deviated into an acute episode.\n\n"
            "Inputs include:\n"
            "- A chronic baseline profile: expected symptom levels, typical exam "
            "  findings, and treatment-adjusted lab values during stable periods.\n"
            "- Current symptoms, signs, and labs at the time of assessment.\n"
            "- Potential triggers (e.g. infection, medication changes, stressors).\n\n"
            "The module calculates a Baseline Deviation Score by comparing current "
            "values to baseline norms. Thresholds produce zones such as:\n"
            "- Chronic Baseline Stable (Green Zone): current state matches expected "
            "  chronic baseline.\n"
            "- Borderline Shift (Yellow Zone): mild deviations that warrant closer "
            "  monitoring but do not yet represent an acute break.\n"
            "- Out-of-Baseline (Red Zone): significant deviation, often a flare or "
            "  new acute process. This escalates the patient to a higher Stack Level "
            "  and triggers acute-phase modules.\n\n"
            "Clinically, Module 2 helps distinguish routine chronic complaints from "
            "true destabilization that needs escalation or urgent evaluation."
        ),
        "meta": {
            "guideline": "EthosOfHealth",
            "module": 2,
            "section": "Chronic Baseline Mode",
            "domain": "framework",
            "version": "v2",
        },
    },
    {
        "source_id": "module_3_stack_level_stability",
        "title": "Ethos of Health – Module 3: Diagnosis-Specific Stack Levels and Zones",
        "text": (
            "Module 3 treats each confirmed diagnosis as its own stack level and assigns "
            "an internal stability zone (for example, 0–5) to that level. This allows "
            "the model to represent multiple diseases in parallel, each with its own "
            "compensation-versus-collapse state.\n\n"
            "For each diagnosis, the module considers:\n"
            "- Symptom severity and recent deltas from that diagnosis's baseline.\n"
            "- Disease-specific labs, imaging, and physiologic markers.\n"
            "- Prior flares, hospitalizations, or complications.\n\n"
            "The output is a per-diagnosis classification such as:\n"
            "- Zone 0–1: well-compensated and stable.\n"
            "- Zone 2–3: early or moderate instability, rising flare risk.\n"
            "- Zone 4–5: decompensation or imminent collapse, requiring active "
            "  management and often higher-level care.\n\n"
            "This per-diagnosis stack-and-zone view integrates with the overall "
            "Ethos of Health framework, so that global decisions (for example, about "
            "heart failure versus diabetes) can respect the independent stability "
            "profiles of each condition."
        ),
        "meta": {
            "guideline": "EthosOfHealth",
            "module": 3,
            "section": "Diagnosis-Specific Stack Levels and Zones",
            "domain": "framework",
            "version": "v2",
        },
    },
]


# ---------------------------------------------------------------------------
# Core upsert logic
# ---------------------------------------------------------------------------

def upsert_ethos_docs(conn, dry_run: bool = False) -> None:
    """
    Upsert ETHOS_DOCS into public.rag_corpus.

    - source      = 'ethos_model'
    - source_id   = module-specific
    - title, text = from ETHOS_DOCS
    - meta        = JSONB with guideline/module metadata
    - ts          = to_tsvector('english', title || ' ' || text)
    """
    if dry_run:
        print("DRY RUN: would upsert the following Ethos of Health docs into public.rag_corpus:")
        for doc in ETHOS_DOCS:
            print(
                f"- source='ethos_model', source_id='{doc['source_id']}', "
                f"title='{doc['title']}'"
            )
        print(f"Total docs: {len(ETHOS_DOCS)}")
        return

    values = []
    for doc in ETHOS_DOCS:
        meta_json = json.dumps(doc.get("meta", {}), separators=(",", ":"))
        values.append(
            (
                "ethos_model",           # source
                doc["source_id"],        # source_id
                doc["title"],            # title
                doc["text"],             # text
                meta_json,               # meta as text, cast to jsonb in SQL
            )
        )

    sql = """
        INSERT INTO public.rag_corpus (source, source_id, title, text, meta, ts)
        SELECT
            v.source,
            v.source_id,
            v.title,
            v.text,
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
    print(f"Upserted {len(ETHOS_DOCS)} Ethos of Health docs into public.rag_corpus (source='ethos_model').")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Upsert Ethos of Health docs into rag_corpus")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be inserted/updated without modifying the database",
    )
    args = parser.parse_args()

    database_url = get_database_url()
    print(f"Connecting to database: {database_url}")

    if args.dry_run:
        # For dry-run we don't actually need to hit DB, but we validate connectivity anyway.
        try:
            conn = psycopg2.connect(database_url)
            conn.close()
            print("Database connectivity OK.")
        except Exception as e:
            print(f"WARNING: could not validate DB connection in dry-run: {e}")
        upsert_ethos_docs(conn=None, dry_run=True)  # type: ignore[arg-type]
        return

    with psycopg2.connect(database_url) as conn:
        upsert_ethos_docs(conn, dry_run=False)

    print("Ethos of Health ingestion completed.")


if __name__ == "__main__":
    main()

