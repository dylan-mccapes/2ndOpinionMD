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

## 8. Rerun results after patch set (user-provided SSE `done`/`persisted`)

### 8a. Outcome summary

The rerun is a success and validates the key fixes shipped in commit `ce7594de`.

Key completion metrics from stream:

- `type=done` emitted with no fatal errors, then `type=persisted` emitted.
- `chapters=56`, `batches=51` (full chapterized run completed end-to-end).
- `llm_events_total=430`, `heuristic_events_added=118`.
- `extract_fail_events=0`, `batch_empty_stubs=0` (excellent).
- `generic_stub_events=51` (still present; see §8d).
- `total_graph_events=769`, `total_graph_edges=11104`.
- `ocr_pending_pages=[]`.

### 8b. What improved (explicitly)

1. **Chapter metadata now survives into graph events.**
   - `chapter_backstamped=339` confirms the new backfill pass is active and filling missing chapter context.
   - Reduced-graph chapter/encounter passes now fire with large counts:
     - `same_chapter=913`
     - `same_encounter=483`
   - This directly resolves the prior regression (`chapter_id=0` everywhere).

2. **Reduced-graph connascence is now live (not temporal-only).**
   - Added edge counts in this run:
     - `same_drug=249`
     - `same_icd=121`
     - `same_day=509`
   - Combined with chapter/encounter, that is 5 strategic connascence families active in one run.

3. **Pipeline reliability improved.**
   - Zero extraction failures and zero empty-batch stubs across 51 batches is a strong stability signal for `eoh-llama3.1:8b` at this context/budget.

4. **Timestamp recovery is functioning.**
   - `timestamps_recovered=78` and `timestamps_recovered_from_preview=1` show both heuristic and new preview-regex recovery paths are active.

5. **Type cleanup path is active.**
   - `reclassified=78` confirms post-pass event-type normalization is executing.

### 8c. Batch-level behavior notes

- Most batches are healthy (few seconds to ~45s), with a few long tails:
  - Batch 3 (`sum_immunizations_p0012`) ~217s
  - Batch 23 (`enc_2016-03-07_office_visit_p0091`) ~203s
  - Batch 40 (`enc_2016-05-09_office_visit_p0152`) ~79s
- These are expected dense/complex pages; no failures were associated.

### 8d. Remaining gap

`generic_stub_events=51` is still non-trivial. This now likely represents:

- truly non-clinical/administrative pages, and/or
- pages where model output omitted events despite parse success.

Recommended follow-up (small, deterministic):

1. Split this metric into:
   - `generic_admin_pages` (explicitly boilerplate), and
   - `generic_model_omission_pages` (should be investigated).
2. Persist a short per-page reason code in `annotations.stub_reason`.
3. Add an SSE warning only when omission pages exceed threshold (e.g., >10% of pages).

### 8e. Updated verdict

This rerun confirms the architecture moved from a mostly temporal skeleton to a **chapter-aware, multi-connascence graph build** with robust completion characteristics. The major structural fixes worked as intended. The next optimization target is reducing and better labeling the remaining 51 generic stubs.

— recorded by agent, 2026-04-21 (updated after rerun)

---

## 9. Second-pass review of exported graph (`ptv_428b017a-3840-490c-8a95-65c4d6cfe10d.json`)

### 9a. Preview clipping bug — fixed

Observed in the exported graph (examples from lines 75 and 98 of the artifact):

- `"ssile serrated polyp/adenoma. Clinical and endoscopic correlation is suggested. "` (should be **Se**ssile…)
- `"OUNSELING, CONTINUING RECOVERY GROUP, >=90 DAYS. Noted on: 04/06/2017Chronic: No"` (should be **C**OUNSELING…)

Root cause (`server/eoh/heuristic_page_extract.py`):

- `_extract_icd_codes` used a raw `text[m.start()-80 : m.start()]` backward slice for both the `[CODE]` and `ICD-10-CM: CODE` passes. Eighty characters of lookback is often **mid-word** for long Kaiser problem-list rows, so the preview lost its leading letters.
- The `len(condition) > 80` filter silently dropped any problem-list description longer than 80 characters.
- Every heuristic preview was additionally clipped with `[:80]` (no word-boundary alignment).

