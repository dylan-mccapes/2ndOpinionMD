# Document & Artifact Handling — Patient Vault

Status: proposal + baseline reference. Implementation gaps are called out explicitly
below under "TODO" bullets. This document is the single source of truth for how
patient-uploaded documents move through the Epistemic Vault into the
`PatientTimelineVision` (PTV) graph.

Audience: backend engineers wiring upload endpoints, frontend engineers driving the
vault upload UX on `/`, and anyone adding a new medical-record source.

## 1. What a patient uploads

A patient can drop **any number of files** into the vault in one action:

- Lab PDFs (single-page or bundled)
- Imaging reports (PDF or image)
- Clinical notes (PDF, DOCX, text)
- Prescriptions (PDF, image, text)
- CSV exports (e.g. CGM, Apple Health)
- FHIR / HL7 JSON exports
- **Full longitudinal timeline** (e.g. Epic MyChart export — often hundreds of pages)

They do **not** need to fill any metadata. Document type, date, and notes are all
optional fields on the upload form. When they are present we use them; when they are
not we derive everything from the file.

## 2. Two ingest tiers — when to use each

We already ship two endpoints. Neither is going away; they serve different needs.

### Tier A — lightweight artifact (current `index.html` default)

```
POST /api/timeline/artifact           (session Bearer)
  multipart: file, document_type?, document_date?, notes?
  → 200 { event_id, patient_id, filename, status: "artifact_stored_in_ptv" }
```

- Max **8 MB** per file.
- Stores a `patient_artifact` node on the user's PTV graph (
  `server/eoh/ptv_journal_bridge.add_patient_artifact_event`).
- For `text/*` content types we keep an 8 KB preview snippet; for everything
  else we store only file metadata (name, mime, size, optional doc type/date/notes).
- **No LLM call.** No event extraction. No RAG indexing.
- Purpose: immediate receipt-in-vault acknowledgement, and something the patient
  can see listed in the vault UI, without spending GPU time.

### Tier B — eoh-llama 8B inference (current `/infer` pipeline)

```
POST /api/timeline/{patient_id}/infer      (no session auth yet — TODO)
  multipart: file, format=pdf|json, password?, model=eoh-llama3.1:8b, num_ctx=32768,
             store_results=true, build_graph=true
  → SSE stream: accepted → status → pdf_read → pii_scrub_done → pre_scan_done
              → infer_start → batch_start/batch_done × N → graph_update
              → complete | error
```

- Max **500 MB**.
- Pipeline (code: `server/api/timeline_infer_routes.py`):
  1. pypdf text extraction in a thread pool (PDF mode) or JSON parse (JSON mode).
  2. `server.utils.pii_scrub.scrub_pages` with header-name detection.
  3. `server.eoh.heuristic_page_extract` regex pre-scan — dates, meds, labs, dx, ICD.
     Pre-scan events are added to PTV with `discovered_by=pdf_page_<n>`, and
     temporal connascence edges inferred (`window_days=7`).
  4. **eoh-llama 8B** batch loop via Ollama `/api/chat`
     (`server.api.stream_config.OLLAMA_BASE_URL`, default `http://localhost:11434/v1`).
     The model verifies/supplements the pre-scan and produces structured events.
  5. Each batch's events are persisted to `ehr.patient_timeline` and merged into
     the PTV graph (`add_events_from_pdf_page` → `vision.add_event`).
  6. Final temporal connascence pass + `save_timeline_vision` (→
     `ehr.patient_graph_vision`).
- Enforces a **single-flight GPU lock** (`_infer_lock`): a second caller gets `409`
  with the active job metadata.

## 3. Vault UX behaviour (on `/`)

The Epistemic Vault on `/` (`index.html`) offers **one upload control** for
documents, but it routes to one of two backends based on intent:

| UX control | Backend | Why |
| --- | --- | --- |
| **Submit Documents** (Documents tab) | Tier A — `/api/timeline/artifact` | Default. Fast, always succeeds, uploads list shows up immediately. |
| **Ingest with eoh-llama 8B** (new button, TODO) | Tier B — new session-auth route (see §5) | Only when the patient wants event extraction. One file at a time because of the GPU lock; multiple files are uploaded sequentially by the browser. |
| **Initialize Timeline** (Timeline tab) | Heavy PDF import (`server/scripts/import_timeline_pdf.py` path) | Explicit opt-in for the full longitudinal record. |

