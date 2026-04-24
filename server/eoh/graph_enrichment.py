"""
Graph Enrichment Agent

Entity/relationship extraction for PatientTimelineVision.
Supports GPT-4.1 (large-context batches) and Ollama models (small-context batches).

Two modes:
  1. Ingestion enrichment  – heavy, called per PDF batch during ingest
  2. Opportunistic enrichment – lighter, called per detective step at runtime

Model selection:
  - Default INGESTION_MODEL is eoh-llama3.1:8b (stream_config). Set INGESTION_MODEL=gpt-4.1 for premium OpenAI.
  - Ollama models (any name not containing "gpt") use the OLLAMA_BASE_URL and
    smaller batches (~24k chars) to fit within typical 8k–32k token contexts.
"""

from __future__ import annotations

import json
import logging
import os
import textwrap
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from server.api.stream_config import EOH_TIMELINE_SUMMARIZER_MODEL, INGESTION_MODEL, MAX_CONTEXT_CHARS
from server.eoh.patient_timeline_vision import (
    PatientTimelineVision,
    TimelineEventVision,
    _infer_temporal_connascence,
)
from server.llm.llm_client import chat_completion_async, get_ollama_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model selection (INGESTION_MODEL imported from stream_config — single default)
# ---------------------------------------------------------------------------

_OLLAMA_BASE_URL: str = (
    os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
)
# Strip trailing /v1 if present (Ollama's native base is /v1, client adds it)
if _OLLAMA_BASE_URL.lower().endswith("/v1"):
    _OLLAMA_BASE_URL = _OLLAMA_BASE_URL[:-3].rstrip("/")
_OLLAMA_BASE_URL = _OLLAMA_BASE_URL + "/v1"

_USE_OLLAMA: bool = "gpt" not in INGESTION_MODEL.lower()

# ---------------------------------------------------------------------------
# Constants — batch sizing adapts to model context window
# ---------------------------------------------------------------------------

CHARS_PER_TOKEN_ESTIMATE = 4
ENRICHMENT_SYSTEM_PROMPT_TOKENS_RESERVE = 4_000

if _USE_OLLAMA:
    # Ollama models typically support 8k–32k tokens; target 6k input tokens
    ENRICHMENT_OUTPUT_TOKENS = 4_096
    _MODEL_CTX_TOKENS = int(os.getenv("OLLAMA_CTX_TOKENS", "8192"))
    BATCH_MAX_CHARS = int(
        (_MODEL_CTX_TOKENS * 0.75 - ENRICHMENT_SYSTEM_PROMPT_TOKENS_RESERVE - ENRICHMENT_OUTPUT_TOKENS)
        * CHARS_PER_TOKEN_ESTIMATE
    )
    BATCH_MAX_CHARS = max(BATCH_MAX_CHARS, 8_000)  # floor: never below 8k chars
else:
    # GPT-4.1: 1M token context.
    # Fill ratio MUST be low (0.10) so there is output budget for events.
    # Math from timeline_summarizer.py:
    #   GPT-4.1 hard output cap = 32,768 tokens.
    #   Target ~150-180 output tokens per page → max ~180 pages/batch.
    #   0.10 fill → input ≈ (1,048,576 × 0.10 − 6,000 − 32,768) × 4 ≈ 264k input chars ≈ 183 pages.
    # Using 0.60 (old value) crammed 1,650 pages/batch → model returned only ~10 events total.
    GPT41_MAX_CONTEXT_TOKENS = 1_048_576
    ENRICHMENT_CONTEXT_FILL_RATIO = 0.10
    ENRICHMENT_OUTPUT_TOKENS = 32_768
    BATCH_MAX_CHARS = int(
        (
            GPT41_MAX_CONTEXT_TOKENS * ENRICHMENT_CONTEXT_FILL_RATIO
            - ENRICHMENT_SYSTEM_PROMPT_TOKENS_RESERVE
            - ENRICHMENT_OUTPUT_TOKENS
        )
        * CHARS_PER_TOKEN_ESTIMATE
    )

OPPORTUNISTIC_MAX_CHARS = 200_000

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

