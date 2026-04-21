#!/usr/bin/env python3
"""End-to-end smoke test for the new graph_finalize passes.

Loads the existing pretty-printed PTV artifact, runs
``finalize_graph`` on it, and reports what changed.

Usage:
    python3 scripts/_smoke_graph_finalize.py [path_to_ptv.json]
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Keep the smoke test lightweight: stub out server.utils.parse_date so we
# don't pull in heavy pipeline deps just to load a JSON graph.
import types, datetime, re  # noqa: E402

stub_root = types.ModuleType("server")
stub_utils = types.ModuleType("server.utils")
stub_pd = types.ModuleType("server.utils.parse_date")

def parse_clinical_date(raw):
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s.lower() in ("unknown", "n/a"):
        return None
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=datetime.timezone.utc)
        except ValueError:
            return None
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", s)
    if m:
        mo, da, yr = (int(g) for g in m.groups())
        if yr < 100:
            yr += 2000 if yr < 50 else 1900
        try:
            return datetime.datetime(yr, mo, da, tzinfo=datetime.timezone.utc)
        except ValueError:
            return None
    return None

def extract_date_from_text(_):
    return None

stub_pd.parse_clinical_date = parse_clinical_date
stub_pd.extract_date_from_text = extract_date_from_text
sys.modules["server"] = stub_root
sys.modules["server.utils"] = stub_utils
sys.modules["server.utils.parse_date"] = stub_pd
stub_root.utils = stub_utils
stub_utils.parse_date = stub_pd

# Now register stubbed submodules we don't want to side-effect-import.
stub_eoh = types.ModuleType("server.eoh")
sys.modules["server.eoh"] = stub_eoh
stub_root.eoh = stub_eoh

# Load patient_timeline_vision directly from file to avoid pydantic chain.
ptv_spec = importlib.util.spec_from_file_location(
    "server.eoh.patient_timeline_vision",
    ROOT / "server" / "eoh" / "patient_timeline_vision.py",
)
ptv_mod = importlib.util.module_from_spec(ptv_spec)
sys.modules["server.eoh.patient_timeline_vision"] = ptv_mod
ptv_spec.loader.exec_module(ptv_mod)
stub_eoh.patient_timeline_vision = ptv_mod

# Same for graph_finalize.
gf_spec = importlib.util.spec_from_file_location(
    "server.eoh.graph_finalize",
    ROOT / "server" / "eoh" / "graph_finalize.py",
)
gf_mod = importlib.util.module_from_spec(gf_spec)
sys.modules["server.eoh.graph_finalize"] = gf_mod
gf_spec.loader.exec_module(gf_mod)

# And registry_export.
rx_spec = importlib.util.spec_from_file_location(
    "server.eoh.registry_export",
    ROOT / "server" / "eoh" / "registry_export.py",
)
rx_mod = importlib.util.module_from_spec(rx_spec)
sys.modules["server.eoh.registry_export"] = rx_mod
rx_spec.loader.exec_module(rx_mod)

# ---------------------------------------------------------------------------
path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "artifacts" / "ptv_428b017a-3840-490c-8a95-65c4d6cfe10d.json"
print(f"Loading graph from {path}")
data = json.loads(path.read_text(encoding="utf-8"))
vision = ptv_mod.PatientTimelineVision.from_dict(data)
print(f"  events_before = {len(vision.events)}")
print(f"  arcs_before   = {len(vision.arcs)}")
print(f"  edges_before  = {vision.count_edges()}")

stats = gf_mod.finalize_graph(vision, chapters=None, pages_text={})

print("\n=== finalize stats ===")
print(json.dumps(stats, indent=2, ensure_ascii=False)[:4000])

print(f"\n  events_after  = {len(vision.events)}")
print(f"  arcs_after    = {len(vision.arcs)}")
print(f"  edges_after   = {vision.count_edges()}")
print(f"  metadata keys = {sorted(vision.metadata.keys())}")

# Sanity checks on what was added.
print("\n--- entities sample ---")
entities = vision.metadata.get("entities") or {}
for key in sorted(entities.keys())[:6]:
    print(f"  {key}  -> {len(entities[key]['event_ids'])} events")
print(f"  ... ({len(entities)} total)")

print("\n--- arc sample ---")
for aid in list(vision.arcs.keys())[:6]:
    a = vision.arcs[aid]
    print(f"  {aid:<48} {len(a.event_ids):>4} events   {a.date_range[0]} — {a.date_range[1]}")
print(f"  ... ({len(vision.arcs)} total)")

print("\n--- event card sample ---")
seen = 0
for eid, ev in vision.events.items():
    card = (ev.annotations or {}).get("card")
    if card and card.get("title"):
        print(f"  [{card['type']:<12} sal={card.get('salience'):<5}] {card['ts']}  {card['title']}")
        seen += 1
    if seen >= 5:
        break

print("\n--- index ---")
idx = vision.metadata.get("index") or {}
for k in ["by_year", "by_icd", "by_icd_family", "by_drug", "by_chapter", "by_arc"]:
    print(f"  {k:<15} keys={len(idx.get(k) or {})}")
print(f"  top_salience_event_ids[0..4] = {(idx.get('top_salience_event_ids') or [])[:5]}")

# Run the registry export too.
print("\n=== registry export ===")
bundle = rx_mod.export_fhir_bundle(vision, redact=True, include_administrative=False)
types_counter = {}
for e in bundle["entry"]:
    t = e["resource"]["resourceType"]
    types_counter[t] = types_counter.get(t, 0) + 1
print(f"  total resources   = {bundle['total']}")
for k in sorted(types_counter):
    print(f"    {k:<24} {types_counter[k]}")

series = rx_mod.export_derived_series(vision)
print("\n--- derived series shape ---")
print(f"  labs      entries: {sum(len(v) for v in series['labs'].values())}  distinct labs: {len(series['labs'])}")
print(f"  meds      entries: {sum(len(v) for v in series['meds'].values())}  distinct meds: {len(series['meds'])}")
print(f"  pros      entries: {sum(len(v) for v in series['pros'].values())}  distinct instruments: {len(series['pros'])}")
print(f"  diagnoses entries: {sum(len(v) for v in series['diagnoses'].values())}  distinct families: {len(series['diagnoses'])}")

# Idempotence check: run finalize a second time.
print("\n--- idempotence ---")
stats2 = gf_mod.finalize_graph(vision, chapters=None, pages_text={})
print(f"  canonical_ids stamped on 2nd pass = {stats2['canonical_ids']}  (expect 0 from new work)")
print(f"  arcs_created   on 2nd pass        = {stats2['arcs']['arcs_created']}  (expect 0)")
print(f"  cards_built    on 2nd pass        = {stats2['cards']['cards_built']}  (rebuilt each time — ok)")

# Write the enriched graph next to the source for inspection.
out_path = path.with_suffix(".finalized.json")
out_path.write_text(json.dumps(vision.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nwrote enriched graph to {out_path} ({out_path.stat().st_size // 1024} KB)")

# FHIR bundle dump
fhir_path = path.with_suffix(".fhir.json")
fhir_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"wrote FHIR bundle to    {fhir_path} ({fhir_path.stat().st_size // 1024} KB)")

# Series dump
series_path = path.with_suffix(".series.json")
series_path.write_text(json.dumps(series, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"wrote derived series to {series_path} ({series_path.stat().st_size // 1024} KB)")

print("\nOK")