The existing **"Uploaded to your vault"** list in the Documents tab now shows every
successful artifact by title (notes → filename → meta line), so the patient always
gets visible feedback, independent of ingest tier.

## 4. Canonical event shape (one shape, every source)

Every event — whether it came from a journal entry, a lightweight artifact, a
mock-timeline insert, or an 8B-extracted PDF batch — is written through
`PatientTimelineVision.add_event(...)` and therefore has the same shape. The
fields we use for ingest-from-documents are:

```jsonc
{
  "event_id": "<see §6 for dedup key>",
  "event_type": "lab | symptom | medication | imaging | flare | visit |
                 procedure | diagnosis | note | patient_artifact |
                 journal_entry | patient_reported_outcome | mock_timeline_event",
  "timestamp": "ISO-8601",
  "preview": "short narrative (≤ 800 chars)",
  "discovered_by": ["vault_artifact_upload", "eoh-llama-8b-infer", ...],
  "annotations": {
    // provenance back to the file the event came from
    "artifact_id":       "<stable id assigned at upload>",
    "artifact_sha256":   "<content hash>",
    "artifact_filename": "original filename",
    "document_type":     "lab | imaging | note | prescription | other",
    "document_date":     "optional ISO date user-provided",
    "source_page":       42,           // PDF page, if known
    "source_batch":      7,            // 8B batch index, if any
    "confidence":        0.0 - 1.0     // 8B confidence
  },
  "connascence": { "temporal": ["<other_event_ids>"], "causal": [...] }
}
```

Two things matter for the document pipeline:

- **`discovered_by` is a list, not a single string.** When two sources independently
  produce the same event we append instead of replacing — the graph tracks who
  found what. `add_event` already does this.
- **`annotations.source_artifacts` (new)** is a list of
  `{ artifact_id, artifact_sha256, source_page?, source_batch? }`. When a merge
  collapses duplicates (§6), the surviving event aggregates the artifacts it came
  from. This is how we later answer "which file did this dx row come from?".

## 5. Multi-artifact ingest endpoint (proposal)

Gap: the current `/infer` endpoint takes one file, identifies the patient by path
parameter, and has no session auth. The vault UX needs:

1. Session auth (Bearer) identifies the patient — no caller-supplied `patient_id`.
2. Multiple files in one call, each processed sequentially through Ollama under
   the existing GPU lock.
3. A predictable per-file event stream so the UI can update the "Uploaded to your
   vault" list as each file finishes extraction.

Proposed endpoint (**TODO — not yet implemented**):

```
POST /api/timeline/artifacts/ingest        (session Bearer)
  multipart: files[] (≥1, ≤20 per call)
             document_type?, document_date?, notes?      # applied to ALL files
             model=eoh-llama3.1:8b
             store_results=true
             build_graph=true
  → SSE stream, per file:
      artifact_accepted { artifact_id, filename, size_bytes, sha256, is_duplicate }
      // if is_duplicate: no further events for this file; skipped server-side
      pdf_read / json_parsed / text_extracted { filename, ... }
      pre_scan_done { filename, events, temporal_edges }
      batch_start / batch_done  × N
      graph_update { total_events, total_edges }
      artifact_done { artifact_id, events_extracted, events_merged, events_duplicated }
    then once at the end:
      complete { artifacts: [...], events_extracted_total, events_merged_total,
                 events_duplicated_total, total_elapsed_ms }
```

Implementation notes:

- Reuse `server/api/timeline_infer_routes._run_inference` per file; iterate the
  caller's uploads inside a single `async with _infer_lock:` block. The GPU lock
  is held for the whole batch so we never interleave with somebody else.
- Patient id comes from `get_vault_user_from_session` (same dependency used by
  `POST /api/timeline/artifact`).
- For formats we cannot currently infer (DOCX, CSV, FHIR JSON) fall back to Tier A
  behaviour: store the `patient_artifact` node with a text snippet if applicable,
  and stream an `artifact_done` with `events_extracted=0, reason="unsupported_for_8b"`.
  This lets the UI still show those files in the vault list.