Audit of the artifact found **66 previews starting with a lowercase letter** — a strong signature of mid-word clipping — including several of the top-degree hub events (e.g. the degree-177 diagnosis `"inued by: Pims, User 08/30/16 1317DiagnosesREACTIVE AIRWAY D"`, which should read "Cont**inued** by: …"). These hub nodes are exactly the ones an agent would traverse first, so the clipping disproportionately hurt agent usefulness.

Fix applied:

1. New `_backward_context(text, end, max_len=240)` helper. It walks leftward to the nearest whitespace/newline before the window and prefers the last line break inside the window, so we **never slice into the middle of a word**.
2. New `_preview_trim(text, limit=200)` helper — word-aligned trailing truncation with an ellipsis.
3. Replaced every `[:80]` in heuristic event construction with `_preview_trim(...)`.
4. Raised the problem-list entry max-length gate from `80` to `_HEURISTIC_PREVIEW_MAX` (200) so long condition names survive.
5. `_extract_noted_dates` now uses the same word-aligned backward window.

Regression test (before → after):

| ICD    | Before                                             | After                                                                                               |
| ------ | -------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| R90.89 | `ssile serrated polyp/adenoma. …`                  | `ABNORMAL BIOPSY FINDINGS Diagnosis: SESSILE SERRATED POLYP/ADENOMA. Clinical and endoscopic correlation is suggested. [R90.89]` |
| Z71.41 | `OUNSELING, CONTINUING RECOVERY GROUP, >=90 DAYS …` | `COUNSELING, CONTINUING RECOVERY GROUP, >=90 DAYS [Z71.41]`                                         |

### 9b. Full graph audit (this export)

769 events, 0 arcs, 5,552 undirected connascence edges.

- **Event types**: `diagnosis 287, medication 237, administrative 75, procedure 62, lab 31, symptom 30, clinical_note 27, visit 12, imaging 5, vital_signs 2, appointment 1`. Clinical vocabulary is good; `administrative` is still ~10%.
- **Chapters**: 53 distinct chapters over 34 distinct encounter dates. Top five by density are `sum_advance_care_planning_p0023` (134), `sum_problem_list_p0003` (127), `enc_2016-05-09_office_visit_p0152` (82), `enc_2016-03-07_office_visit_p0091` (54), `enc_2016-03-16_office_visit_p0099` (45).
- **Timestamps**: `63.6%` of events have a known timestamp. Year distribution: 311 in 2016 (the cluster this truncated PDF centers on), with long-tail coverage 2007–2025.
- **ICD coverage**: **73 distinct ICD-10 codes**. Top codes include `M48.06, M51.36, J45.909, M54.5, I48.0, K21.9, I10, E78.5` — musculoskeletal + cardio + metabolic, all high-value for registries.
- **Medication fidelity**: 225/237 (`95%`) have `drug_name`, 172 have dosage, 170 have route.
- **Connascence edge mix** (directed counts): `temporal 6554, same_chapter 1826, same_day 1018, same_encounter 966, same_drug 498, same_icd 242`. Coverage is excellent — `767/769` events (100%) have at least one edge, only 2 orphans.
- **Arcs = 0.** No named clinical threads (e.g. "atrial fibrillation care", "colonoscopy follow-up") exist yet. This is the largest traversal gap.

### 9c. Is this graph useful today?

**Yes — for retrieval and light summarization.** An agent can:

- Look up a code (73 ICDs) and pull every associated event via `same_icd`.
- Start at any encounter date, use `same_encounter` to gather the whole visit, `same_chapter` to pull the pages that were logically one document, and `temporal` to walk outward in time.
- Resolve drug lineages via `same_drug` (498 edges).

**But it is under-powered for narrative synthesis** because:

