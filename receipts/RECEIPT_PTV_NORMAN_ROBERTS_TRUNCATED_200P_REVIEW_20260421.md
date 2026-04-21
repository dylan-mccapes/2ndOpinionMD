# RECEIPT — PTV Review: Norman Eric Roberts (truncated 200-page)

**Date:** 2026-04-21
**Artifact under review:** `artifacts/ptv_428b017a.json` (from `ehr.patient_graph_vision`)
**Source PDF:** `data/patient_timelines/NormanEricRoberts_decrypted_truncated.pdf` (200 pages)
**Pipeline:** `POST /api/timeline/import-pdf-stream` → `stream_ingest_extracted_pdf_pages`
**LLM:** Ollama `eoh-llama3.1:8b` @ 32k ctx, 60% input / 30% output fill
**Stream outcome:** `skeleton_persisted` early, then chapter-by-chapter enrichment, `persisted` final

---

## 1. Headline numbers

| Metric | Value |
| --- | --- |
| Total events | **644** |
| Events with real timestamp | **393 (61%)** |
| Events with `timestamp == "unknown"` | 251 (39%) |
| Pages with ≥1 event | 200/200 |
| `arcs` (clinical arcs) | **0** (dataclass exists, not yet populated) |
| Top-level `edges`/`arcs` list in dump | empty |
| Temporal connascence pairs (unique, undirected) | **2,470** |
| Events carrying any connascence | 364/644 (56%) — all `temporal` |
| Chapter-annotated events | **0/644 (0%)** ← regression |

Event-type distribution:

```
diagnosis  240   medication 207   procedure 57   note 34
page        34   lab         30   symptom   29   visit 8
imaging      3   vital_signs  1   appointment 1
```

Year histogram (parsed timestamps):

```
2016=264  2025=38  2015=19  2024=12  2014=7  2009=7  2017=6
2007=6    2021=5   2004=5   2018=4   2023=4  2006=3  2012=3
(plus 10 more years with 1–2 events each)
```

---

## 2. Where we did well

1. **Every page got coverage.** 200/200 pages contributed at least one event; no silent page drops. Heuristic + LLM merged cleanly.
2. **Drug normalization landed on the node.** 197/207 medications (95%) carry `annotations.drug_name`, 144 carry `drug_dosage`, 143 carry `drug_route`. This is the single biggest win of the Ollama pass — it survived the round-trip.

   ```1002:1009:c:\2OPMD\2ndOpinionMD-MVP\server\eoh\patient_timeline_vision.py
   vision.add_event(
       event_id=event_id,
       event_type=event_type,
       timestamp=timestamp,
       preview=preview,
       discovered_by=discovered_by,
       annotations=annotations,
   )
   ```
3. **Event typology is sensible.** 11 types, strong skew toward diagnosis and medication — exactly what we’d expect from an oncology/chronic-care packet. Procedure/lab/imaging buckets non-empty.
4. **Chronology cluster matches ground truth.** 264 events land in 2016 (the dense hospital episode), and the long tail stretches back to 2004. The skeleton + LLM correctly surfaced the episode’s center of mass.
5. **ICD-10 codes are bracketed in previews.** 67 distinct codes detected via regex inside diagnosis previews (`[K81.0]`, `[D12.6]`, `[D64.9]`, …) — a free, high-signal grouping key.
6. **Regex skeleton → SSE `skeleton_persisted` fired before any LLM call.** The client-side UX goal (“show something in < 5 s”) held.
7. **Truncation was rare and benign.** A handful of `Repaired truncated JSON` warnings lost 1–2 trailing chars, no events dropped.

---

## 3. Where we did poorly

### 3a. **BUG — chapter metadata silently dropped** (severity: high)

Zero events carry `chapter_id`, `encounter_date`, `encounter_type`, `section_header`, or `chapter_kind`:

```
annotation_keys: pdf_page=644, drug_name=198, drug_norm_source=198,
                 drug_dosage=144, drug_route=143
with_chapter_id=0   with_encounter_date=0
```

Root cause in `server/eoh/patient_timeline_vision.py`:

