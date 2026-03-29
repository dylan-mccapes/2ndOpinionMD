#!/usr/bin/env python3
"""
Walk a PatientTimelineVision graph, extract drug names from medication node
previews, and normalize them against the RxNorm vocabulary in Postgres.

Phase 1 (mechanical): regex extraction of drug names from preview text,
         trigram search against ontology.rxnorm_conso.
Phase 2 (LLM):        GPT-4.1 batch judgement on ambiguous matches.

Usage (from 2ndOpinionMD-MVP/server):
    python3 scripts/normalize_medications_rxnorm.py \
      ../artifacts/timeline_full_20260327_1717/patient_timeline_vision_norman_eric_roberts_20260327_174843.json

    # With LLM judgement:
    python3 scripts/normalize_medications_rxnorm.py \
      ../artifacts/timeline_full_20260327_1717/patient_timeline_vision_norman_eric_roberts_20260327_174843.json \
      --llm

Challenge rating: Easy.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

script_dir = Path(__file__).resolve().parent
server_dir = script_dir.parent
parent_of_server = server_dir.parent

if str(parent_of_server) not in sys.path:
    sys.path.insert(0, str(parent_of_server))

os.chdir(server_dir)

from dotenv import load_dotenv
load_dotenv(server_dir / ".env", override=True)

from server.eoh.patient_timeline_vision import PatientTimelineVision

log = logging.getLogger("normalize_meds")

_KNOWN_NON_DRUGS = frozenset({
    "patient", "release", "medical", "information", "clinical", "notes",
    "continued", "orders", "visit", "telephone", "letters", "messages",
    "documents", "after", "summary", "encounter", "other", "labs",
    "walnut", "creek", "administration", "adult", "family", "medicine",
    "current", "outpatient", "hospital", "discharge", "report", "history",
    "allergies", "reactions", "status", "active", "inactive", "pending",
    "medications", "medication", "start", "date", "end", "oral",
    "intravenous", "topical", "injection", "tablet", "capsule", "solution",
    "cream", "ointment", "patch", "spray", "drops", "inhaler", "daily",
    "twice", "three", "four", "every", "hours", "take", "takes",
})

_DRUG_PATTERNS = [
    # "BRAND [GENERIC NAME]" or "BRAND [GENERIC SALT]" — very common in EHR exports
    re.compile(r"^([A-Za-z][\w\-]+(?:\s+[A-Za-z][\w\-]+)?)\s*\[([^\]]+)\]"),
    # "Generic (BRAND)" or "Generic (BRAND / BRAND2)" pattern
    re.compile(r"^([\w][\w\-]+(?:,?\s+[\w][\w\-]+)*)\s*\(([A-Z][\w\s/\-]+)\)"),
    # Tall-man lettering: buPROPion, ceFAZolin, amLODIPine, FLUoxetine, traMADol
    re.compile(
        r"^([a-z]+[A-Z]{2,}[a-z]+(?:\s+[A-Za-z][\w\-]+)?)"
        r"\s*(?:\(|[\[\s]\s*\d|,?\s+\d)",
    ),
    # Leading drug name followed by dose: "Prednisone 40 mg" or "Aspirin 81 mg"
    # Accepts mixed case (tall-man) at start of line
    re.compile(
        r"^((?:[A-Za-z][\w\-]+)(?:,?\s+(?:[A-Za-z][\w\-]+))*)"
        r"\s+\d+[\.,/]?\d*\s*(?:mg|mcg|g|gram|unit|mL|meq|%)",
        re.IGNORECASE,
    ),
    # "started X", "prescribed X", "taking X", "on X", "given X", "receiving X"
    re.compile(
        r"(?:start(?:ed|ing)?|prescrib(?:ed|ing)|tak(?:es?|ing)|using:?\s*"
        r"|(?:^|\s)on\s|given|receiving|administer(?:ed|ing)?|"
        r"continu(?:ed?|ing)|discontinu(?:ed?|ing)|stopp(?:ed|ing)|refill(?:ing)?)\s+"
        r"([A-Za-z][\w\-]+(?:\s+[A-Za-z][\w\-]+)?)",
        re.IGNORECASE,
    ),
    # "Drug Name 500 mg Oral Tab" or similar — dose + form after name
    re.compile(
        r"([\w][\w\-]+(?:\s+[\w][\w\-]+)?)\s+\d+[\.,]?\d*\s*"
        r"(?:mg|mcg|g|gram|unit|mL|meq|%)\s*(?:/[\d.]+\s*(?:mg|mL|g|gram))?\s+"
        r"(?:oral|iv|im|sq|subq|topical|inhal|inject|po|pr|sl|subl|od|bd|tds|qid|prn)",
        re.IGNORECASE,
    ),
    # Parenthetical brand: "(PROTONIX)" or "(PLAVIX)" or "(ANCEF/KEFZOL)"
    re.compile(r"\(([A-Z][A-Z\s/\-]{2,})\)", re.ASCII),
    # "vaccine given" pattern: "TYPE vaccine given"
    re.compile(r"^([A-Za-z][\w\-]+(?:\s+[\w\-]+)?)\s+vaccine\s+given", re.IGNORECASE),
    # Adherence/review mention: "adherence to Losartan"
    re.compile(
        r"(?:adherence|compliance|refill(?:ing)?|adjust(?:ing|ment)?|titrat(?:ed?|ing)|"
        r"increas(?:ed?|ing)|decreas(?:ed?|ing)|taper(?:ed|ing)?)\s+(?:to\s+|of\s+)?"
        r"([A-Za-z][\w\-]+(?:\s+[A-Za-z][\w\-]+)?)",
        re.IGNORECASE,
    ),
    # "Order for drugName" pattern
    re.compile(
        r"(?:order(?:ed)?|rx|prescription)\s+(?:for\s+)?"
        r"([A-Za-z][\w\-]+(?:\s+[A-Za-z][\w\-]+)?)",
        re.IGNORECASE,
    ),
]


def extract_drug_candidates(preview: str) -> List[str]:
    """Extract plausible drug name candidates from a medication event preview."""
    candidates: List[str] = []
    text = preview.strip()

    for pat in _DRUG_PATTERNS:
        for m in pat.finditer(text):
            for g in m.groups():
                if g:
                    name = g.strip().rstrip(".,;:")
                    # Normalize tall-man lettering for filtering
                    name_lower = name.lower()
                    if len(name) > 2 and name_lower not in _KNOWN_NON_DRUGS:
                        candidates.append(name)

    # Fallback: line starts with word(s) then a number
    if not candidates:
        m = re.match(
            r"^([A-Za-z][\w\-]+(?:,?\s+[A-Za-z][\w\-]+){0,2})\s*[\-\u2013\u2014,]?\s*\d",
            text,
        )
        if m:
            name = m.group(1).strip()
            if name.lower() not in _KNOWN_NON_DRUGS and len(name) > 2:
                candidates.append(name)

    seen: set = set()
    deduped: List[str] = []
    for c in candidates:
        key = c.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(c)
    return deduped


async def lookup_rxnorm_trgm(
    pool, drug_name: str, limit: int = 3
) -> List[Dict[str, str]]:
    """Trigram similarity search against ontology.rxnorm_conso."""
    sql = """
        SELECT rxcui, str, tty,
               similarity(str, $1) AS sim
        FROM ontology.rxnorm_conso
        WHERE str % $1
          AND tty IN ('IN', 'PIN', 'BN', 'SCD', 'SBD', 'SCDF', 'SBDF')
        ORDER BY sim DESC
        LIMIT $2;
    """
    rows = await pool.fetch(sql, drug_name, limit)
    return [{"rxcui": r["rxcui"], "str": r["str"], "tty": r["tty"],
             "sim": float(r["sim"])} for r in rows]


async def batch_llm_judge(
    client,
    ambiguous: List[Dict[str, Any]],
    model: str = "gpt-4.1",
    batch_size: int = 30,
) -> Dict[str, Dict[str, str]]:
    """Ask GPT-4.1 to pick the best RxNorm match for ambiguous drug extractions."""
    results: Dict[str, Dict[str, str]] = {}

    for i in range(0, len(ambiguous), batch_size):
        batch = ambiguous[i:i + batch_size]
        items = []
        for entry in batch:
            candidates_str = "; ".join(
                f"RXCUI={c['rxcui']} \"{c['str']}\" (tty={c['tty']}, sim={c['sim']:.2f})"
                for c in entry["candidates"]
            )
            items.append(
                f"EVENT {entry['event_id']}: preview=\"{entry['preview'][:200]}\"\n"
                f"  Extracted: \"{entry['extracted_name']}\"\n"
                f"  Candidates: {candidates_str}"
            )

        prompt = (
            "You are a pharmacist normalizing drug names. For each EVENT below, "
            "pick the best RxNorm candidate or respond 'NONE' if no candidate matches.\n\n"
            "Return JSON: {\"event_id\": {\"rxcui\": \"...\", \"drug_name\": \"...\"}, ...}\n"
            "Use the generic (IN) name when available. Only pick a match if you are confident.\n\n"
            + "\n\n".join(items)
        )

        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        try:
            batch_results = json.loads(raw)
            for eid, val in batch_results.items():
                if isinstance(val, dict) and val.get("rxcui") and val["rxcui"] != "NONE":
                    results[eid] = val
        except json.JSONDecodeError:
            log.warning("LLM batch %d/%d returned invalid JSON", i // batch_size + 1,
                        (len(ambiguous) + batch_size - 1) // batch_size)

    return results


async def run(args):
    with open(args.vision_json) as f:
        data = json.load(f)
    vision = PatientTimelineVision.from_dict(data)

    med_events = [
        (eid, ev) for eid, ev in vision.events.items()
        if ev.event_type == "medication"
    ]
    print(f"Medication events: {len(med_events)}")

    # Phase 1: Extract drug candidates — prefer annotation, fall back to regex
    extractions: List[Dict[str, Any]] = []
    no_candidate = 0
    from_annotation = 0
    from_regex = 0
    already_normalized = 0
    for eid, ev in med_events:
        # Skip events that already have an rxcui
        if ev.annotations.get("rxcui"):
            already_normalized += 1
            continue

        # Prefer drug_name from LLM extraction annotation
        anno_drug = ev.annotations.get("drug_name", "").strip()
        if anno_drug:
            extractions.append({
                "event_id": eid,
                "extracted_name": anno_drug,
                "all_candidates": [anno_drug],
                "preview": ev.preview,
                "source": "annotation",
            })
            from_annotation += 1
            continue

        # Fall back to regex extraction
        candidates = extract_drug_candidates(ev.preview)
        if candidates:
            extractions.append({
                "event_id": eid,
                "extracted_name": candidates[0],
                "all_candidates": candidates,
                "preview": ev.preview,
                "source": "regex",
            })
            from_regex += 1
        else:
            no_candidate += 1

    print(f"Extracted drug name: {len(extractions)}/{len(med_events)} ({100*len(extractions)/len(med_events):.0f}%)")
    print(f"  From annotation (LLM):  {from_annotation}")
    print(f"  From regex (fallback):   {from_regex}")
    print(f"  Already normalized:      {already_normalized}")
    print(f"  No candidate found:      {no_candidate}")

    if not args.db_url:
        print("\nNo --db-url provided. Showing extraction results only (no RxNorm lookup).")
        for ext in extractions[:20]:
            print(f"  {ext['event_id']:24s} | {ext['extracted_name']:30s} | {ext['preview'][:60]}")
        _save_extractions(args, vision, extractions, {})
        return

    # Phase 1b: RxNorm trigram lookup
    import asyncpg
    pool = await asyncpg.create_pool(args.db_url, min_size=1, max_size=4)

    high_confidence = []
    ambiguous = []
    no_match = []

    for ext in extractions:
        matches = await lookup_rxnorm_trgm(pool, ext["extracted_name"])
        ext["candidates"] = matches
        if matches and matches[0]["sim"] >= 0.6:
            high_confidence.append(ext)
        elif matches:
            ambiguous.append(ext)
        else:
            no_match.append(ext)

    await pool.close()

    print(f"\nRxNorm lookup results:")
    print(f"  High confidence (sim >= 0.6): {len(high_confidence)}")
    print(f"  Ambiguous (sim < 0.6):        {len(ambiguous)}")
    print(f"  No match:                     {len(no_match)}")

    # Apply high-confidence matches directly
    applied: Dict[str, Dict[str, str]] = {}
    for ext in high_confidence:
        best = ext["candidates"][0]
        applied[ext["event_id"]] = {
            "drug_name": best["str"],
            "rxcui": best["rxcui"],
            "source": "rxnorm_trgm",
            "confidence": f"sim={best['sim']:.2f}",
        }

    # Phase 2: LLM judgement on ambiguous matches
    if args.llm and ambiguous:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("\nOPENAI_API_KEY not set — skipping LLM judgement.")
        else:
            from openai import AsyncOpenAI
            client = AsyncOpenAI()
            print(f"\nRunning GPT-4.1 judgement on {len(ambiguous)} ambiguous matches...")
            llm_results = await batch_llm_judge(client, ambiguous)
            for eid, val in llm_results.items():
                applied[eid] = {
                    "drug_name": val["drug_name"],
                    "rxcui": val["rxcui"],
                    "source": "rxnorm_trgm+llm_judge",
                    "confidence": "llm_confirmed",
                }
            print(f"  LLM confirmed: {len(llm_results)}")

    _save_extractions(args, vision, extractions, applied)


def _save_extractions(args, vision, extractions, applied):
    """Apply normalizations to vision and save."""
    for eid, norm in applied.items():
        if eid in vision.events:
            ev = vision.events[eid]
            ev.annotations["drug_name"] = norm["drug_name"]
            ev.annotations["rxcui"] = norm.get("rxcui", "")
            ev.annotations["drug_norm_source"] = norm.get("source", "")

    total_meds = sum(1 for ev in vision.events.values() if ev.event_type == "medication")
    with_drug = sum(1 for ev in vision.events.values()
                    if ev.event_type == "medication" and ev.annotations.get("drug_name"))

    print(f"\nFinal: {with_drug}/{total_meds} medication events have drug_name ({100*with_drug/total_meds:.0f}%)")

    out_path = str(args.vision_json).replace(".json", "_rxnorm.json")
    vision.save(out_path, force=True)
    print(f"Saved: {out_path}")

    manifest = {
        "total_medication_events": total_meds,
        "extracted_from_preview": len(extractions),
        "normalized_to_rxnorm": len(applied),
        "applied": {eid: v for eid, v in list(applied.items())[:50]},
    }
    manifest_path = out_path.replace(".json", "_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest: {manifest_path}")


def main():
    parser = argparse.ArgumentParser(description="Normalize medications against RxNorm")
    parser.add_argument("vision_json", type=Path)
    parser.add_argument("--db-url", default=os.getenv("SYNC_DATABASE_URL",
                        "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd"))
    parser.add_argument("--llm", action="store_true", help="Use GPT-4.1 for ambiguous matches")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if not args.vision_json.exists():
        print(f"Not found: {args.vision_json}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
