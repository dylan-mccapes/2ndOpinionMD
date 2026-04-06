#!/usr/bin/env python3
"""
Retroactively apply heuristic pre-extraction to an existing PTV graph.

Does two things:
1. Recovers timestamps on clinical events using heuristic page dates
2. Adds heuristic events (ICD diagnoses, medications, labs) that
   the LLM missed entirely

Does NOT require Ollama or any LLM. Just the PDF and the existing PTV JSON.

Usage:
    python scripts/apply_heuristic_to_existing_ptv.py \
        ../artifacts/timeline_ollama_20260330_1312/patient_timeline_vision_norman_eric_roberts_20260330_151754.json \
        ../data/patient_timelines/NormanEricRoberts_decrypted.pdf \
        -o ../artifacts/timeline_ollama_20260330_1312/ptv_heuristic_enriched.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

script_dir = Path(__file__).resolve().parent
server_dir = script_dir.parent
parent_of_server = server_dir.parent

if str(parent_of_server) not in sys.path:
    sys.path.insert(0, str(parent_of_server))
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

from pypdf import PdfReader
from server.eoh.heuristic_page_extract import heuristic_extract_batch
from server.utils.parse_date import extract_date_from_text


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply heuristic enrichment to existing PTV")
    parser.add_argument("ptv_json", type=Path, help="Path to existing PTV JSON")
    parser.add_argument("pdf_path", type=Path, help="Path to decrypted PDF")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output enriched PTV JSON")
    args = parser.parse_args()

    print(f"Loading PTV: {args.ptv_json}")
    with open(args.ptv_json) as f:
        data = json.load(f)

    events = data["events"]
    total = len(events)
    clinical_keys = [k for k, v in events.items() if v["event_type"] not in ("page",)]
    unknown_keys = [k for k in clinical_keys if events[k]["timestamp"].lower() in ("unknown", "")]
    print(f"  {total} total events, {len(clinical_keys)} clinical, {len(unknown_keys)} unknown timestamps")

    print(f"Reading PDF: {args.pdf_path}")
    reader = PdfReader(str(args.pdf_path))
    pages = []
    for idx, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip().replace("\x00", "")
        if text:
            pages.append((idx + 1, text))
    print(f"  {len(pages)} non-empty pages")

    print("Running heuristic extraction...")
    t0 = time.perf_counter()
    heur = heuristic_extract_batch(pages)
    elapsed = time.perf_counter() - t0
    print(f"  {elapsed*1000:.0f}ms ({elapsed/len(pages)*1000:.2f}ms/page)")

    page_dates = {pn: r.page_date for pn, r in heur.items() if r.page_date}
    print(f"  {len(page_dates)}/{len(pages)} pages have encounter dates")

    # Phase 1: Timestamp recovery on existing events
    ts_recovered = 0
    ts_from_preview = 0
    ts_from_page = 0

    for eid in unknown_keys:
        ev = events[eid]
        preview_date = extract_date_from_text(ev.get("preview", ""))
        if preview_date:
            ev["timestamp"] = preview_date.strftime("%Y-%m-%d")
            ev.setdefault("annotations", {})["timestamp_source"] = "heuristic_preview"
            ts_recovered += 1
            ts_from_preview += 1
            continue

        parts = eid.split("_")
        if len(parts) >= 2 and parts[0] == "pdf":
            page_str = parts[1].lstrip("p").lstrip("0") or "0"
            try:
                pg = int(page_str)
                if pg in page_dates:
                    ev["timestamp"] = page_dates[pg]
                    ev.setdefault("annotations", {})["timestamp_source"] = "heuristic_page_date"
                    ts_recovered += 1
                    ts_from_page += 1
            except ValueError:
                pass

    print(f"\nTimestamp recovery: {ts_recovered}/{len(unknown_keys)} recovered")
    print(f"  From preview text: {ts_from_preview}")
    print(f"  From page date: {ts_from_page}")
    new_unknown = len(unknown_keys) - ts_recovered
    new_pct = (len(clinical_keys) - new_unknown) / len(clinical_keys) * 100
    print(f"  Timestamp coverage: {new_pct:.1f}% (was {(len(clinical_keys)-len(unknown_keys))/len(clinical_keys)*100:.1f}%)")

    # Phase 2: Add heuristic events the LLM missed
    existing_previews = {ev.get("preview", "")[:40].lower() for ev in events.values()}
    heur_added = 0

    for pn, hr in sorted(heur.items()):
        for he in hr.events:
            preview_key = he.preview[:40].lower()
            if preview_key in existing_previews:
                continue
            existing_previews.add(preview_key)

            event_id = f"pdf_p{pn:04d}_heur_{heur_added:04d}"
            ev_dict = {
                "event_id": event_id,
                "event_type": he.event_type,
                "timestamp": he.timestamp,
                "preview": he.preview[:80],
                "source_page": pn,
                "annotations": {"heuristic_source": he.source},
                "connascence": [],
            }
            if he.drug_name:
                ev_dict["annotations"]["drug_name"] = he.drug_name
                ev_dict["drug_name"] = he.drug_name
            if he.drug_dosage:
                ev_dict["annotations"]["drug_dosage"] = he.drug_dosage
                ev_dict["drug_dosage"] = he.drug_dosage
            if he.drug_route:
                ev_dict["annotations"]["drug_route"] = he.drug_route
                ev_dict["drug_route"] = he.drug_route
            if he.icd_code:
                ev_dict["annotations"]["icd_code"] = he.icd_code

            events[event_id] = ev_dict
            heur_added += 1

    print(f"\nHeuristic events added: {heur_added}")
    print(f"Total events: {len(events)} (was {total})")

    # Phase 3: Deduplication pass
    from collections import defaultdict
    hash_groups: dict[str, list[str]] = defaultdict(list)
    for eid, ev in events.items():
        if ev["event_type"] == "page":
            continue
        preview_80 = ev.get("preview", "")[:80].strip().lower()
        drug = ev.get("drug_name", "")
        ts = ev.get("timestamp", "")
        h = f"{preview_80}|{drug}|{ts}"
        hash_groups[h].append(eid)

    dup_groups = {h: eids for h, eids in hash_groups.items() if len(eids) > 1}
    removed = 0
    for h, eids in dup_groups.items():
        survivor = max(eids, key=lambda e: len(events[e].get("connascence", [])))
        for eid in eids:
            if eid != survivor:
                del events[eid]
                removed += 1

    print(f"Deduplication: removed {removed} duplicate events")
    print(f"Final event count: {len(events)}")

    # Save
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nSaved: {args.output}")


if __name__ == "__main__":
    main()