INGESTION_ENRICHMENT_SYSTEM_PROMPT = textwrap.dedent("""\
You are a clinical timeline graph enrichment agent.

Your task: Extract structured clinical entities and relationships from raw
patient document text to build a PatientTimelineVision graph.

**PHI / PII BOUNDARY (non-negotiable):**
You will frequently receive page text that includes the source EHR's
letterhead banner (patient name, MRN, DOB, address, phone, facility name,
provider names). **Never** copy any of these tokens into ``preview``,
``title``, ``one_line``, ``batch_summary``, ``reason``, or any other text
field you emit. Specifically, if you see:
  - a person's first/last name (patient, family member, or provider)
  - a medical record number (``MRN: ...``, ``MR # ...``, any 6+ digit
    identifier presented as one)
  - a date of birth (``DOB:``, ``born``, ``Date of Birth``)
  - a street address, city + state + ZIP, or phone number
  - a hospital / clinic / facility name used as a location identifier
Treat them as out-of-band metadata and omit them. Summaries must describe
the clinical event only: what happened, to which body system, with which
code (ICD-10, RxNorm, LOINC, SNOMED), on what date. If a preview would
otherwise be empty without the PHI context, return a short clinical
descriptor derived from the event_type and code (e.g.
"Hypertension diagnosis [I10]") instead of quoting the banner.

**Output JSON schema:**
```json
{
  "events": [
    {
      "event_id": "page_<start>_<type>_<seq>",
      "event_type": "diagnosis|lab|medication|procedure|symptom|visit|imaging|flare|note",
      "timestamp": "YYYY-MM-DD or best estimate or empty string",
      "preview": "1-2 sentence human-readable summary of this event",
      "codes": {
        "icd_code":        "I10",
        "icd_description": "Essential (primary) hypertension",
        "drug_name":       "metformin",
        "drug_dosage":     "500 mg PO BID",
        "drug_route":      "oral",
        "drug_status":     "active|held|discontinued",
        "lab_name":        "hemoglobin a1c",
        "lab_value":       "7.2",
        "lab_unit":        "%",
        "lab_flag":        "H|L|HIGH|LOW|A"
      }
    }
  ],
  "edges": [
    {
      "from_id": "event_id_1",
      "to_id": "event_id_2",
      "kind": "temporal|causal|diagnostic|treatment|lab_trend|symptom_cluster",
      "strength": 0.0-1.0,
      "reason": "brief explanation"
    }
  ],
  "batch_summary": "2-3 sentence summary of what this batch covers clinically"
}
```

**CODE INDEX INVARIANT (non-negotiable):**
The graph maintains a flat per-code chronology at
``metadata.code_index`` (buckets: drugs, rxnorm, icd, labs, loinc). The
pipeline keeps this index in sync with event annotations automatically
— but **only for codes it sees**. When you identify a code from the
page text (ICD-10 code, drug generic name + dose + route, lab name +
value + unit), you MUST put it in the event's ``codes`` block above.
Omit the block entirely when no code is present. Do not invent codes.
If you are uncertain about an ICD-10 code, leave it out — an agent
downstream will resolve it from the description.

**Instructions:**
1. Read the document text carefully. Extract ALL clinically relevant events — do not truncate.
2. Assign meaningful event_ids incorporating page numbers for traceability.
3. Infer timestamps where possible from context (dates, relative references).
4. Identify relationships (edges) between events — only high-confidence ones.
5. Be thorough but honest. Do not hallucinate events not present in the text.
6. Include every distinct diagnosis, medication change, procedure, lab result, imaging study,
   and clinical note that contains meaningful medical information.
7. When a code is clearly present in the source text, include it in
   the event's ``codes`` block so the code_index stays authoritative.

**Connascence edge types:**
- temporal: events close in time (within days/weeks)
- causal: one event directly caused another
- diagnostic: lab/symptom supports a diagnosis
- treatment: medication/procedure targets a condition
- lab_trend: same test measured over time
- symptom_cluster: related symptoms forming a pattern
""")