- Emit ALL the Tier A metadata as well, so the lightweight "Uploaded to your vault"
  list stays correct regardless of whether 8B extraction ran.

Client loop (simplest integration):

1. User drops `file[0..n]` into the Documents tab.
2. Frontend posts them once to `/api/timeline/artifacts/ingest`.
3. On each `artifact_accepted` event, call `appendUploadedArtifactRow({...})` so
   the patient sees the file arrive. Badge = *Processing*.
4. On `artifact_done`, flip the badge to *Extracted · N events* (or
   *Stored* if `events_extracted=0`).
5. On `complete`, no further action — the PTV is already saved.

## 6. Deduplication — artifact level and event level

There are two kinds of duplicates we care about:

### 6.1 Artifact-level (same file uploaded twice)

- Every file produces `artifact_sha256 = sha256(file_bytes)` at upload time.
- We record `artifact_id = "art_<sha256[:16]>"` so the id is idempotent: re-uploading
  bit-identical bytes yields the same id.
- **If the sha is already present** in the user's PTV `metadata.artifacts[]`,
  emit `artifact_accepted { is_duplicate: true }` and skip ingestion. No GPU time,
  no double-write. The existing artifact node is touched with an updated
  `last_seen_at` stamp.
- `vision.metadata["artifacts"]` (list) keeps the per-user catalog:

  ```json
  {
    "artifact_id": "art_abc123...",
    "sha256":      "abc123...",
    "filename":    "chart_mychart_export.pdf",
    "mime":        "application/pdf",
    "size_bytes":  12345678,
    "uploaded_at": "2026-04-17T16:07:23Z",
    "last_seen_at":"2026-04-17T16:07:23Z",
    "document_type": "note",
    "document_date": null,
    "user_notes":   null,
    "ingest_tier":  "A | B",
    "pages":        182,
    "events_extracted": 47
  }
  ```

### 6.2 Event-level (same event found in two files, or in regex + 8B of one file)

The existing `vision.add_event(event_id, ...)` already does event-level dedup
*by id*. We need a dedup key that's stable across files. Proposal — a composite
"coordinate" computed **before** calling `add_event`:

```python
dedup_key = canonical(
    patient_id,
    event_type,
    normalized_timestamp_day,     # truncate to UTC date
    normalized_label,             # lower, strip, collapse whitespace, rxnorm/loinc/snomed if present
)
event_id = f"{event_type}_{sha256(dedup_key)[:16]}"
```

Concrete normalization rules (mirror the ones already used in
`server.eoh.timeline_summarizer._dedupe_timeline_rows` — we extract that into
`server/eoh/event_dedup.py` for reuse):

| event_type | normalized label |
| --- | --- |
| `lab` | LOINC code if extracted; else lowercased analyte name (e.g. `hba1c`) |
| `medication` | RxNorm CUI if normalized; else lowercased generic (e.g. `methotrexate`) |
| `diagnosis` | ICD-10 code; else lowercased problem name |
| `imaging` | modality + body-region (`mri_knee_left`) |
| `procedure` | CPT code; else lowercased procedure name |
| `visit` | `visit_<day>` (collapse same-day duplicates) |
| other | `sha256(preview[:200])` fallback |

Merge behaviour when two sources produce the same `event_id`:

1. `discovered_by` is **union**-ed (`add_event` already does this).
2. `annotations.source_artifacts` is **appended** with every `(artifact_id, page,
   batch)` triple.
3. Numeric lab values: if both sources have a value, keep the one with higher
   `confidence`. Record the other under `annotations.value_variants`.
4. `preview` prefers the 8B-extracted sentence over a regex fragment (pick
   longest).
5. Temporal connascence edges (`connascence`) are unioned per-kind.

### 6.3 Rebuild vs merge when a full timeline arrives later

Scenario: patient uploaded three lab PDFs on Monday, then on Friday uploads a
full MyChart export that covers those same labs plus many more.

Policy — **merge, never overwrite**:

- Run Tier B on the big PDF exactly like any other artifact.
- Because labs share the same dedup key, Monday's lab events are found in the
  graph before the new events are inserted; the coordinate-keyed `add_event` call
  turns into an *update* (union `discovered_by`, append `source_artifacts`), not a
  new node. The original Monday artifact's provenance is preserved.