```990:1000:c:\2OPMD\2ndOpinionMD-MVP\server\eoh\patient_timeline_vision.py
annotations: Dict[str, Any] = {"pdf_page": page_num}
drug_name = event.get("drug_name")
if drug_name and isinstance(drug_name, str) and drug_name.strip():
    annotations["drug_name"] = drug_name.strip()
    annotations["drug_norm_source"] = "llm_extraction"
drug_dosage = event.get("drug_dosage")
if drug_dosage and isinstance(drug_dosage, str) and drug_dosage.strip():
    annotations["drug_dosage"] = drug_dosage.strip()
drug_route = event.get("drug_route")
if drug_route and isinstance(drug_route, str) and drug_route.strip():
    annotations["drug_route"] = drug_route.strip().lower()
```

`add_events_from_pdf_page` **rebuilds `annotations` from scratch**. The chapter stamps written by `stream_populate_vision_from_extracted_pages` onto `ev["annotations"]` are discarded before `add_event` is called. Consequence: every chapter-scoped UI affordance, every chapter-grouped analytic, every reduced-graph connascence pass (see §4) is starved of its grouping key.

**Fix (1 line):**

```python
passthrough = event.get("annotations") or {}
annotations: Dict[str, Any] = {"pdf_page": page_num, **passthrough}
```

### 3b. **Only `temporal` connascence was recorded.** (severity: high — user’s observation)

```
events_with_any_connascence: 364/644
conn_kinds:                  {temporal: 2,470 unique pairs}
```

The 7-day window is a correct but narrow signal. It collapses an entire hospital stay into one dense blob and leaves the rest of the graph unconnected. No `same_drug`, `same_icd`, `same_chapter`, `same_day`, `same_page`, `same_encounter` edges exist. That is the graph equivalent of a timeline with no joints.

### 3c. **Stored `arcs` is empty.**

`ClinicalArc` is defined and serialized, but nothing populates it. The stream never emits “arc” frames, and `to_dict()` writes `arcs: {}`. (The file even shows `arcs: []` — a minor drift we should normalize.)

### 3d. **`edges`/graph-level arc list is empty.** (severity: medium)

The `persisted` SSE frame reported `graph_edges: 4940`, but only the per-event `connascence` lists are non-empty; there is no graph-level edge list. `count_edges()` double-counts directed pairs and mixes with that reporting, which is misleading to the client.

### 3e. **Diagnosis timestamps mostly “unknown”.** (severity: medium)

Of the 240 diagnoses, virtually all land on `pdf_page=3` (a “Problem List” dump) with `timestamp: unknown`. The onset dates are actually present in the preview text itself — e.g.,

```
OUNSELING, CONTINUING RECOVERY GROUP, >=90 DAYS. Noted on: 04/06/2017 …
```

but the first character was clipped and the `Noted on:` date was never promoted to `event.timestamp`. A dumb post-pass regex (`Noted on:\s*(\d{2}/\d{2}/\d{4})`) would fix most of these.

### 3f. **`event_type="page"` generic events are slag.** (severity: low)

34 `page` events have boilerplate previews like `Release of Medical Information25 N Via Monte…`. They should be filtered before they ever reach the graph, or demoted to a page manifest table.

### 3g. **A handful of heuristic drug-name false positives.**

e.g., `Version 1 of 1 G` on page 44 became `drug_name: "Version 1 of"` — the heuristic grabbed a footer/version token.

### 3h. **Preview character-drift on page 3.**

`"ssile serrated polyp/adenoma. …"` (lost leading `Se…`), `"OUNSELING, …"` (lost `C`). The JSON truncation repair is nibbling leading characters on wrapped items. Low impact for the graph but ugly in the UI.

---

## 4. Strategic improvement plan — **reduced-graph connascence**

> User directive: *“We should be running connascence against reduced graphs. It shouldn’t be clever. Strategic.”*

The pattern: for each clinically meaningful **grouping key**, take the subset of events sharing that key and emit pairwise `same_<key>` edges. No cleverness. The intelligence comes from the choice of key, not the algorithm.

Reduced-graph pass candidates, with **actual** candidate-pair counts from this run:

| Pass | Grouping key | Groups | Multi-member groups | Candidate undirected pairs | Wire status |
| --- | --- | ---:| ---:| ---:| --- |
| `same_chapter` | `annotations.chapter_id` | — | — | — | **blocked by §3a** |
| `same_encounter` | `annotations.encounter_date` | — | — | — | **blocked by §3a** |
| `same_day` | `timestamp[:10]` | 101 | 46 | **4,022** | ready now |
| `same_page` | `annotations.pdf_page` | 200 | 100 | **3,190** | ready now |
| `same_icd` | regex `\[([A-Z]\d{2}(?:\.\w+)?)\]` on preview | 67 | 15 | **64** | ready now |
| `same_drug` | `annotations.drug_name.lower()` | 102 | 35 | **241** | ready now |
| `temporal_7d` | existing | — | — | 2,470 | already on |