OPPORTUNISTIC_ENRICHMENT_SYSTEM_PROMPT = textwrap.dedent("""\
You are an opportunistic graph enrichment agent.

Given a detective step's findings and the current graph state, you have FOUR jobs:
  1. Identify new clinical events to add.
  2. Identify new structural edges between events.
  3. Identify CAUSAL relationships — the most valuable signal.
  4. Identify CONFOUNDERS — factors that complicate causal attribution.

**PHI / PII BOUNDARY (non-negotiable):**
Never write patient names, family-member names, provider/staff names,
medical record numbers, dates of birth, street addresses, phone numbers,
email addresses, or facility names into any text field you emit
(``preview``, ``mechanism``, ``reason``, ``confounded_relationship``,
``batch_summary``, etc.). Summaries must describe the clinical event
only: what happened, to which body system, with which code, on what date.
If the input text includes an EHR banner, ignore it.

**Output JSON schema:**
```json
{
  "new_events": [
    {
      "event_id": "step_<step_id>_<type>_<seq>",
      "event_type": "diagnosis|lab|medication|procedure|symptom|visit|imaging|flare|note",
      "timestamp": "YYYY-MM-DD or empty",
      "preview": "1-2 sentence summary",
      "codes": {
        "icd_code":    "I10",
        "drug_name":   "metformin",
        "drug_dosage": "500 mg PO BID",
        "drug_route":  "oral",
        "lab_name":    "hemoglobin a1c",
        "lab_value":   "7.2",
        "lab_unit":    "%"
      }
    }
  ],
  "code_updates": [
    {
      "event_id":       "<existing_event_id>",
      "icd_code":       "I50.23",
      "icd_description":"Acute on chronic systolic heart failure",
      "drug_name":      "furosemide",
      "drug_dosage":    "40 mg PO daily",
      "drug_route":     "oral",
      "drug_status":    "active|held|discontinued",
      "lab_name":       "bnp",
      "lab_value":      "1240",
      "lab_unit":       "pg/mL",
      "lab_flag":       "H",
      "reasoning":      "Preview references CHF exacerbation; ICD code inferred from description."
    }
  ],
  "new_edges": [
    {
      "from_id": "event_id_1",
      "to_id": "event_id_2",
      "kind": "temporal|causal|caused_by|confounded_by|diagnostic|treatment|lab_trend|symptom_cluster",
      "strength": 0.0-1.0,
      "reason": "brief explanation"
    }
  ],
  "causal_annotations": [
    {
      "cause_event_id": "existing_or_new_event_id",
      "effect_event_id": "existing_or_new_event_id",
      "mechanism": "1-2 sentence causal explanation (e.g. 'IVIG administered to suppress MG flare; flare resolved within 4 weeks')",
      "confidence": 0.0-1.0
    }
  ],
  "confounder_annotations": [
    {
      "primary_event_id": "the diagnosis/outcome being attributed",
      "confounder_event_id": "the confounding factor event",
      "confounded_relationship": "brief description of which causal claim is confounded",
      "confounder_type": "substance_use|comorbidity|medication_effect|social_determinant|measurement_bias|other",
      "explanation": "1-2 sentence explanation of why this is a confounder (e.g. 'Alcohol use disorder complicates attribution of hepatic injury to medication — both are plausible causes')",
      "confidence": 0.0-1.0
    }
  ],
  "enrichment_note": "1 sentence on what changed"
}
```

**Instructions:**
1. Review the detective step answer and citations carefully.
2. Compare against the existing graph events (provided as context).
3. Add ONLY genuinely new events or edges not already in the graph.
4. Be opportunistic: if nothing new, return empty arrays. That is fine.
5. Do not duplicate existing events. Check event_ids and previews.

**CODE INDEX INVARIANT (non-negotiable):**
The graph maintains a flat per-code chronology at
``metadata.code_index`` (drugs / rxnorm / icd / labs / loinc). It is the
lookup structure 8B traversal agents use for "every time this patient
got X." The pipeline keeps it synced with event annotations via
``code_index_ops.register_code_on_event``, but it can only sync codes
it is told about. Therefore:

  * When you add a **new event** whose source text contains an ICD-10
    code, a drug name (with dose/route if available), or a lab name
    (with value/unit), emit it in the event's ``codes`` block.
  * When you find that an **existing event** is missing a code the
    source text actually contains, append a ``code_updates`` entry
    keyed on that event's ``event_id``. This is how the index learns
    about codes the regex pass missed. Use this for ICD codes
    inferable from a description, generic-name drugs recorded only as
    brand names, labs where a LOINC-mappable name was not extracted.
  * Never invent codes. If you are not certain, leave the field blank
    and note the uncertainty in ``reasoning``. A missing code is fine.
    A wrong code poisons every future lookup.

**CAUSAL ANNOTATION INSTRUCTIONS (critical — do not skip):**
Scan the step answer for causal language:
  - "caused by", "due to", "resulted in", "led to", "secondary to"
  - "in response to", "triggered by", "following", "precipitated by"
  - "improved after", "worsened with", "resolved when", "progressed despite"

For each causal relationship found, add a `causal_annotation` entry:
  - `cause_event_id`: the event that is the cause (use existing graph event_id if present)
  - `effect_event_id`: the event that is the effect (use existing graph event_id if present)
  - `mechanism`: a precise clinical explanation of the causal pathway
  - `confidence`: 0.9 = explicit statement in text, 0.7 = strong clinical inference, 0.5 = reasonable hypothesis

Causal annotations can reference existing graph events OR newly added events.
Even one strong causal annotation is more valuable than ten structural edges.

**CONFOUNDER ANNOTATION INSTRUCTIONS (critical — do not skip):**
Scan the step answer for any factor that makes a causal claim ambiguous or uncertain:
  - Substance use: alcohol use disorder, tobacco, opioids, cannabis — these confound liver, pulmonary, cardiac, and pain attributions
  - Polypharmacy: multiple medications with overlapping effects (e.g. hepatotoxicity from several agents simultaneously)
  - Comorbidities: when two active conditions both explain the same symptom (e.g. fatigue from MG AND from hypothyroidism)
  - Social determinants: housing instability, food insecurity, care access gaps that confound adherence or disease trajectory
  - Measurement bias: lab values affected by timing, hydration, or concurrent illness

For each confounder found, add a `confounder_annotation` entry:
  - `primary_event_id`: the event whose causal attribution is being questioned
  - `confounder_event_id`: the confounding factor (may be an existing diagnosis, substance use event, or social factor)
  - `confounded_relationship`: the specific causal claim being complicated
  - `confounder_type`: one of substance_use|comorbidity|medication_effect|social_determinant|measurement_bias|other
  - `explanation`: why this factor makes the causal claim uncertain, with clinical specifics
  - `confidence`: 0.9 = clearly documented confounder, 0.7 = clinically recognized risk, 0.5 = speculative

Confounders do NOT invalidate causal claims — they contextualize them. The graph is more valuable with honest uncertainty than with false certainty.
""")


