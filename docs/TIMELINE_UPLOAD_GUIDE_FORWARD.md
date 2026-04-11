---
title: "2ndOpinionMD — Timeline Upload Guide"
subtitle: "For Dr. Kaleb Michaud, PhD · FORWARD Registry Integration"
author: "Dylan McCapes · 2ndOpinionMD"
date: "April 2026"
geometry: margin=1in
fontsize: 11pt
linkcolor: blue
header-includes:
  - \usepackage{fancyhdr}
  - \pagestyle{fancy}
  - \fancyhead[L]{2ndOpinionMD}
  - \fancyhead[R]{FORWARD Timeline Upload Guide}
  - \fancyfoot[C]{\thepage}
---

\newpage

# 1. Overview

2ndOpinionMD accepts patient timelines via a single HTTP endpoint and runs them
through our local **eoh-llama 8B** model for structured event extraction,
clinical arc identification, and knowledge graph construction.  All inference
runs on-premise on PortalNode hardware (RTX 4090 GPUs) — no patient data
leaves the local network.

The endpoint supports two upload formats:

| Format | Best for | Content |
|--------|----------|---------|
| **PDF** (default) | Patients uploading their medical records directly | Unencrypted PDF of any size |
| **JSON** | Structured EHR exports from FORWARD or other registries | Array of event objects |

Both formats are chunked automatically to fit within the model's context
window.  Progress streams back in real time as Server-Sent Events (SSE).

---

# 2. Endpoint

```
POST /api/timeline/{patient_id}/infer
Content-Type: multipart/form-data
```

**Base URL**: `https://2ndopinionmd.ai`

Replace `{patient_id}` with a unique, de-identified patient identifier
(e.g. `forward_patient_00142`).

---

# 3. Uploading a PDF (Easiest)

This is the simplest path.  The patient (or data coordinator) uploads an
unencrypted PDF of their medical records.  The server extracts text from
every page, chunks the pages into batches, and runs each batch through
the 8B model.

### curl example

```bash
curl -N https://2ndopinionmd.ai/api/timeline/forward_patient_00142/infer \
  -F "file=@/path/to/patient_timeline.pdf" \
  -F "store_results=true" \
  -F "build_graph=true"
```

### Form fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `file` | Yes | — | The PDF file |
| `format` | No | `pdf` | Set to `pdf` (or omit entirely) |
| `password` | No | — | PDF password, if the file is encrypted |
| `store_results` | No | `true` | Write extracted events to the database |
| `build_graph` | No | `true` | Build a PatientTimelineVision knowledge graph |
| `model` | No | `eoh-llama3.1:8b` | Ollama model name |
| `num_ctx` | No | `32768` | Context window size (tokens) |
| `question` | No | *(clinical investigation)* | Override the extraction prompt |

### What happens

1. **Upload** — File bytes are received (progress visible in curl).
2. **PDF extraction** — pypdf extracts text from every page in a background
   thread.  An SSE `status` event reports progress.
3. **Heuristic pre-scan** — A fast regex pass (~0.5 ms/page) runs over every
   extracted page, pulling dates, medications (with dose and route), lab
   results, diagnoses, ICD-10 codes, and section context.  Pre-scan events
   are immediately added to the knowledge graph and temporal connascence
   edges (events within 7 days) are auto-linked.  An SSE `pre_scan_done`
   event reports what was found.
4. **Batching** — Pages are grouped into batches that fit the 8B model's
   context window (~48k characters, up to 10 pages per batch).  Each batch
   includes a "pre-scan skeleton" showing what regex already extracted.
5. **Inference** — Each batch is sent to eoh-llama 8B.  The model verifies
   the skeleton, corrects any errors, and supplements with events regex
   cannot find (symptoms, flares, treatment responses, clinical reasoning,
   causal relationships).  SSE events report per-batch progress.
6. **Graph construction** — LLM-extracted events merge into the pre-scan
   graph.  A final temporal connascence pass runs over the complete graph.
7. **Complete** — A final SSE event reports totals.

### Notes on large PDFs

- PDFs of any size are supported (tested with 4,223-page, 177 MB records).
- The heuristic pre-scan completes in seconds even for very large PDFs
  (~2 seconds for 4,000 pages) and immediately populates the graph.
- A 4,000+ page PDF produces ~420 batches at 10 pages each.
- Each batch takes 10–45 seconds depending on content density.
- Full processing of a very large record may take several hours.
- Only one inference can run at a time (GPU constraint).  A second request
  returns HTTP 409 with details about the active job.