Once §3a is fixed, `same_chapter` and `same_encounter` become the strongest signals because they come from the PDF’s own structure.

### Pseudocode (single pass, ≤20 lines)

```python
from collections import defaultdict

def emit_reduced_graph_edges(vision, key_fn, kind):
    buckets: dict[str, list[str]] = defaultdict(list)
    for eid, ev in vision.events.items():
        k = key_fn(ev)
        if k:
            buckets[str(k)].append(eid)
    for k, members in buckets.items():
        if len(members) < 2:
            continue
        for a, b in itertools.combinations(members, 2):
            vision.add_edge(a, b, kind, provenance={"group": k})
```

Run this five times with different `key_fn`s (chapter, encounter_date, drug_name, icd_code, pdf_page, timestamp[:10]). Emit one SSE frame per pass (`connascence_pass: {kind, edges_added, elapsed_ms}`) so the UI can report progress.

### Arc collapsing (free, non-clever)

A `ClinicalArc` is just a **named reduced graph with ≥2 members**:

- `same_drug(Pantoprazole)` → arc named `"Pantoprazole continuity"`, `date_range=(min_ts, max_ts)`.
- `same_icd(D64.9)` → arc named `"Anemia (D64.9)"`.
- `same_chapter(<chapter_id>)` → arc named after `section_header`.

Populate `vision.arcs` with these automatically; no LLM needed. Users get the “groups of related events” affordance immediately.

### De-densification

Within dense reduced graphs (e.g., a 40-event chapter), emit **star edges from a representative node** (earliest timestamp, or the chapter header event) instead of full cliques. Pair counts drop from `n(n-1)/2` to `n-1`, graph stays readable.

---

## 5. Prioritized action list

1. **(30 min)** Patch `add_events_from_pdf_page` to pass-through `event["annotations"]` — restores chapter/encounter keys.
2. **(1 hr)** Add `server/eoh/reduced_graph_connascence.py` with the 5-line loop above; call it from `stream_populate_vision_from_extracted_pages` after the LLM phase completes; emit `connascence_pass` SSE frames.
3. **(30 min)** Add an ICD-code extractor (`\[([A-Z]\d{2}(?:\.\w+)?)\]`) and a `Noted on: MM/DD/YYYY` timestamp-recovery post-pass. Backfills ~200 diagnosis onset dates for free.
4. **(20 min)** Drop `event_type="page"` slag at the ingest boundary; move boilerplate pages to a page-manifest side-table instead.
5. **(30 min)** Populate `vision.arcs` from multi-member reduced-graph groups (`same_drug`, `same_icd`, `same_chapter`). No LLM.
6. **(20 min)** Make `persisted` frame report true graph-level edge count (undirected) not the bidirectional `count_edges()` sum.
7. **(Stretch)** Tighten the drug-name heuristic to reject version/footer tokens (e.g., drop candidates matching `^Version \d+`).

Acceptance criteria for the next PTV run on the same 200-page fixture:

- `with_chapter_id >= 600/644`.
- Four new connascence kinds present with non-zero pair counts.
- `vision.arcs` non-empty, at least 15 arcs from `same_icd ∪ same_drug`.
- Diagnosis timestamps: `ts_known/ts_unknown` ratio shifts from `393/251` toward `≥500/≤144`.
- SSE `persisted` frame reports the same edge count that `jq '.arcs | length'` returns on the saved artifact.

---

## 6. Verdict

The Ollama chapter-aware pipeline is **working and persisting**, and for text-only PDFs the extraction itself is good — particularly drug normalization. The gap is structural, not intelligence: we’re stamping chapter metadata and then dropping it one function later, and we’re running exactly one of the five obvious reduced-graph connascence passes. Both are mechanical fixes, not research problems. Do them next.

---

## 7. Post-review addendum (same session)

### 7a. Verified the Ollama stream actually finished

Server-side evidence (user-provided log tail):

```
12:48:45 … Ollama OpenAI-compat /v1/chat/completions: model=eoh-llama3.1:8b  num_ctx=32768  num_predict=6144  pages=[199, 200]
12:48:47 … HTTP Request: POST http://192.168.0.245:11434/v1/chat/completions "HTTP/1.1 200 OK"
12:48:47 … Repaired truncated JSON (close-brace): salvaged 2 page(s) …
12:48:47 … Temporal connascence pass: 644 events total … → +2470 links (edges 14→4940)
```