# ---------------------------------------------------------------------------
# Ingestion enrichment (heavy — called per PDF batch)
# ---------------------------------------------------------------------------

async def enrich_graph_from_batch(
    batch_text: str,
    page_range: str,
    patient_id: str,
    vision: PatientTimelineVision,
    batch_index: int,
    total_batches: int,
) -> Dict[str, Any]:
    """
    Run the enrichment model on a batch of PDF text to extract entities and relationships.

    Returns enrichment stats dict for logging.
    """
    t0 = time.perf_counter()
    batch_chars = len(batch_text)

    logger.info(
        "GRAPH_ENRICH [batch %d/%d] patient=%s pages=%s chars=%s — calling %s...",
        batch_index + 1, total_batches, patient_id, page_range, f"{batch_chars:,}", INGESTION_MODEL,
    )
    print(
        f"\n{'─'*70}\n"
        f"  GRAPH ENRICHMENT  batch {batch_index+1}/{total_batches}\n"
        f"  patient: {patient_id}  pages: {page_range}\n"
        f"  input chars: {batch_chars:,}  (~{batch_chars // CHARS_PER_TOKEN_ESTIMATE:,} tokens)\n"
        f"{'─'*70}"
    )

    messages = [
        {"role": "system", "content": INGESTION_ENRICHMENT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Patient ID: {patient_id}\n"
                f"Pages: {page_range}\n"
                f"Batch {batch_index+1} of {total_batches}\n\n"
                f"--- DOCUMENT TEXT ---\n{batch_text}"
            ),
        },
    ]

    stats = {
        "batch_index": batch_index,
        "page_range": page_range,
        "input_chars": batch_chars,
        "events_extracted": 0,
        "edges_extracted": 0,
        "code_index_writes": 0,
        "elapsed_ms": 0,
        "error": None,
    }

    try:
        call_kwargs: Dict[str, Any] = dict(
            model=INGESTION_MODEL,
            messages=messages,
            max_tokens=ENRICHMENT_OUTPUT_TOKENS,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        if _USE_OLLAMA:
            call_kwargs["client"] = get_ollama_client(base_url=_OLLAMA_BASE_URL)

        resp = await chat_completion_async(**call_kwargs)

        raw = resp.choices[0].message.content or "{}"
        result = json.loads(raw)

        events_list = result.get("events", [])
        edges_list = result.get("edges", [])
        batch_summary = result.get("batch_summary", "")

        # Deferred import — keeps graph_enrichment importable when
        # code_index_ops is absent in a stripped deployment.
        from server.eoh import code_index_ops

        events_added = 0
        code_index_writes = 0
        for ev in events_list:
            eid = ev.get("event_id", "")
            if not eid:
                continue
            vision.add_event(
                event_id=eid,
                event_type=ev.get("event_type", "note"),
                timestamp=ev.get("timestamp", ""),
                preview=ev.get("preview", ""),
                discovered_by=f"enrich_batch_{batch_index}_{page_range}",
                annotations={
                    "page_range": page_range,
                    "batch_index": batch_index,
                    "enrichment_source": "ingestion",
                },
            )
            events_added += 1

            # Thread the agent-supplied ``codes`` block onto the new
            # event and refresh metadata.code_index in one call so the
            # flat per-code chronology is never stale.
            codes = ev.get("codes") or {}
            if isinstance(codes, dict) and codes:
                try:
                    code_index_ops.register_code_on_event(
                        vision, eid,
                        drug_name=codes.get("drug_name"),
                        drug_dosage=codes.get("drug_dosage"),
                        drug_route=codes.get("drug_route"),
                        drug_status=codes.get("drug_status"),
                        icd_code=codes.get("icd_code"),
                        icd_description=codes.get("icd_description"),
                        lab_name=codes.get("lab_name"),
                        lab_value=codes.get("lab_value"),
                        lab_unit=codes.get("lab_unit"),
                        lab_flag=codes.get("lab_flag"),
                        provenance=f"agent:ingestion:batch{batch_index}",
                    )
                    code_index_writes += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "GRAPH_ENRICH code_index write failed eid=%s: %s",
                        eid, exc,
                    )

        edges_added = 0
        for edge in edges_list:
            from_id = edge.get("from_id", "")
            to_id = edge.get("to_id", "")
            kind = edge.get("kind", "temporal")
            if from_id and to_id and from_id in vision.events and to_id in vision.events:
                vision.add_connascence_link(from_id, to_id, kind)
                edges_added += 1

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        stats.update(
            events_extracted=events_added,
            edges_extracted=edges_added,
            code_index_writes=code_index_writes,
            elapsed_ms=elapsed_ms,
        )

        logger.info(
            "GRAPH_ENRICH [batch %d/%d] DONE — events=%d edges=%d code-index=%d elapsed=%dms summary=%s",
            batch_index + 1, total_batches,
            events_added, edges_added, code_index_writes, elapsed_ms,
            batch_summary[:120],
        )
        print(
            f"  ✓ batch {batch_index+1} enrichment complete\n"
            f"    events extracted: {events_added}\n"
            f"    edges extracted:  {edges_added}\n"
            f"    code-index writes:{code_index_writes}\n"
            f"    elapsed:          {elapsed_ms:,}ms\n"
            f"    summary: {batch_summary[:200]}"
        )

    except json.JSONDecodeError as e:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        stats["elapsed_ms"] = elapsed_ms
        stats["error"] = f"JSON parse error: {e}"
        logger.error("GRAPH_ENRICH [batch %d/%d] JSON parse failed: %s", batch_index + 1, total_batches, e)
        print(f"  ✗ batch {batch_index+1} enrichment JSON parse failed: {e}")

    except Exception as e:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        stats["elapsed_ms"] = elapsed_ms
        stats["error"] = str(e)
        logger.error("GRAPH_ENRICH [batch %d/%d] failed: %s", batch_index + 1, total_batches, e, exc_info=True)
        print(f"  ✗ batch {batch_index+1} enrichment failed: {e}")

    return stats


