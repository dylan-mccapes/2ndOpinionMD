"""Quick structural inspection of the scrubbed PTV graph for PDF authoring."""
import json
from collections import Counter
from pathlib import Path

SRC = Path("artifacts/ptv_46860f06-e0a5-42d4-af9f-4dd8caa666f0_full_20260422T143255Z_scrubbed_pretty.json")

with SRC.open("r", encoding="utf-8") as fh:
    d = json.load(fh)

print("top-level keys:", list(d.keys()))
print("patient_id:", d["patient_id"])
print("built_at:", d["built_at"])
print("session_only:", d["session_only"])
print("last_pdf_ingest:", d["metadata"].get("last_pdf_ingest"))
print("pro.forward:", d["metadata"].get("pro", {}).get("forward"))
print()
print(f"counts: arcs={len(d['arcs'])} events={len(d['events'])}")

etypes = Counter(e.get("event_type") for e in d["events"].values())
print("event_type dist:", dict(etypes))

afam = Counter()
for aid in d["arcs"]:
    if aid.startswith("arc_icd_"):
        afam["icd"] += 1
    elif aid.startswith("arc_drug_"):
        afam["drug"] += 1
    elif aid.startswith("arc_lab_"):
        afam["lab"] += 1
    elif aid.startswith("arc_proc_"):
        afam["proc"] += 1
    elif aid.startswith("arc_sym_"):
        afam["sym"] += 1
    else:
        afam["other"] += 1
print("arc family:", dict(afam))

print()
print("sample arcs (first 10):")
for aid, a in list(d["arcs"].items())[:10]:
    name = a.get("name", "")
    nev = len(a.get("event_ids", []))
    status = a.get("status")
    dr = a.get("date_range")
    print(f"  {aid:30s}  name={name!r:45s}  events={nev:3d}  status={status}  dates={dr}")

# arcs by event count
arcs_by_count = sorted(d["arcs"].items(), key=lambda kv: -len(kv[1].get("event_ids", [])))
print()
print("top-10 arcs by event count:")
for aid, a in arcs_by_count[:10]:
    print(f"  {aid:30s}  name={a.get('name','')!r:45s}  events={len(a.get('event_ids',[]))}")

astatus = Counter(a.get("status") for a in d["arcs"].values())
print()
print("arc status dist:", dict(astatus))

ek = d["metadata"].get("entity_keys", {})
print()
print(f"entity_keys total: {len(ek)}")
ek_kind = Counter(v.get("kind") for v in ek.values())
print("entity_keys by kind:", dict(ek_kind))

# samples per kind
print()
print("entity_keys samples:")
for kind in ek_kind:
    samples = [k for k, v in ek.items() if v.get("kind") == kind][:3]
    print(f"  {kind}: {samples}")

# top salience events
print()
top = sorted(
    d["events"].values(),
    key=lambda e: (e.get("annotations", {}).get("salience") or 0),
    reverse=True,
)[:10]
print("top-10 salience events:")
for e in top:
    s = e.get("annotations", {}).get("salience")
    t = e.get("event_type")
    p = (e.get("preview") or "")[:90].replace("\n", " ")
    print(f"  s={s}  type={t:15s}  preview={p!r}")

# connascence density
conn_counts = Counter()
for e in d["events"].values():
    conn = e.get("connascence", {}) or {}
    for kind, lst in conn.items():
        if isinstance(lst, list):
            conn_counts[kind] += len(lst)
print()
print("connascence edges total per kind:", dict(conn_counts))

# arcs with populated summary
pop = [a for a in d["arcs"].values() if a.get("summary")]
print()
print(f"arcs with non-empty summary: {len(pop)}")
pop_oq = [a for a in d["arcs"].values() if a.get("open_questions")]
print(f"arcs with open_questions: {len(pop_oq)}")
pop_ce = [a for a in d["arcs"].values() if a.get("cross_arc_edges")]
print(f"arcs with cross_arc_edges: {len(pop_ce)}")

# status_flags distribution across events
sf = Counter()
for e in d["events"].values():
    for f in (e.get("annotations", {}).get("status_flags") or []):
        sf[f] += 1
print()
print("status_flags dist:", dict(sf))

# chapter kinds
ck = Counter()
for e in d["events"].values():
    ck[e.get("annotations", {}).get("chapter_kind")] += 1
print("chapter_kind dist:", dict(ck))

# date coverage
dts = [e.get("timestamp") for e in d["events"].values() if e.get("timestamp") and e.get("timestamp") != "unknown"]
print()
print(f"events with real timestamp: {len(dts)} / {len(d['events'])}")
if dts:
    print(f"date range: {min(dts)} .. {max(dts)}")

# in_workup_for / caused_by connascence
iw = cb = 0
for e in d["events"].values():
    c = e.get("connascence", {}) or {}
    iw += len(c.get("in_workup_for", []) or [])
    cb += len(c.get("caused_by", []) or [])
print()
print(f"connascence in_workup_for edges: {iw}")
print(f"connascence caused_by edges: {cb}")