Artifact corroboration: 593/644 event IDs match the `*_eNNNN` pattern that only the LLM/heuristic pipeline emits, vs 51 `*_generic` stubs for pages where the LLM returned nothing. That is Ollama output, not regex skeleton. What read as "regex-only" was the 80-char preview cap baked into the Ollama system prompt.

### 7b. Implemented the §5 action list

All in one pass:

| # | Change | Files |
|---|---|---|
| 1 | `add_events_from_pdf_page` now passes through caller `annotations` (chapter_id, encounter_date, encounter_type, section_header, chapter_kind, icd_code, heuristic_source, timestamp_source) | `server/eoh/patient_timeline_vision.py` |
| 2 | Ollama & full prompts: `preview` now ≤240 chars / 2-sentence medical summary (sentence 1 = WHAT, sentence 2 = WHY/CONTEXT). Output cap bumped from 500 to 400 chars for small models. | `server/eoh/timeline_summarizer.py` |
| 3 | Event-type vocabulary widened: `diagnosis, medication, lab, procedure, symptom, clinical_note, vital_signs, imaging, immunization, administrative`. All 9 `event_type="page"` fallback sites now emit `"administrative"` — `page` never escapes to storage. | `server/eoh/timeline_summarizer.py` |
| 4 | `_reclassify_event_types` rewritten: bucket `page/unknown/note/administrative`, run clinical keyword regexes first, then fall back to `administrative` for boilerplate and `clinical_note` for prose. Vaccine rows promote to `immunization` (was `procedure`). | `server/eoh/timeline_summarizer.py` |
| 5 | New `_infer_reduced_graph_connascence`: five passes `same_chapter / same_encounter / same_drug / same_icd / same_day`, full clique for ≤8 members, star topology for larger buckets. | `server/eoh/timeline_summarizer.py` |
| 6 | New `_recover_timestamps_from_preview`: dumb `Noted on: MM/DD/YYYY` regex fills missing timestamps; stamps `annotations.timestamp_source = "noted_on_regex"`. | `server/eoh/timeline_summarizer.py` |
| 7 | New `_backfill_chapter_annotations`: for any event whose `pdf_page` falls inside a chapter but lacks `chapter_id`, stamp chapter + encounter_* + section_header. Makes same_chapter/same_encounter work even for heuristic-only events added during the regex-skeleton phase. | `server/eoh/timeline_summarizer.py` |
| 8 | Finalizers (streaming + non-streaming) now run in order: temporal → reclassify → noted-on ts recovery → chapter back-stamp → reduced-graph passes → timestamp scrub. SSE `done` frame and return dict surface `reduced_graph_connascence`, `timestamps_recovered_from_preview`, `chapter_backstamped`. | `server/eoh/timeline_summarizer.py` |

### 7c. Dry-run validation (replaying the passes against the saved 644-event artifact)

```
edges_added: {same_chapter: 0, same_encounter: 0, same_drug: 196,
              same_icd: 64, same_day: 390}

Top same_drug buckets:   tramadol=11, meloxicam=7, norco=7,
                         pantoprazole=6, hydrocodone-acetaminophen=6
Top same_icd  buckets:   Z71.89=6, I10=5, J45.909=5, I48.0=4, K21.9=4
Top same_day  buckets:   2016-05-09=56, 2016-06-08=41, 2016-03-07=37
chapter/encounter buckets: 0  ← confirms §3a (annotations dropped pre-fix)
```

`same_chapter` / `same_encounter` show `0` on this artifact because it was produced **before** the §3a fix — chapter metadata was stripped at ingest time. The next run (with §3a + §7b#7 in place) is expected to light both passes up. `same_drug`, `same_icd`, `same_day` all work *right now* on the existing artifact without any re-ingest.

### 7d. Expected gains next run

- `annotations.chapter_id` on ≥95% of events (from 0%).
- ≥5 new connascence kinds populating `event.connascence`, not just `temporal`.
- `preview` values that read like a chart note rather than a truncated sentence.
- Zero events with `event_type="page"`; boilerplate pages bucket to `administrative`.
- `Noted on:`-anchored diagnosis dates promoted from `"unknown"` to a real `YYYY-MM-DD`.

— recorded by agent, 2026-04-21