---

# 4. Uploading Structured EHR JSON

If the patient's data is already structured (e.g. a FORWARD registry export
or FHIR-formatted EHR dump), upload it as JSON.  This skips PDF extraction
entirely and goes straight to batching and inference.

### curl example

```bash
curl -N https://2ndopinionmd.ai/api/timeline/forward_patient_00142/infer \
  -F "file=@/path/to/patient_ehr_export.json" \
  -F "format=json" \
  -F "store_results=true" \
  -F "build_graph=true"
```

The only difference from PDF is adding `-F "format=json"`.

### Expected JSON structure

The file should contain a JSON array of event objects, or an object with an
`events` key:

```json
{
  "events": [
    {
      "ts": "2024-01-15T10:30:00Z",
      "event_type": "lab",
      "source": "EHR",
      "text": "CRP elevated at 38.2 mg/L...",
      "structured": {
        "CRP": 38.2,
        "CRP_unit": "mg/L",
        "ESR": 54
      }
    },
    {
      "ts": "2024-03-20T14:00:00Z",
      "event_type": "visit",
      "source": "EHR",
      "text": "Follow-up visit. 3 swollen joints...",
      "structured": {
        "swollen_joint_count": 3,
        "das28_crp": 4.2
      }
    }
  ]
}
```

### Event fields

| Field | Required | Description |
|-------|----------|-------------|
| `ts` | Recommended | ISO-8601 timestamp |
| `event_type` | No | One of: `lab`, `symptom`, `medication`, `imaging`, `flare`, `visit`, `procedure`, `diagnosis`, `note` |
| `source` | No | Data source label (e.g. `EHR`, `FORWARD`, `patient_upload`) |
| `text` | Recommended | Free-text narrative describing the event |
| `structured` | No | Key-value pairs for extracted values (lab results, scores, etc.) |
| `meta` | No | Arbitrary metadata |

A bare JSON array (without the `events` wrapper) is also accepted:

```json
[
  { "ts": "2024-01-15T10:30:00Z", "event_type": "lab", "text": "..." },
  { "ts": "2024-03-20T14:00:00Z", "event_type": "visit", "text": "..." }
]
```

### Batching for large JSON

Events are serialized to text blocks and grouped into batches the same way
PDF pages are.  A JSON file with 2,000 events will typically produce 15–20
batches, each processed in 10–45 seconds.

---

# 5. Monitoring Progress

The endpoint returns a `text/event-stream` (Server-Sent Events).  Each event
has a type and a JSON payload:

```
event: accepted
data: {"patient_id":"...","model":"eoh-llama3.1:8b","file":"timeline.pdf",...}

event: status
data: {"phase":"pdf_extracting","message":"Extracting text from PDF (50 MB)..."}

event: pdf_read
data: {"total_pages":1847,"pages_with_text":1623,"total_chars":4200000}

event: status
data: {"phase":"pre_scan","message":"Running heuristic pre-scan on 1623 pages..."}

event: pre_scan_done
data: {"events":412,"dates":1847,"meds":38,"labs":95,"dx":67,"temporal_edges":280,
       "graph_events":412}

event: infer_start
data: {"patient_id":"...","total_batches":162,"model":"eoh-llama3.1:8b",...}

event: batch_start
data: {"batch":1,"total":162,"chars":47200,"page_range":"1-10"}

event: batch_done
data: {"batch":1,"extracted":18,"stored":18,"elapsed_ms":23000}

event: graph_update
data: {"total_events":430,"total_edges":285}

... (repeats for each batch) ...

event: complete
data: {"batches_processed":162,"events_extracted":892,"total_elapsed_ms":1500000,...}
```

The `-N` flag in curl disables output buffering so events appear in real time.

### Checking status

To check if an inference is already running:

```bash
curl https://2ndopinionmd.ai/api/timeline/infer/status
```

Returns:

```json
{"busy": true, "active_job": {"patient_id": "...", "started_at": "..."}}
```

or `{"busy": false}` if the GPU is available.

---

# 6. FORWARD Convenience Endpoint

For initial integration testing, a dedicated endpoint is available that
does not require a patient ID — it uses a fixed de-identified ID
(`forward_patient_00142`) and an RA-specific extraction prompt.

### Upload a PDF (simplest)

```bash
curl -N https://2ndopinionmd.ai/api/timeline/forward/upload \
  -F "file=@patient_timeline.pdf"
```

### Upload EHR JSON

```bash
curl -N https://2ndopinionmd.ai/api/timeline/forward/upload \
  -F "file=@patient_ehr_export.json" \
  -F "format=json"
```