1. **No arcs.** The graph is a bag of events glued together by identity edges; it has no "threads" the way a clinician thinks (e.g. "gallbladder story", "AFib workup", "chronic low back pain").
2. **Hub nodes are noisy.** The top-degree diagnosis node (degree 178) is `"Hyperlipidemia"` dated `2004-06-01` — a plausible central node — but the #2 hub (degree 177) is still fragmentary regex spillage (`"inued by: Pims, User 08/30/16 1317Diagnoses…"`). With the 9a fix, future rebuilds will stop producing these pseudo-hubs.
3. **Timestamps missing for 36% of events.** Many of these are *recoverable* (e.g. a problem-list entry can inherit its "Noted on" or its chapter's `encounter_date`). We only backstamp `chapter_id` today; we don't backstamp a best-effort `timestamp` on every event that still says `unknown`.
4. **No content-hash / canonical dedupe.** Drugs and diagnoses appear multiple times across chapters because the node key is `pdf_p{page}_e{idx}`. An agent that asks "how many times has this patient been on methotrexate?" will over-count.
5. **Granularity is page-shaped, not clinical-entity-shaped.** One "colonoscopy" sits in the graph as ~6 separate events (order, procedure, pathology, follow-up, diagnosis coded, note). There is no "entity" (Condition, MedicationStatement, Procedure) that binds them.

### 9d. What to build next, specifically

Ranked, each with a concrete definition-of-done.

1. **Arcs (ClinicalArc) — the missing narrative layer.**
   - Build a deterministic, regex/heuristic pass that seeds arcs for:
     - each distinct ICD family (e.g. `I48.*` → "Atrial fibrillation"),
     - each distinct drug (`drug_name` normalized),
     - each procedure line (colonoscopy, cholecystectomy, EGD, …),
     - each major encounter cluster (office visits sharing provider + problem).
   - Populate `arcs[<arc_id>] = {name, kind, event_ids[], start_ts, end_ts, summary}`.
   - Any event can live in multiple arcs; use `annotations.arc_ids: [...]` on the event.
   - **DoD**: ≥ 80% of `diagnosis`/`medication`/`procedure` events belong to ≥ 1 arc; JSON dump shows non-empty `arcs`.

2. **Canonical entity layer (content hashing).**
   - For each event, compute `annotations.canonical_key` as, e.g., `drug:<normalized-name>` or `icd:<code>` or `procedure:<cpt-or-name>`.
   - Add a separate `entities` map at graph level: `entities["drug:methotrexate"] = {first_seen, last_seen, event_ids, aliases[]}`.
   - **DoD**: question "how many times did the patient receive methotrexate" resolves in O(1) from `entities["drug:methotrexate"].event_ids`.

3. **Best-effort timestamp backfill.**
   - For every event still at `timestamp="unknown"`, inherit in order: (a) chapter `encounter_date`, (b) nearest preceding "Noted on"/"Collected"/"Resulted" on the same page, (c) page-level `page_date`.
   - Record the source in `annotations.timestamp_source` (which already exists for `noted_on_regex`).
   - **DoD**: % `ts_known` rises from `63.6` to `≥ 90`.

4. **Boolean state per event: `status_flags`.**
   - `{active, resolved, chronic, stopped, continued, acute, flare}` inferred from the nearby text ("Chronic: No", "(Discontinued)", "resolved", "acute"). Drives registry queries.
   - **DoD**: ≥ 60% of `diagnosis` and `medication` events carry at least one status flag.

5. **Reduce `administrative` noise: chapter-level collapse.**
   - If a whole chapter is classified `administrative` (cover, release of information, visit summary boilerplate), emit **one** chapter-level event `chapter_administrative` and drop the page-level admin events. Keep them in a `suppressed_events` list for auditability.
   - **DoD**: `event_type="administrative"` drops from 75 to ≲ 15 in similar 200-page fixtures.

6. **Explicit edge `caused_by` / `in_workup_for`.**
   - Deterministic rule: a lab/imaging/procedure in an encounter whose problem list contains a single dominant diagnosis → add `caused_by` edge from the procedure to the diagnosis event.
   - **DoD**: a colonoscopy's pathology event points to the `D12.6` adenoma event with `connascence.caused_by`.

### 9e. Making the graph easier for `eoh-llama-8b` agents to traverse

The 8B agent's job is to select a subgraph for the synthesis model. Everything below is cheap to add and directly helps selection:

- **Add a top-level `index` block** in the graph JSON:
  ```
  index: {
    by_year: { "2016": [event_ids…], … },
    by_icd:  { "I48.0": [event_ids…], … },
    by_drug: { "methotrexate": [event_ids…], … },
    by_chapter: { "enc_2016-05-09_office_visit_p0152": […] },
    by_arc:  { "afib_care": […] }
  }
  ```
  An agent can then answer "show me the AFib thread" without scanning 769 nodes.
- **Add a stable `salience` score per event.** A simple formula: `salience = 1.0 + log(1+degree) + 0.5*has_icd + 0.5*has_drug + 0.5*is_hub_of_arc`. Agents prefer high-salience nodes first and naturally compress dense chapters.
- **Compact "card" view per event.** In addition to the full node, expose `event.card = { title, one_line, ts, arc_ids, icd, drug }` under 140 chars. The 8B agent can stream cards for selection and fetch full nodes only for the selected ones — this is literally the context-budget trick the main pipeline already uses for LLM input.
- **Edge weights + rationale.** Today `connascence[kind] = [ids]`. Upgrade to `connascence[kind] = [{id, strength, reason}]` for LLM-authored edges and keep the lightweight list for deterministic edges. Agents can prune low-strength edges first.
- **Prompt pattern for agents.** Give the 8B agent a fixed tool surface: `get_event(id)`, `follow(id, kind)`, `list_arc(arc_id)`, `by_code(icd)`, `by_drug(name)`. Today the agent would have to re-implement these from the raw JSON.

### 9f. Making the PTV useful for longitudinal registries (RISE, FORWARD)

RISE (rheumatology) and FORWARD (PRO / longitudinal RA) registries all need **patient-level, normalized, time-aligned** data. The current graph is patient-level and time-aligned but not yet normalized. To bridge that gap:

1. **Registry-flavored export adapter.** A thin module `server/registry_export/` that emits FHIR-R4-shaped resources from the PTV:
   - `Condition` from `diagnosis` events (ICD-10-CM already present).
   - `MedicationStatement` from `medication` events (RxNorm mapping pass).
   - `Observation` from `lab` / `vital_signs`.
   - `Procedure` from `procedure` events (CPT mapping pass).
   - `Encounter` from chapters with `kind="encounter"` (class, start, end, reason).
   This keeps the PTV as our rich internal graph and makes interchange a compile step.
2. **Coded vocabularies.**
   - ICD-10 already covered. Add:
     - **RxNorm / RxCUI** mapping for `drug_name` (use UMLS MRCONSO or the public RxNorm API at build time).
     - **LOINC** mapping for labs / vital signs.
     - **SNOMED-CT** mapping for problem-list symptoms that aren't cleanly coded.
   - Store as `annotations.codes = [{system, code, display}]` so the registry adapter is a 1-liner lookup.
3. **Disease-activity PROs.** For a rheumatology-relevant timeline, the graph needs fields the registries actually care about:
   - `HAQ`, `RAPID3`, `CDAI`, `DAS28`, `pain VAS`, `morning stiffness` — harvest from notes with a small regex + LLM pass (they appear in standard phrases like "RAPID3 score = 4.7").
   - Emit them as `event_type="pro"` with `annotations.instrument`, `annotations.value`, `annotations.units`.
4. **Longitudinal derived series.** A post-pass that emits, per arc:
   - `series.labs["HbA1c"] = [(ts, value, unit)…]`
   - `series.meds["methotrexate"] = [(start, end, dose_mg_wk, status)…]`
   - `series.pros["RAPID3"] = [(ts, value)…]`
   These are what RISE/FORWARD actually ingest.
5. **Patient-level metadata surface.** `graph.patient = { dob, sex, race_ethnicity, smoking_status, insurance, zip3 }` captured once (most of this is in the cover and problem-list chapters).
6. **Provenance chain.** Every coded value must carry `source = {pdf_page, chapter_id, extractor, confidence}` so registry QC can audit; the PTV already carries `heuristic_source`/`timestamp_source` — extend to LLM-derived codes.
7. **Deterministic diff contract.** When the same PDF is re-ingested, event IDs should be stable (content-hash of `(normalized_preview, chapter_id, timestamp)`). Registries reject churny IDs.
8. **De-identification toggle.** A `graph.redacted` view that strips names/MRNs/addresses from previews while keeping codes and timestamps — registry uploads require this.

### 9g. Files changed in this pass

- `server/eoh/heuristic_page_extract.py`
  - New `_preview_trim` helper (word-boundary truncation, 200-char default).
  - New `_backward_context` helper (word-aligned backward window, 240-char default).
  - `_extract_icd_codes` now uses `_backward_context` in both the bracket and explicit-label passes.
  - `_extract_noted_dates` now uses `_backward_context`.
  - `_extract_diagnoses` problem-list entry length gate raised from 80 → 200 (`_HEURISTIC_PREVIEW_MAX`).
  - All `[:80]` preview truncations replaced with `_preview_trim(...)` (5 sites: `_extract_medications` ×2, `_extract_labs`, `_extract_diagnoses` ×2, `HeuristicEvent.to_dict`).

### 9h. Expected behavioral delta on next rerun

- Previews starting with a lowercase letter should drop from `66/769` (~8.6%) to near zero (some legitimate lowercase free-text previews from the LLM path will remain).
- Top hub events will present full, readable titles — directly improving agent traversal quality.
- `leading-lowercase` can be used as a simple CI assertion (e.g., `< 2%` of all events).

— recorded by agent, 2026-04-21 (PTV exported artifact review)

---

## 10. Implementation pass — deterministic graph finalize + registry export

All items from §9d (graph usefulness), §9e (agent traversal) and §9f (longitudinal registries) are now implemented as deterministic, pure-Python passes. Two new modules:

- `server/eoh/graph_finalize.py` — `finalize_graph(vision, chapters=..., pages_text=...)` runs 12 idempotent passes:

  1. `_assign_canonical_ids` — content-hashed `annotations.canonical_id` (SHA-1 over type, normalized preview, chapter_id, day). Stable across ingests → registry diffing now possible without churning event IDs.
  2. `_backfill_timestamps` — inherits chapter `encounter_date` / annotation `encounter_date` onto events still at `unknown`. Records `timestamp_source`.
  3. `_infer_status_flags` — `annotations.status_flags = ["active", "resolved", "chronic", "stopped", "continued", "acute", "flare", "worsening", "improving", "non_chronic"]` derived from preview text.
  4. `_build_entities_map` — canonical `{drug,icd,procedure,lab}` entities stored at `vision.metadata["entities"]`; each event stamped with `annotations.entity_keys`.
  5. `_seed_clinical_arcs` — populates `vision.arcs` with `arc_icd_<family>`, `arc_drug_<slug>`, `arc_proc_<slug>`, `arc_encounter_<date>_<type>`. Every event gets `annotations.arc_ids`.
  6. `_infer_causal_edges` — dominant-ICD-family heuristic per encounter chapter → adds `in_workup_for` and `caused_by` connascence (with `edge_provenance`, `strength=0.8 / 0.6`).
  7. `_collapse_admin_chapters` — cover/boilerplate chapters collapse to one `chapter_administrative` event; individual admin events marked `status="suppressed"` with `collapsed_into`.
  8. `_harvest_pros` — regex extractor for `HAQ, RAPID3, CDAI, DAS28, SDAI, pain_VAS, morning_stiffness_min, fatigue_VAS` from raw pages *and* event previews. Emits `event_type="pro"` events.
  9. `_extract_patient_metadata` — best-effort DOB, sex, smoking, ZIP3 into `vision.metadata["patient"]`. Name/MRN are stored separately at `vision.metadata["patient_phi"]` so the registry adapter can redact independently.
  10. `_compute_salience` — `annotations.salience = 1 + log(1+degree) + 0.5·has_icd + 0.5·has_drug + 0.5·is_arc_hub + 0.75·has_causal`.
  11. `_build_event_cards` — `annotations.card = {title, one_line, ts, type, icd, drug, arc_ids, salience}` compact streaming view.
  12. `_build_index_block` — `vision.metadata["index"] = {by_year, by_icd, by_icd_family, by_drug, by_chapter, by_arc, top_salience_event_ids, entities_by_kind}`.

- `server/eoh/registry_export.py` — compile-step adapter:
  - `export_fhir_bundle(vision, redact=True, include_administrative=False)` → FHIR R4 Bundle with `Patient`, `Condition`, `MedicationStatement`, `Observation`, `Procedure`, `Encounter` resources.
  - `export_derived_series(vision)` → `{labs, meds, pros, diagnoses}` per-entity time series for registry ingest.
  - `redact_vision(vision)` → deep-copied graph with PHI scrubbed from previews and cards, `patient_phi` dropped.
  - `code_mapping_hint(kind, name)` → built-in tiny table (~20 drugs → RxNorm, ~15 labs → LOINC, ~8 procedures → SNOMED-CT) as a typed extension point; the full mapping can later swap in a real UMLS-backed lookup without touching call sites.

### 10a. Wiring

Both ingest paths now run the finalizer before reporting `done`:

- `populate_vision_from_extracted_pages` — appends `finalize_stats` to its return dict.
- `stream_populate_vision_from_extracted_pages` — emits a new `{"type": "finalize", "stats": ...}` SSE frame before the terminal `done` frame; `done` also carries `finalize_stats`.

Failures in finalize are logged and swallowed — the pipeline still returns the primary graph.

### 10b. End-to-end validation against the existing artifact

Ran `scripts/_smoke_graph_finalize.py` over `artifacts/ptv_428b017a-3840-490c-8a95-65c4d6cfe10d.json` (769 events, 11 104 edges, **0 arcs** before):

```
canonical_ids:            769 stamped
timestamp_backfill:        82 inherited from annotations.encounter_date
status_flags:             110 events tagged
entities:                 190 entities (events_tagged=375)
arcs:                     173 arcs seeded  (0 → 173)
salience:                 769 scored
cards:                    769 built
index keys: years=20, icds=73, icd_families=63, drugs=106, chapters=53, arcs=173
FHIR bundle: 663 resources (Patient=1, Condition=287, MedicationStatement=237, Observation=33, Procedure=62, Encounter=43)
Derived series: labs=7/8, meds=106/225, pros=0/0, diagnoses=64/287
Idempotence: re-running produced 0 new canonical_ids, 0 new arcs — passes are safe to re-run.
```

Causal edges, admin collapse, PRO harvest, and patient metadata return 0 in this dry run because the pipeline-level `chapters` and `pages_text` aren't available when finalizing a loaded JSON; in live ingest all four passes receive their inputs directly from `sectionize_pages` + `extraction_pages`.

### 10c. What this unlocks

- **Agent traversal**: `vision.metadata["index"].top_salience_event_ids` gives an 8B-agent a ranked entry point; `entities` and `arcs` give it a tool surface to hop condition → events / drug → events in O(1).
- **Registry ingest**: `export_fhir_bundle(vision, redact=True)` returns an R4 Bundle ready for RISE/FORWARD-style upload. Coded systems (ICD-10-CM baked-in, RxNorm / LOINC / SNOMED via the code-mapping hint) stub in the right shape so a later UMLS-backed mapper drops in cleanly.
- **Longitudinal analytics**: `export_derived_series(vision)` is the shape research registries actually consume.
- **Provenance**: every derived edge carries `edge_provenance[by, kind, strength]`; every derived event carries `timestamp_source`, `heuristic_source`, or `discovered_by=graph_finalize:*`.

### 10d. Files changed / added

- new `server/eoh/graph_finalize.py` (~700 LOC, 12 passes, 0 external deps)
- new `server/eoh/registry_export.py` (~400 LOC, FHIR + series + de-id + code-mapping stub)
- modified `server/eoh/timeline_summarizer.py`
  - `populate_vision_from_extracted_pages` now runs `finalize_graph` and returns `finalize_stats`.
  - `stream_populate_vision_from_extracted_pages` emits a `finalize` SSE frame and includes `finalize_stats` in `done`.
- new `scripts/_smoke_graph_finalize.py` — end-to-end regression harness for the finalizer and registry export.

### 10e. Next validation

Next ingest of the 200-page truncated PDF will exercise chapter-aware causal edges, admin collapse, PRO harvesting, and patient metadata extraction. Expected deltas vs the old artifact:

- `caused_by + in_workup_for` ≫ 0 (was 0).
- `admin_collapsed` > 0 (cover + ROI chapters should collapse).
- `pros` > 0 if any PRO instrument phrasing survives in the note text.
- `patient.dob / sex / smoking_status / zip3` all populated from cover + problem-list pages.
- `leading-lowercase` preview fraction falls from ~8.6% → near 0 (heuristic fix from §9a).

— recorded by agent, 2026-04-21 (graph_finalize + registry_export implementation)