- Pre-scan temporal edges are re-run after the merge so the big PDF's richer
  temporal context weaves in.
- The PTV `metadata.artifacts` list grows by exactly one entry (the big PDF).
- `ehr.patient_timeline` gets **new rows only for genuinely new events** —
  `_store_extracted_events` uses
  `INSERT ... ON CONFLICT (patient_id, event_type, content_sha) WHERE content_sha IS NOT NULL DO NOTHING`
  against the partial unique index from migration **007** (no `ts::date` in the
  index: `timestamptz::date` is not IMMUTABLE under PostgreSQL index rules).

Explicit non-goal: we do **not** try to "diff" an old and a new version of the
same document. If a MyChart export is re-downloaded, the sha changes (timestamps
drift) but the underlying events dedup correctly, so the user just sees the
second upload marked as `is_duplicate=false, events_extracted=N,
events_duplicated=N`.

## 7. Where things live — quick file map

| Concern | File |
| --- | --- |
| Tier A endpoint | `server/api/session_routes.py` (`POST /api/timeline/artifact`) |
| Tier B endpoint | `server/api/timeline_infer_routes.py` (`POST /api/timeline/{patient_id}/infer`) |
| Proposed multi-artifact ingest | `server/api/session_routes.py` (**TODO**: `POST /api/timeline/artifacts/ingest`) |
| PTV node helper for artifacts | `server/eoh/ptv_journal_bridge.add_patient_artifact_event` |
| PTV add-event dedup | `server/eoh/patient_timeline_vision.PatientTimelineVision.add_event` |
| Canonical dedup keys (proposed) | `server/eoh/event_dedup.py` (**TODO — extract from `timeline_summarizer._dedupe_timeline_rows`**) |
| Ollama client / 8B call | `server/api/timeline_infer_routes._call_ollama_8b` |
| Pre-scan regex | `server/eoh/heuristic_page_extract.py` |
| PII scrub | `server/utils/pii_scrub.py` |
| Alembic 006 (PRO) | `server/alembic/versions/006_add_journal_patient_reported_outcomes.py` |
| Alembic 007 | `content_sha` + partial unique index `(patient_id, event_type, content_sha)` |
| Vault UI — uploads list | `index.html` (`doc-uploaded-section`, `appendUploadedArtifactRow`) |

## 8. Operational notes

- **GPU single-flight**: `POST /infer` already enforces this. Tier B multi-file
  ingest MUST hold the same `_infer_lock` across the full batch — do not take and
  release between files, or another patient can slip in mid-upload.
- **Timeouts**: Ollama 8B batches are slow. Current client timeout is
  `read=900s`. A 180-page PDF can take 10+ minutes; the browser keeps the SSE
  connection warm with regular `status`/`batch_*` events.
- **Disk pressure**: we do not persist the raw file bytes; only the extracted
  text (scrubbed) and structured events hit disk. If we later want raw-file
  storage we should encrypt client-side first — PTV metadata is HIPAA territory
  but `patient_artifact` today deliberately stores no more than a text snippet.
- **FORWARD / PRO**: the same graph also mirrors journal rows with
  `event_type="patient_reported_outcome"` when the journal has
  `patient_reported_outcomes` set (`server/eoh/ptv_journal_bridge.py`). These
  flow through the same dedup keys, so a doctor-upload lab and a patient PRO for
  the same day do NOT collide — the event_type differs.

## 9. Open questions (please do not implement blindly)

1. Do we want an **"archive" tier** where Tier A artifacts are later retro-ingested
   through 8B? (UX: a "Run deep extraction on previous uploads" button.) It's the
   natural progression but would need background job infra.
2. Storage of raw files — some compliance auditors want the original PDF
   recoverable for 6+ years. Today we discard it after extraction. Explicit
   decision pending.
3. Do we index the text of **8B-extracted events** into the RAG vector store
   automatically (so `doc-search` on the vault finds them)? Currently only the
   legacy `POST /api/rag/upload_timeline_pdf` path does that.
4. Multi-patient households — if a file's name/header indicates a different
   patient than the authenticated session user, we currently accept and scrub.
   Probably we want a "doesn't look like you" soft-block in the UI.

— *last updated 2026-04-17 (feature/ptv-vault-auth-journal)*