Both default to `store_results=true` and `build_graph=true`.

The general endpoint (`/api/timeline/{patient_id}/infer`) is also available
if you need to specify patient IDs per upload.

---

# 7. Querying the Graph

Once a timeline has been ingested, the knowledge graph is available for
queries via the `/api/graph/` endpoints.  All endpoints use the same
`patient_id` used during upload (e.g. `forward_patient_00142`).

### Full graph export

```bash
curl https://2ndopinionmd.ai/api/graph/forward_patient_00142/full -o graph.json
```

Returns the complete knowledge graph as JSON — every event, edge, arc,
and metadata field.  Use this to pull the entire dataset for downstream
analysis, visualisation, or import into another system.

### Graph snapshot (lightweight overview)

```bash
curl https://2ndopinionmd.ai/api/graph/forward_patient_00142/snapshot | python3 -m json.tool
```

Returns event counts by type, date ranges, and a compact node list.

### Structural topology

```bash
curl https://2ndopinionmd.ai/api/graph/forward_patient_00142/topology
```

Connected components, orphan events, hub events (most connected), temporal
gaps (>90 days), edge type distribution, and graph density.

### Search events

```bash
# All medications
curl "https://2ndopinionmd.ai/api/graph/forward_patient_00142/events?event_type=medication"

# Search by keyword
curl "https://2ndopinionmd.ai/api/graph/forward_patient_00142/events?q=methotrexate"

# Filter by date range
curl "https://2ndopinionmd.ai/api/graph/forward_patient_00142/events?date_from=2020-01-01&date_to=2024-12-31"
```

### Single event + neighbours

```bash
curl https://2ndopinionmd.ai/api/graph/forward_patient_00142/event/dx_001
```

Returns the event detail and all connected events grouped by edge type.

### Priority traversal

```bash
curl "https://2ndopinionmd.ai/api/graph/forward_patient_00142/traverse?seed=dx_001&max_nodes=50"
```

Walks the graph from a seed event following highest-value edges first
(causal > diagnostic > treatment > drug\_response > lab\_trend > temporal).

### Temporal gaps

```bash
curl "https://2ndopinionmd.ai/api/graph/forward_patient_00142/gaps?min_gap_days=60"
```

Periods of silence — often indicating lost-to-follow-up, care transitions,
or extraction gaps.

### Negative space

```bash
curl https://2ndopinionmd.ai/api/graph/forward_patient_00142/negative
```

Expected-but-absent patterns: diagnoses without follow-up labs, medications
without efficacy assessments — the gaps where diagnostic mysteries hide.

### Ask a question (LLM-powered)

```bash
curl -X POST https://2ndopinionmd.ai/api/graph/forward_patient_00142/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What biologic switches has this patient had and why?"}'
```

Sends the question to eoh-llama 8B with graph context and returns a
cited answer.

### Edge list

```bash
# All edges
curl https://2ndopinionmd.ai/api/graph/forward_patient_00142/edges

# Only causal edges
curl "https://2ndopinionmd.ai/api/graph/forward_patient_00142/edges?kind=causal"
```

---

# 8. Quick Reference


### FORWARD endpoint (recommended for testing)

```bash
# PDF
curl -N https://2ndopinionmd.ai/api/timeline/forward/upload \
  -F "file=@TIMELINE.pdf"

# JSON
curl -N https://2ndopinionmd.ai/api/timeline/forward/upload \
  -F "file=@EHR_EXPORT.json" \
  -F "format=json"
```

### General endpoint (per-patient ID)

```bash
# PDF
curl -N https://2ndopinionmd.ai/api/timeline/PATIENT_ID/infer \
  -F "file=@TIMELINE.pdf"

# JSON
curl -N https://2ndopinionmd.ai/api/timeline/PATIENT_ID/infer \
  -F "file=@EHR_EXPORT.json" \
  -F "format=json"
```

### Check GPU status

```bash
curl https://2ndopinionmd.ai/api/timeline/infer/status
```

---

# 9. Security and Privacy

- All inference runs locally on PortalNode hardware. No data is sent to
  external APIs.
- Patient identifiers should be de-identified before upload (use study IDs,
  not names or MRNs).
- The eoh-llama 8B model runs entirely on-premise via Ollama.
- Uploaded files are held in memory during processing and are not persisted
  to disk.
- Extracted events are stored in PostgreSQL only if `store_results=true`.

---

*Questions or issues: dylan@2ndopinionmd.ai*