# ---------------------------------------------------------------------------
# Opportunistic enrichment (lighter — called per detective step)
# ---------------------------------------------------------------------------

async def enrich_graph_opportunistic(
    step_id: str,
    step_question: str,
    step_answer: str,
    step_citations: Optional[List[Dict[str, Any]]],
    patient_id: str,
    vision: PatientTimelineVision,
    *,
    discovered_by_prefix: str = "detective_step",
) -> Dict[str, Any]:
    """
    Lightweight enrichment after a detective step (or timeline summarizer pass) completes.

    `discovered_by_prefix` is joined with `step_id` for event provenance, e.g.
    `detective_step` + `s3` -> `detective_step_s3`; `timeline_summarizer` + `single_pass`.

    Returns enrichment stats dict.
    """
    t0 = time.perf_counter()

    existing_event_ids = list(vision.events.keys())[:200]
    existing_previews = [
        f"{eid}: {vision.events[eid].preview[:80]}"
        for eid in existing_event_ids[:100]
    ]

    citations_text = ""
    if step_citations:
        parts = []
        for c in step_citations[:20]:
            title = c.get("title", "")
            snippet = c.get("snippet", c.get("text", ""))[:400]
            parts.append(f"- {title}: {snippet}")
        citations_text = "\n".join(parts)

    answer_trimmed = (step_answer or "")[:OPPORTUNISTIC_MAX_CHARS]

    user_content = (
        f"Patient ID: {patient_id}\n"
        f"Detective step: {step_id}\n"
        f"Question: {step_question}\n\n"
        f"--- STEP ANSWER ---\n{answer_trimmed}\n\n"
        f"--- CITATIONS ---\n{citations_text}\n\n"
        f"--- EXISTING GRAPH EVENTS (sample) ---\n"
        + "\n".join(existing_previews)
    )

    logger.info(
        "GRAPH_ENRICH_OPPO step=%s patient=%s existing_events=%d input_chars=%d",
        step_id, patient_id, len(vision.events), len(user_content),
    )
    print(
        f"\n  ⚡ Opportunistic enrichment — step {step_id}\n"
        f"     existing graph events: {len(vision.events)}  edges: {vision.count_edges()}"
    )

    stats = {
        "step_id": step_id,
        "events_before": len(vision.events),
        "edges_before": vision.count_edges(),
        "events_added": 0,
        "edges_added": 0,
        "causal_annotations_added": 0,
        "confounder_annotations_added": 0,
        "code_index_writes": 0,
        "code_updates_applied": 0,
        "elapsed_ms": 0,
        "error": None,
    }

    try:
        resp = await chat_completion_async(
            model=EOH_TIMELINE_SUMMARIZER_MODEL,
            messages=[
                {"role": "system", "content": OPPORTUNISTIC_ENRICHMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=4096,
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        raw = resp.choices[0].message.content or "{}"
        result = json.loads(raw)

        new_events = result.get("new_events", [])
        new_edges = result.get("new_edges", [])
        code_updates = result.get("code_updates", [])
        causal_annotations = result.get("causal_annotations", [])
        confounder_annotations = result.get("confounder_annotations", [])
        note = result.get("enrichment_note", "")

        # Deferred import — avoids a circular import at module load.
        from server.eoh import code_index_ops

        events_added = 0
        code_index_writes = 0
        for ev in new_events:
            eid = ev.get("event_id", "")
            if not eid or eid in vision.events:
                continue
            vision.add_event(
                event_id=eid,
                event_type=ev.get("event_type", "note"),
                timestamp=ev.get("timestamp", ""),
                preview=ev.get("preview", ""),
                discovered_by=f"{discovered_by_prefix}_{step_id}",
                annotations={"enrichment_source": "opportunistic", "step_id": step_id},
            )
            events_added += 1

            # If the agent emitted a "codes" block on this new event,
            # write it through register_code_on_event so the flat
            # metadata.code_index stays in sync with the event's
            # annotations.  Same contract applies for ingestion.
            codes = ev.get("codes") or {}
            if isinstance(codes, dict) and codes:
                try:
                    code_index_ops.register_code_on_event(
                        vision, eid,
                        drug_name=codes.get("drug_name"),
                        drug_dosage=codes.get("drug_dosage"),
                        drug_route=codes.get("drug_route"),
                        drug_status=codes.get("drug_status"),
                        icd_code=codes.get("icd_code"),
                        icd_description=codes.get("icd_description"),
                        lab_name=codes.get("lab_name"),
                        lab_value=codes.get("lab_value"),
                        lab_unit=codes.get("lab_unit"),
                        lab_flag=codes.get("lab_flag"),
                        provenance=f"agent:ogre:{step_id}",
                    )
                    code_index_writes += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "GRAPH_ENRICH_OPPO code_index write (new event) failed eid=%s: %s",
                        eid, exc,
                    )

        # ``code_updates`` attaches codes the agent found on EXISTING
        # events (typically ones whose heuristic extractor missed the
        # code, e.g. ICD inferable from description or generic name
        # recorded only as a brand name).
        code_updates_applied = 0
        for upd in code_updates or []:
            eid = (upd or {}).get("event_id", "")
            if not eid or eid not in vision.events:
                continue
            try:
                rep = code_index_ops.register_code_on_event(
                    vision, eid,
                    drug_name=upd.get("drug_name"),
                    drug_dosage=upd.get("drug_dosage"),
                    drug_route=upd.get("drug_route"),
                    drug_status=upd.get("drug_status"),
                    icd_code=upd.get("icd_code"),
                    icd_description=upd.get("icd_description"),
                    lab_name=upd.get("lab_name"),
                    lab_value=upd.get("lab_value"),
                    lab_unit=upd.get("lab_unit"),
                    lab_flag=upd.get("lab_flag"),
                    provenance=f"agent:ogre:{step_id}",
                )
                if rep.get("applied"):
                    code_updates_applied += 1
                    code_index_writes += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "GRAPH_ENRICH_OPPO code_index update failed eid=%s: %s",
                    eid, exc,
                )

        edges_added = 0
        for edge in new_edges:
            from_id = edge.get("from_id", "")
            to_id = edge.get("to_id", "")
            kind = edge.get("kind", "temporal")
            if from_id and to_id and from_id in vision.events and to_id in vision.events:
                vision.add_edge(
                    source_event_id=from_id,
                    target_event_id=to_id,
                    connascence_type=kind,
                    strength=float(edge.get("strength", 1.0)),
                    discovered_by=f"{discovered_by_prefix}_{step_id}",
                    metadata={"reason": edge.get("reason", "")},
                )
                edges_added += 1

        # Causal annotations: directional cause→effect edges on existing/new events
        causal_added = 0
        for ann in causal_annotations:
            cause_id = ann.get("cause_event_id", "")
            effect_id = ann.get("effect_event_id", "")
            mechanism = ann.get("mechanism", "")
            confidence = float(ann.get("confidence", 0.7))
            if not (cause_id and effect_id):
                continue
            if cause_id not in vision.events or effect_id not in vision.events:
                logger.debug(
                    "GRAPH_ENRICH_OPPO causal_annotation skipped (event not in graph): "
                    "cause=%s effect=%s", cause_id, effect_id,
                )
                continue
            # Directional: cause event gets "caused_by" annotation pointing to effect;
            # effect event gets reverse "effect_of" annotation. Both are stored as edges.
            vision.add_edge(
                source_event_id=cause_id,
                target_event_id=effect_id,
                connascence_type="caused_by",
                strength=confidence,
                discovered_by=f"{discovered_by_prefix}_{step_id}",
                metadata={"mechanism": mechanism, "confidence": confidence},
            )
            # Store mechanism text directly on the cause event for retrieval
            if cause_id in vision.events:
                vision.events[cause_id].annotations.setdefault("causal_mechanisms", []).append(
                    {"effect": effect_id, "mechanism": mechanism, "confidence": confidence,
                     "step_id": step_id}
                )
            causal_added += 1

        # Confounder annotations: confounded_by edges + confounder metadata on primary event
        confounders_added = 0
        for ann in confounder_annotations:
            primary_id = ann.get("primary_event_id", "")
            confounder_id = ann.get("confounder_event_id", "")
            explanation = ann.get("explanation", "")
            confounded_rel = ann.get("confounded_relationship", "")
            confounder_type = ann.get("confounder_type", "other")
            confidence = float(ann.get("confidence", 0.7))
            if not (primary_id and confounder_id):
                continue
            if primary_id not in vision.events or confounder_id not in vision.events:
                logger.debug(
                    "GRAPH_ENRICH_OPPO confounder_annotation skipped (event not in graph): "
                    "primary=%s confounder=%s", primary_id, confounder_id,
                )
                continue
            vision.add_edge(
                source_event_id=primary_id,
                target_event_id=confounder_id,
                connascence_type="confounded_by",
                strength=confidence,
                discovered_by=f"{discovered_by_prefix}_{step_id}",
                metadata={
                    "confounded_relationship": confounded_rel,
                    "confounder_type": confounder_type,
                    "explanation": explanation,
                    "confidence": confidence,
                },
            )
            # Store confounder detail directly on the primary event for retrieval
            if primary_id in vision.events:
                vision.events[primary_id].annotations.setdefault("confounders", []).append(
                    {
                        "confounder_event_id": confounder_id,
                        "confounder_type": confounder_type,
                        "confounded_relationship": confounded_rel,
                        "explanation": explanation,
                        "confidence": confidence,
                        "step_id": step_id,
                    }
                )
            confounders_added += 1

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        stats.update(
            events_added=events_added,
            edges_added=edges_added + causal_added + confounders_added,
            causal_annotations_added=causal_added,
            confounder_annotations_added=confounders_added,
            code_index_writes=code_index_writes,
            code_updates_applied=code_updates_applied,
            elapsed_ms=elapsed_ms,
        )

        logger.info(
            "GRAPH_ENRICH_OPPO step=%s DONE +%d events +%d edges +%d causal +%d confounders "
            "+%d code-index writes (%d agent code_updates) (%dms) — %s",
            step_id, events_added, edges_added, causal_added, confounders_added,
            code_index_writes, code_updates_applied, elapsed_ms, note[:120],
        )
        print(
            f"     ✓ +{events_added} events  +{edges_added} edges  "
            f"+{causal_added} causal  +{confounders_added} confounders  "
            f"+{code_index_writes} code-index ({elapsed_ms:,}ms)\n"
            f"     note: {note[:200]}"
        )

    except Exception as e:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        stats["elapsed_ms"] = elapsed_ms
        stats["error"] = str(e)
        logger.error("GRAPH_ENRICH_OPPO step=%s failed: %s", step_id, e, exc_info=True)
        print(f"     ✗ enrichment failed: {e}")

    return stats


# ---------------------------------------------------------------------------
# Utility: compute dynamic batch boundaries from page list
# ---------------------------------------------------------------------------

def compute_batch_boundaries(
    pages: List[tuple],
    max_chars: int = BATCH_MAX_CHARS,
) -> List[List[tuple]]:
    """
    Group (page_num, text) tuples into batches that each fit within max_chars.

    Returns list of batches, each batch is a list of (page_num, text) tuples.
    """
    batches: List[List[tuple]] = []
    current_batch: List[tuple] = []
    current_chars = 0

    for page_num, text in pages:
        page_chars = len(text)
        if current_chars + page_chars > max_chars and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_chars = 0
        current_batch.append((page_num, text))
        current_chars += page_chars

    if current_batch:
        batches.append(current_batch)

    return batches
