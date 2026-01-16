from __future__ import annotations

import json
import logging
import math
import os
import textwrap
from dataclasses import dataclass
from typing import Any, Dict, List
from inspect import iscoroutine
from openai import AsyncOpenAI, OpenAI
import random
import re
import hashlib
import anyio
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional, Tuple, Union

from collections import Counter, defaultdict

from server.api.stream_config import (
    EOH_TIMELINE_SUMMARIZER_SYSTEM_PROMPT,
    EOH_TIMELINE_SUMMARIZER_MODEL,
    EOH_TIMELINE_RAG_SUMMARY_ENABLED,
    EOH_TIMELINE_PROBE_SYSTEM_PROMPT,
    EOH_TIMELINE_GAP_RETRIEVAL_SYSTEM_PROMPT,
)

from server.api.eoh_gap_retrieval import (
    EOH_GAP_RETRIEVAL_SYSTEM_PROMPT,
    build_eoh_gap_retrieval_payload,
    build_compact_context_for_gap,
)

from server.llm.llm_client import chat_completion_async as _llm_chat_completion_async, embedding_async, get_async_openai_client
from server.timeline.embedding_cache import get_cached_query_embedding, put_cached_query_embedding

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class SnapshotEvent:
    ts: str
    event_type: str
    preview: str

@dataclass
class StructuredProbeSnapshot:
    patient_id: str
    counts: Dict[str, int]
    dx_examples: List[SnapshotEvent]
    lab_examples: List[SnapshotEvent]
    note_examples: List[SnapshotEvent]

logger = logging.getLogger(__name__)

_openai_client = OpenAI(timeout=60.0)


class DateTimeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime and date objects."""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


@dataclass
class TimelineSummaries:
    """
    Canonical LLM-facing timeline summaries.

    - timeline_summary: primary longitudinal story used by router, EoH, etc.
    - meds_and_labs_snapshot: human-readable meds/labs snapshot for context.
    - valyu_summary: compact, search-oriented signal list for Valyu queries.
    """
    timeline_summary: str = ""
    meds_and_labs_snapshot: str = ""
    valyu_summary: str = ""



# ---------------------------------------------------------------------------
# Tuning knobs
# ---------------------------------------------------------------------------

# Default max tokens for a *single* summarizer call.
DEFAULT_MAX_TOKENS = 1024

# Hard cap on how much raw timeline text we ever include in a "fallback" summary.
FALLBACK_MAX_CHARS = 120_000

# If the timeline is shorter than this many characters, we do a single-pass summary.
SINGLE_PASS_CHAR_THRESHOLD = 80_000

# For very large timelines, we chunk into ~this many characters per segment.
CHUNK_TARGET_CHAR_LEN = 40_000

# Max number of chunks we’ll map over before we start aggressively merging.
MAX_CHUNKS = 10

# Map step: keep chunk-level summaries tight, so we can afford a nice reduce.
MAP_STEP_MAX_TOKENS = 1024

# Max size of any canonical summary string we hand downstream (router, Valyu, etc.)
SUMMARY_MAX_CHARS = 40_000

# ---------------------------------------------------------------------------
# Timeline RAG / probe knobs
# ---------------------------------------------------------------------------

# Model used for probe LLM (TS/ANN term generation); default to summarizer model.
TIMELINE_PROBE_MODEL = os.getenv(
    "EOH_TIMELINE_PROBE_MODEL",
    EOH_TIMELINE_SUMMARIZER_MODEL,
)

# Embedding model used for timeline ANN queries.
TIMELINE_EMBEDDING_MODEL = os.getenv(
    "TIMELINE_EMBEDDING_MODEL",
    "text-embedding-3-small",
)

# Probe term limits
TIMELINE_PROBE_MAX_TS_TERMS = 12
TIMELINE_PROBE_MAX_ANN_QUERIES = 6

# Gap term limits
TIMELINE_GAP_MAX_SLOTS = 12

# How many TS/ANN rows we try to pull *before* char-budget trimming.
TIMELINE_TS_LIMIT_PER_TERM = 16
TIMELINE_ANN_LIMIT_PER_QUERY = 12

# Hard cap on number of fused timeline docs before formatting.
TIMELINE_MAX_DOCS = 96

# --- ANN Library pre-signal (run before probe) ----------------------------
TIMELINE_ANN_LIBRARY_PREPROBE_ENABLED = True
TIMELINE_ANN_LIBRARY_PREPROBE_MAX_QUERIES = 10     # keep small (6–12 ideal)
TIMELINE_ANN_LIBRARY_PREPROBE_PER_QUERY_LIMIT = 4  # top rows per query
TIMELINE_ANN_LIBRARY_PREPROBE_MAX_ROWS = 24        # total rows after dedupe
TIMELINE_ANN_LIBRARY_PREPROBE_MAX_CHARS = 6_000    # block size added to probe context

NOTE_TABLE = "text.mimiciv_notes_resolved"
NOTE_KEY_COLUMN = "note_id"
NOTE_TEXT_COLUMN = "note_text"

PREFERRED_NOTE_DOMAINS = (
    "Discharge summary",
    "Physician",
    "Nursing",
    "Radiology",
    "ECG",
    "Echo",
)

# Pick your embedding model consistently for timeline ANN
EOH_TIMELINE_ANN_EMBED_MODEL = os.getenv("EOH_TIMELINE_ANN_EMBED_MODEL", "text-embedding-3-small").strip()

def _norm_query(s: str) -> str:
    # normalize whitespace only; do NOT lowercase (can change biomedical acronyms sometimes)
    return " ".join((s or "").strip().split())

def _sha256(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()

# --- ANN pre-probe suite (high-signal, should land across MIMIC patients) ---
TIMELINE_PREPROBE_SUITE_TOP_K = 8
TIMELINE_PREPROBE_SUITE_MAX_QUERIES = 5
TIMELINE_PREPROBE_SUITE_MAX_UNIQUE_ROWS = 20
TIMELINE_PREPROBE_SUITE_MAX_CHARS = 5000

TIMELINE_PREPROBE_SUITE_QUERIES: List[str] = [
    "Identify major phases in this patient’s course over time (baseline → flares → remissions). For each phase, cite key diagnoses and lab signatures.",
    "Establish the patient’s baseline clinical state and baseline labs, then identify deviations that suggest flare windows.",
    "Map evidence for organ-system involvement over time (renal, hepatic, hematologic, pulmonary, cardiac). Cite the strongest signals.",
    "Characterize inflammation and anemia patterns over time; consider iron deficiency vs chronic inflammation vs mixed, citing supporting labs/events.",
    "What key evidence is missing (meds, note bodies, imaging reports), and how should the detective workflow degrade gracefully while staying evidence-anchored?",
]

# ---------------------------
# ANN Library (>= 30 entries)
# ---------------------------
ANN_LIBRARY: Dict[str, Dict[str, Any]] = {
    # CTD / autoimmune landscape
    "ctd_overview": {
        "query": "Longitudinal connective tissue disease evolution with competing diagnoses and shifting phenotype over time.",
        "when": "Use for big-picture CTD arc and competing labels (MCTD/SLE/SSc/RA/overlap).",
        "tags": ["autoimmune", "ctd", "diagnostic_landscape"],
    },
    "mctd_overlap": {
        "query": "Mixed connective tissue disease / overlap syndrome pattern: Raynaud, ILD, myositis, arthritis, scleroderma features.",
        "when": "Use when MCTD/overlap is suspected or labeled; pulls cross-system signature rows.",
        "tags": ["mctd", "overlap", "ctd"],
    },
    "sle_activity": {
        "query": "Systemic lupus erythematosus activity pattern: flares vs remission, serologies, cytopenias, renal involvement, steroids.",
        "when": "Use when SLE is on the table; good for flare signatures and multi-organ patterns.",
        "tags": ["sle", "flare", "ctd"],
    },
    "scleroderma_ild": {
        "query": "Systemic sclerosis phenotype with interstitial lung disease progression and cardiopulmonary complications over time.",
        "when": "Use when scleroderma/SSc or ILD/fibrosis dominates; helps surface PFT/CT/oxygen notes.",
        "tags": ["scleroderma", "ild", "pulmonary"],
    },
    "ra_trajectory": {
        "query": "Rheumatoid arthritis trajectory with inflammatory activity, anemia of chronic disease, and treatment escalation over time.",
        "when": "Use when RA is competing/dominant; often finds chronic inflammation + DMARD patterns.",
        "tags": ["ra", "inflammation", "treatment"],
    },

    # Pulmonary
    "ild_progression": {
        "query": "Interstitial lung disease progression: worsening dyspnea, imaging fibrosis, oxygen needs, PFT decline, hospitalizations.",
        "when": "Use for any ILD/fibrosis/pulm trajectory. Great for notes not containing 'ILD' explicitly.",
        "tags": ["pulmonary", "ild"],
    },
    "pulm_htn_right_heart": {
        "query": "Pulmonary hypertension / right heart strain in autoimmune disease: echo changes, RV failure, hypoxemia trajectory.",
        "when": "Use when PH is suspected or oxygenation + echo findings show up intermittently.",
        "tags": ["pulmonary", "ph", "cardiac"],
    },
    "ards_respiratory_failure": {
        "query": "Acute respiratory decompensation episodes: ARDS, intubation, high-flow oxygen, ICU-level respiratory failure.",
        "when": "Use to catch acute crises even if ICU events are sparse or mislabeled.",
        "tags": ["pulmonary", "icu", "acute"],
    },

    # Renal
    "renal_decline": {
        "query": "Renal function decline over time: rising creatinine, AKI episodes, proteinuria/hematuria, nephritis concern.",
        "when": "Use when renal involvement is possible; finds lab clusters + note context.",
        "tags": ["renal", "aki", "labs"],
    },
    "glomerulonephritis_signal": {
        "query": "Autoimmune glomerulonephritis / nephritis signal: active urine sediment, complement/autoantibodies, edema, hypertension.",
        "when": "Use when nephritis is suspected but not consistently coded.",
        "tags": ["renal", "nephritis", "ctd"],
    },

    # Hematologic
    "cytopenias": {
        "query": "Autoimmune cytopenias pattern: chronic anemia, thrombocytopenia or thrombocytosis, leukopenia, transfusions.",
        "when": "Use when anemia/cytopenias dominate and you need longitudinal characterization.",
        "tags": ["heme", "anemia", "labs"],
    },
    "hemolysis_thrombotic": {
        "query": "Hemolysis or thrombotic microangiopathy concern: falling hemoglobin, hemolysis labs, schistocytes, platelet shifts.",
        "when": "Use if anemia is complex or abrupt with platelet dynamics.",
        "tags": ["heme", "tma", "labs"],
    },

    # Hepatic / GI
    "transaminitis_pattern": {
        "query": "Liver enzyme elevation pattern over time: transaminitis episodes, cholestasis, drug-induced liver injury concern.",
        "when": "Use when AST/ALT/ALP/bili move; catches med-toxicity narrative in notes.",
        "tags": ["hepatic", "labs", "toxicity"],
    },
    "gi_dysmotility_malabsorption": {
        "query": "GI involvement in connective tissue disease: dysmotility, reflux, malabsorption, weight loss, diarrhea/constipation.",
        "when": "Use for systemic sclerosis GI or nonspecific chronic GI trajectories.",
        "tags": ["gi", "ctd"],
    },

    # Neuro / MSK
    "myositis_signal": {
        "query": "Inflammatory myopathy / myositis signal: proximal weakness, CK elevation, EMG/biopsy references, steroid response.",
        "when": "Use when weakness/CK/myositis is in differential.",
        "tags": ["msk", "myositis", "labs"],
    },
    "arthritis_synovitis": {
        "query": "Inflammatory arthritis pattern: synovitis, joint pain/swelling, morning stiffness, erosive disease discussions.",
        "when": "Use when arthritis is prominent but not consistently coded.",
        "tags": ["msk", "arthritis"],
    },

    # Vasculitis / thrombosis
    "vasculitis_signal": {
        "query": "Systemic vasculitis concern: purpura, neuropathy, renal/pulm involvement, ANCA references, steroid pulses.",
        "when": "Use when vasculitis is a plausible alternative/overlap.",
        "tags": ["vasculitis", "overlap"],
    },
    "thrombosis_aps": {
        "query": "Thrombosis / antiphospholipid syndrome signal: recurrent clots, miscarriages, anticoagulation, stroke/PE/DVT mentions.",
        "when": "Use if clotting/anticoag is present or unexplained events exist.",
        "tags": ["aps", "thrombosis", "treatment"],
    },

    # Infection / immunosuppression risk
    "immunosupp_infection": {
        "query": "Infection risk under chronic immunosuppression: recurrent pneumonias, opportunistic infections, sepsis evaluations.",
        "when": "Use to separate flare vs infection and highlight treatment risk accumulation.",
        "tags": ["infection", "immunosuppression", "risk"],
    },
    "steroid_complications": {
        "query": "Chronic corticosteroid exposure complications: osteoporosis, diabetes, adrenal suppression, infections, myopathy.",
        "when": "Use when steroids appear repeatedly or complications are suspected.",
        "tags": ["steroids", "risk"],
    },

    # Treatment / meds
    "dmard_biologic_changes": {
        "query": "Immunosuppressive therapy changes over time: DMARD escalation, biologic switches, toxicity, adherence issues.",
        "when": "Use for treatment arc; often finds med lists and narrative decisions in notes.",
        "tags": ["treatment", "dmard", "biologic"],
    },
    "cyclophosphamide_rituximab": {
        "query": "High-intensity immunosuppression episodes: cyclophosphamide, rituximab, pulse steroids, induction/maintenance patterns.",
        "when": "Use if severe disease is suspected; catches high-signal therapy rows.",
        "tags": ["treatment", "high_intensity"],
    },

    # Trajectory / timeline windows
    "early_onset_context": {
        "query": "Early disease onset narrative: initial symptoms, first diagnoses, earliest organ involvement, baseline function.",
        "when": "Use when early story is missing; good for anchoring arc (start-of-timeline).",
        "tags": ["timeline_window", "early"],
    },
    "midcourse_inflections": {
        "query": "Mid-course inflection points: hospitalizations, rapid phenotype shift, new organ involvement, major therapy changes.",
        "when": "Use for mid-timeline mystery building and arc shaping.",
        "tags": ["timeline_window", "mid"],
    },
    "late_course_current_state": {
        "query": "Late-course/current state: dominant active problems now, cumulative organ damage, recent decompensations, current risks.",
        "when": "Use when summary needs stronger 'where we are now' grounding.",
        "tags": ["timeline_window", "late"],
    },

    # Notes-centric retrieval helpers
    "discharge_summary_signal": {
        "query": "Discharge summary / progress note narrative that summarizes recent hospitalization course and active problems.",
        "when": "Use when notes are rich but labels are sparse; finds summarizing note passages.",
        "tags": ["notes", "hospital_course"],
    },
    "problem_list_active_issues": {
        "query": "Active problem list discussions and assessment/plan sections describing dominant issues and working diagnoses.",
        "when": "Use to pull A/P style note text that’s high-yield for differential + risks.",
        "tags": ["notes", "problem_list"],
    },

    # Labs/trends
    "inflammation_trend": {
        "query": "Inflammatory marker trajectory: CRP/ESR trends, fever/inflammation clusters, flare-like patterns over time.",
        "when": "Use when distinguishing flare vs noise needs longitudinal lab grounding.",
        "tags": ["labs", "inflammation", "flare"],
    },
    "autoantibody_serology": {
        "query": "Autoimmune serology over time: ANA, dsDNA, ENA panel, RF/CCP, complements, ANCA; how results cluster.",
        "when": "Use when diagnostic labels need serology support or discordance exploration.",
        "tags": ["labs", "serology", "diagnostic_landscape"],
    },

    # Cardiac
    "pericarditis_myocarditis": {
        "query": "Autoimmune cardiac involvement: pericarditis, myocarditis, chest pain with inflammatory features, effusions.",
        "when": "Use if chest pain/effusions appear or CTD cardiac involvement is plausible.",
        "tags": ["cardiac", "autoimmune"],
    },

    # Skin / Raynaud
    "raynaud_digital_ulcers": {
        "query": "Raynaud phenomenon and digital ischemia/ulcers over time with systemic sclerosis overlap concern.",
        "when": "Use when Raynaud/ischemia clues exist but are inconsistently coded.",
        "tags": ["skin", "scleroderma", "overlap"],
    },

    # “Mystery / discordance” helpers
    "discordance_labels_vs_course": {
        "query": "Discordance between diagnostic labels and longitudinal course: what features do not fit the working diagnosis?",
        "when": "Use specifically for detective 'mystery' steps and alternative hypotheses.",
        "tags": ["mystery", "diagnostic_landscape"],
    },
    "malignancy_mimic": {
        "query": "Malignancy or hematologic disorder mimicking rheumatologic disease: unexplained cytopenias, weight loss, fevers, LDH.",
        "when": "Use if there are persistent unexplained systemic findings or anemia patterns.",
        "tags": ["mystery", "heme", "onc"],
    },
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass
class RagBudget:
    max_rows: int
    max_chars: int
    max_ts_terms: int
    max_ann_queries: int

def compute_remaining_gap_budget(
    *,
    budget: RagBudget,
    probe_ts_terms: list[str],
    probe_ann_queries: list[str],
    current_rows: list[dict],
    current_ctx_chars: int,
) -> RagBudget:
    used_ts = len([t for t in probe_ts_terms if (t or "").strip()])
    used_ann = len([a for a in probe_ann_queries if (a or "").strip()])
    used_rows = len(current_rows)

    return RagBudget(
        max_rows=max(0, budget.max_rows - used_rows),
        max_chars=max(0, budget.max_chars - current_ctx_chars),
        max_ts_terms=max(0, budget.max_ts_terms - used_ts),
        max_ann_queries=max(0, budget.max_ann_queries - used_ann),
    )


async def chat_completion_async(*args, **kwargs):
    """
    Backwards-compatible wrapper:
    - supports _chat_completion_async({...kwargs...}) older call sites
    - supports keyword-only calls
    """
    if args:
        if len(args) == 1 and isinstance(args[0], dict) and not kwargs:
            kwargs = args[0]
        else:
            raise TypeError("chat_completion_async expects keyword args or a single dict payload")

    return await _llm_chat_completion_async(**kwargs)


def _norm_event_type(et: Optional[str]) -> str:
    return (et or "").strip().lower()


def _as_dict(maybe: Any) -> Dict[str, Any]:
    """
    Defensive: asyncpg *should* give jsonb as dict, but we also support
    (a) JSON string, (b) None, (c) unexpected types.
    """
    if isinstance(maybe, dict):
        return maybe
    if maybe is None:
        return {}
    if isinstance(maybe, str):
        s = maybe.strip()
        if not s:
            return {}
        try:
            obj = json.loads(s)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}
    return {}


def _ensure_structured_dict(structured: Any) -> Dict[str, Any]:
    """
    Timeline events should carry `structured` as a dict (jsonb).
    But some codepaths may pass a JSON string or None.
    Normalize to dict to prevent snapshot/preview regressions.
    """
    if structured is None:
        return {}
    if isinstance(structured, dict):
        return structured
    if isinstance(structured, (bytes, bytearray)):
        try:
            structured = structured.decode("utf-8", errors="ignore")
        except Exception:
            return {"_raw": repr(structured)}

    if isinstance(structured, str):
        s = structured.strip()
        # If it's JSON, parse it; otherwise keep as raw string.
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
            try:
                obj = json.loads(s)
                return obj if isinstance(obj, dict) else {"_json": obj}
            except Exception:
                return {"_raw": structured}
        return {"_raw": structured}

    # Last resort
    return {"_raw": repr(structured)}


def _pick_slices(events: List[Dict[str, Any]], k: int = 3) -> List[Dict[str, Any]]:
    """Pick k slices across the timeline (early/mid/late)."""
    if not events:
        return []
    n = len(events)
    idxs = sorted(set([
        0,
        n // 2,
        n - 1,
    ]))
    # If you want more than 3, sprinkle random
    while len(idxs) < min(k, n):
        idxs.append(random.randrange(0, n))
        idxs = sorted(set(idxs))
    out = []
    for i in idxs[:k]:
        e = events[i]
        out.append({
            "ts": e.get("ts"),
            "event_type": e.get("event_type"),
            "summary": e.get("summary") or e.get("text") or "",
            "structured_keys": sorted(list((e.get("structured") or {}).keys()))[:30],
        })
    return out

def _lab_signal(lab_events: List[Dict[str, Any]], max_items: int = 20) -> Dict[str, Any]:
    """Return a small set of high-signal labs with abnormal flags / extremes."""
    if not lab_events:
        return {"n": 0, "high_signal": []}

    # You likely already normalize labs into structured: test_name, value, unit, flag, ref range...
    # Grab abnormal flags first, else extremes.
    abnormal = [e for e in lab_events if (e.get("structured") or {}).get("flag")]
    if abnormal:
        chosen = abnormal[:max_items]
    else:
        chosen = lab_events[:max_items]

    def fmt(e: Dict[str, Any]) -> Dict[str, Any]:
        s = e.get("structured") or {}
        return {
            "ts": e.get("ts"),
            "test": s.get("test_name"),
            "value": s.get("value") if s.get("value") is not None else s.get("value_text"),
            "unit": s.get("unit"),
            "flag": s.get("flag"),
            "ref": s.get("reference_range") or {"low": s.get("reference_low"), "high": s.get("reference_high")},
        }

    return {"n": len(lab_events), "high_signal": [fmt(e) for e in chosen]}

def _small_excerpt(text: str, limit: int = 240) -> str:
    if not text:
        return ""
    t = " ".join(text.split())
    return t[:limit] + ("…" if len(t) > limit else "")

def ann_library_for_llm() -> List[Dict[str, Any]]:
    # compact form for prompts / payloads
    out = []
    for k, v in ANN_LIBRARY.items():
        out.append(
            {
                "id": k,
                "query": v["query"],
                "when": v.get("when", ""),
                "tags": v.get("tags", []),
            }
        )
    return out

async def _get_cached_embeddings(
    conn: Any,
    model: str,
    input_norms: List[str],
) -> Dict[str, List[float]]:
    if not input_norms:
        return {}
    rows = await conn.fetch(
        """
        SELECT input_norm, embedding
        FROM ehr.query_embedding_cache
        WHERE model = $1
          AND input_norm = ANY($2::text[])
        """,
        model,
        input_norms,
    )
    # asyncpg + pgvector may return vector as list[float] or as a string representation
    result = {}
    for r in rows:
        emb = r["embedding"]
        # Handle different return types from asyncpg/pgvector
        if isinstance(emb, list) and len(emb) > 0 and isinstance(emb[0], (int, float)):
            # Already a list of numbers
            result[r["input_norm"]] = emb
        elif isinstance(emb, str):
            # String representation like "[0.1,-0.2,...]" - parse it
            try:
                # Remove brackets and split by comma
                emb_cleaned = emb.strip('[]')
                emb_list = [float(x.strip()) for x in emb_cleaned.split(',') if x.strip()]
                result[r["input_norm"]] = emb_list
            except Exception:
                logger.warning(f"Failed to parse embedding string for input_norm={r['input_norm']}")
                continue
        else:
            # Try to convert - might be a vector type from pgvector extension
            try:
                emb_list = list(emb)
                # Check if it looks like a list of numbers (not characters)
                if len(emb_list) > 0 and isinstance(emb_list[0], (int, float)):
                    result[r["input_norm"]] = emb_list
                else:
                    logger.warning(f"Embedding appears to be list of non-numeric types for input_norm={r['input_norm']}")
                    continue
            except Exception:
                logger.warning(f"Unexpected embedding type: {type(emb)} for input_norm={r['input_norm']}")
                continue
    return result


async def _insert_cached_embedding(
    conn: Any,
    model: str,
    input_norm: str,
    input_raw: str,
    embedding: List[float],
) -> None:
    # Convert embedding list to pgvector string literal format
    vec_literal = _to_pgvector_literal(embedding)
    await conn.execute(
        """
        INSERT INTO ehr.query_embedding_cache (model, input_norm, input_raw, embedding)
        VALUES ($1, $2, $3, $4::vector)
        ON CONFLICT (model, input_norm) DO NOTHING
        """,
        model,
        input_norm,
        input_raw,
        vec_literal,
    )


async def embed_queries_with_cache(
    pool: Any,
    queries: List[str],
    model: Optional[str] = None,
) -> Dict[str, List[float]]:
    """
    Returns {input_norm: embedding}. Uses DB cache; batches missing embeddings in one OpenAI call.
    """
    model = (model or EOH_TIMELINE_ANN_EMBED_MODEL).strip()
    normed = [_norm_query(q) for q in queries if _norm_query(q)]
    # preserve order but unique
    seen = set()
    uniq_normed = []
    norm_to_raw: Dict[str, str] = {}
    for raw in queries:
        n = _norm_query(raw)
        if not n or n in seen:
            continue
        seen.add(n)
        uniq_normed.append(n)
        norm_to_raw[n] = raw

    async with pool.acquire() as conn:
        cached = await _get_cached_embeddings(conn, model, uniq_normed)
        missing = [n for n in uniq_normed if n not in cached]

    if missing:
        # One embeddings request for all missing items
        raw_inputs = [norm_to_raw[n] for n in missing]

        def _do_embed():
            return _openai_client.embeddings.create(
                model=model,
                input=raw_inputs,
            )

        resp = await anyio.to_thread.run_sync(_do_embed)
        vectors = [d.embedding for d in resp.data]  # list[list[float]]

        async with pool.acquire() as conn:
            for n, raw, emb in zip(missing, raw_inputs, vectors):
                await _insert_cached_embedding(conn, model, n, raw, list(emb))
                cached[n] = list(emb)

    return cached

def resolve_ann_query_item(item: str) -> Tuple[str, Optional[str]]:
    """
    Returns (resolved_query, library_id_or_none).
    Accepts:
      - "LIB:<id>" -> ANN_LIBRARY[id]["query"]
      - raw string -> itself
    """
    s = (item or "").strip()
    if s.upper().startswith("LIB:"):
        lib_id = s.split(":", 1)[1].strip()
        if lib_id in ANN_LIBRARY:
            return ANN_LIBRARY[lib_id]["query"], lib_id
        # unknown library id; fall back to raw
        return s, None
    return s, None


def filter_out_overlaps(items: List[str], avoid: set) -> List[str]:
    out = []
    for x in items or []:
        nx = _norm_query(x)
        if not nx:
            continue
        if nx in avoid:
            continue
        out.append(x)
    return out

def pick_ann_library_queries_for_question(question: str) -> list[str]:
    """
    Choose a small subset of ANN library queries based on the question.
    No LLM call; just heuristic mapping.
    """
    q = (question or "").lower()

    # You already have TIMELINE_ANN_LIBRARY like:
    # { "ILD_ARC": {"query": "...", "when": "..."} , ... }
    lib = ANN_LIBRARY  # import / reference wherever you defined it

    buckets: list[str] = []

    # Core always-on story builders
    buckets += ["BASELINE_TERRAIN", "LONGITUDINAL_ARC", "DIAGNOSTIC_DRIFT"]

    # If question smells like autoimmune/CTD/RA/SLE/scleroderma
    if any(k in q for k in ["autoimmune", "connective tissue", "ctd", "lupus", "sle", "scler", "rheumatoid", "ra", "sjogren", "mctd"]):
        buckets += ["AUTOIMMUNE_CORE", "FLARE_PATTERN", "IMMUNOSUPPRESSION_RISK"]

    # Organ system hints
    if any(k in q for k in ["lung", "ild", "fibrosis", "pulmonary", "dlco", "ct chest"]):
        buckets += ["PULMONARY_ILD_ARC"]
    if any(k in q for k in ["renal", "creatinine", "gfr", "nephritis", "proteinuria"]):
        buckets += ["RENAL_ARC"]
    if any(k in q for k in ["anemia", "cbc", "platelet", "thrombo", "wbc"]):
        buckets += ["HEMATOLOGIC_ARC"]
    if any(k in q for k in ["liver", "alt", "ast", "bilirubin", "inr"]):
        buckets += ["HEPATIC_ARC"]
    if any(k in q for k in ["gi", "gastro", "diarrhea", "bleed", "malabsorption"]):
        buckets += ["GI_ARC"]

    # Dedup while preserving order
    seen = set()
    chosen_ids = []
    for bid in buckets:
        if bid in lib and bid not in seen:
            chosen_ids.append(bid)
            seen.add(bid)

    # Cap
    chosen_ids = chosen_ids[:TIMELINE_ANN_LIBRARY_PREPROBE_MAX_QUERIES]
    return [lib[x]["query"] for x in chosen_ids]


async def seed_ann_library_embeddings(pool: Any) -> None:
    """
    Ensures all ANN_LIBRARY queries are embedded + cached.
    Safe to call multiple times (idempotent via ON CONFLICT).
    """
    lib_queries = [v["query"] for v in ANN_LIBRARY.values()]
    await embed_queries_with_cache(pool, lib_queries, model=EOH_TIMELINE_ANN_EMBED_MODEL)


async def _search_timeline_ann_for_queries(
    pool: Any,
    patient_id: str,
    ann_queries: List[str],
    per_query_limit: int = 24,
) -> List[Dict[str, Any]]:
    if not ann_queries:
        return []

    # Resolve library ids -> query strings
    resolved_queries: List[str] = []
    for item in ann_queries:
        q, _lib = resolve_ann_query_item(item)
        if _norm_query(q):
            resolved_queries.append(q)

    if not resolved_queries:
        return []

    # Ensure library is seeded (cheap if already cached)
    await seed_ann_library_embeddings(pool)

    # Get embeddings via cache in ONE call for missing items
    emb_map = await embed_queries_with_cache(pool, resolved_queries, model=EOH_TIMELINE_ANN_EMBED_MODEL)

    out: List[Dict[str, Any]] = []
    async with pool.acquire() as conn:
        for q in resolved_queries:
            qn = _norm_query(q)
            q_emb = emb_map.get(qn)
            if not q_emb:
                continue

            # Convert embedding to pgvector string literal
            # Handle both list[float] (from cache) and string (already formatted) cases
            if isinstance(q_emb, str):
                q_emb_literal = q_emb
            elif isinstance(q_emb, list):
                q_emb_literal = _to_pgvector_literal(q_emb)
            else:
                # Try to convert to list first
                try:
                    q_emb_list = list(q_emb)
                    q_emb_literal = _to_pgvector_literal(q_emb_list)
                except Exception:
                    logger.warning(f"Failed to convert embedding to pgvector literal for query {qn[:50]}")
                    continue
            
            # (Your existing ANN SQL; keep unchanged)
            rows = await conn.fetch(
                """
                SELECT id, ts, event_type, text,
                       1 - (embedding <=> $3::vector) AS score
                FROM ehr.patient_timeline
                WHERE patient_id = $1
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> $3::vector
                LIMIT $2
                """,
                patient_id,
                per_query_limit,
                q_emb_literal,
            )

            for r in rows:
                out.append(
                    {
                        "id": str(r["id"]),
                        "ts": r["ts"].isoformat() if hasattr(r["ts"], "isoformat") else str(r["ts"]),
                        "event_type": r["event_type"],
                        "text": (r["text"] or "")[:400],
                        "score": float(r["score"]) if r.get("score") is not None else None,
                        "query": q,
                    }
                )

    return out

async def _build_preprobe_ann_library_signal(
    *,
    pool: Any,
    client: Any,
    patient_id: str,
    question: str,
) -> tuple[list[dict], str]:
    """
    Run a small set of ANN library queries *before* probe, to give the probe LLM
    real, high-yield anchors from the timeline.
    Returns: (rows, formatted_text_block)
    """
    if not TIMELINE_ANN_LIBRARY_PREPROBE_ENABLED:
        return [], ""

    ann_queries = pick_ann_library_queries_for_question(question)
    if not ann_queries:
        return [], ""

    try:
        rows = await _search_timeline_ann_for_queries(
            pool=pool,
            patient_id=patient_id,
            ann_queries=ann_queries,
            per_query_limit=TIMELINE_ANN_LIBRARY_PREPROBE_PER_QUERY_LIMIT,
        )
    except Exception:
        logger.exception("Pre-probe ANN library signal failed; skipping.")
        return [], ""

    if not rows:
        return [], ""

    # Dedupe and cap
    rows = _dedupe_timeline_rows(rows)
    rows = rows[:TIMELINE_ANN_LIBRARY_PREPROBE_MAX_ROWS]

    # Time stratify lightly (optional but helpful): take earliest/mid/latest
    try:
        rows_sorted = sorted(rows, key=lambda r: str(r.get("ts") or ""))
        if len(rows_sorted) > 9:
            third = max(1, len(rows_sorted) // 3)
            rows = rows_sorted[:third] + rows_sorted[third:2*third:2] + rows_sorted[-third:]
            rows = _dedupe_timeline_rows(rows)[:TIMELINE_ANN_LIBRARY_PREPROBE_MAX_ROWS]
        else:
            rows = rows_sorted
    except Exception:
        pass

    # Format
    text = _format_timeline_rows_for_context(
        rows,
        max_chars=TIMELINE_ANN_LIBRARY_PREPROBE_MAX_CHARS,
        label_prefix="ANNLIB",
    )

    block = (
        "=== ANN LIBRARY PRE-SIGNAL (high-yield anchors; may be incomplete) ===\n"
        + text
        + "\n=== END ANN LIBRARY PRE-SIGNAL ===\n"
    )
    return rows, block


def _render_ann_rows_compact(rows: List[Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for r in rows:
        ts = r.get("ts") or ""
        et = r.get("event_type") or ""
        txt = (r.get("text") or "").replace("\n", " ").strip()
        score = r.get("score")
        if len(txt) > 220:
            txt = txt[:220] + "…"
        sfx = f" (score={score:.3f})" if isinstance(score, (float, int)) else ""
        lines.append(f"- [{ts}] {et}: {txt}{sfx}")
    return lines


async def _build_preprobe_ann_suite(
    *,
    pool: Any,
    client: Any,
    patient_id: str,
    question: str,
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Runs a small suite of ANN queries BEFORE calling the probe planner.
    Returns:
      - suite_payload: [{"query": str, "top_k": int, "rows": [...]}]
      - suite_block: markdown string for easy injection / debugging
    """
    queries = TIMELINE_PREPROBE_SUITE_QUERIES[:TIMELINE_PREPROBE_SUITE_MAX_QUERIES]

    suite_payload: List[Dict[str, Any]] = []
    all_rows: List[Dict[str, Any]] = []

    for q in queries:
        # This uses the existing ANN search in this module (already cached + embedded)
        rows = await _search_timeline_ann_for_queries(
            pool=pool,
            patient_id=patient_id,
            ann_queries=[q],
            per_query_limit=TIMELINE_PREPROBE_SUITE_TOP_K,
        )
        # rows returned by search_timeline_ann are typically a flat list of dicts with query included
        # Filter to just this query
        q_rows = [r for r in rows if (r.get("query") == q or r.get("query") is None)]
        q_rows = _dedupe_timeline_rows(q_rows)

        suite_payload.append(
            {
                "query": q,
                "top_k": TIMELINE_PREPROBE_SUITE_TOP_K,
                "rows": [
                    {
                        "id": r.get("id"),
                        "ts": r.get("ts"),
                        "event_type": r.get("event_type"),
                        "text": r.get("text"),
                        "score": r.get("score"),
                    }
                    for r in q_rows
                ],
            }
        )
        all_rows.extend(q_rows)

    # Global dedupe + cap
    all_rows = _dedupe_timeline_rows(all_rows)[:TIMELINE_PREPROBE_SUITE_MAX_UNIQUE_ROWS]

    # Build a compact, query-grouped markdown block for peek_text injection
    parts: List[str] = []
    parts.append("# PRE-PROBE ANN SUITE (Top hits, deduped)")
    for item in suite_payload:
        q = item["query"]
        q_rows = item.get("rows") or []
        # Re-render compact lines from the stored rows
        parts.append(f"\n## Q: {q}")
        parts.extend(_render_ann_rows_compact(q_rows[:TIMELINE_PREPROBE_SUITE_TOP_K]))

    block = "\n".join(parts)
    if len(block) > TIMELINE_PREPROBE_SUITE_MAX_CHARS:
        block = block[:TIMELINE_PREPROBE_SUITE_MAX_CHARS] + "\n…(truncated)\n"

    return suite_payload, block


def _safe_get_choice_content(resp: Any) -> str:
    """
    Extract the .content from the first choice, or return '{}' if missing.
    """
    try:
        return resp.choices[0].message.content or "{}"
    except Exception:
        return "{}"


def _clean_note_preview(raw: str, max_chars: int) -> str:
    """
    Turn raw note_text into a compact, readable preview:
      - collapse whitespace
      - normalize a couple of common headers
      - hard truncate
    """
    import re

    text = (raw or "").strip()
    if not text:
        return ""

    # Collapse whitespace/newlines
    text = re.sub(r"\s+", " ", text)

    # Optional: normalize some patterns
    text = re.sub(r"^INDICATION:\s*", "Indication: ", text, flags=re.IGNORECASE)

    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + " [truncated]"

    return text

def _push_sample(bucket: list, ev: dict, *, max_items: int) -> None:
    if len(bucket) >= max_items:
        return

    et = (bucket.get("event_type") if isinstance(bucket, dict) else getattr(bucket, "event_type", None)) or "unknown"
    structured = _as_dict(ev.get("structured"))
    domain = (structured.get("domain") or structured.get("note_domain") or "").strip()

    # --- LAB preview (robust) ---
    def _fmt_lab(s: Dict[str, Any]) -> str:
        name = (s.get("test_name") or s.get("label") or s.get("item_label") or "Lab").strip()
        name = re.sub(r"\s+", " ", name).strip()
        flag = (s.get("flag") or "").strip()
        unit = (s.get("unit") or s.get("valueuom") or "").strip()

        # try numeric first, then text, then qualitative
        val = s.get("value")
        if val is None or val == "":
            val = s.get("value_text")
        if val is None or val == "":
            val = s.get("qualitative")
        val_str = "" if val is None else str(val).strip()

        core = f"{name} {val_str}".strip()
        if unit:
            core = f"{core} {unit}".strip()
        if flag:
            core = f"{core} (flag={flag})"
        return core

    preview_text = ""
    note_id = ""

    if et == "lab":
        preview_text = _fmt_lab(structured)
    elif et == "diagnosis":
        code = (structured.get("icd_code") or structured.get("code") or "").strip()
        title = (structured.get("title") or structured.get("long_title") or structured.get("label") or "").strip()
        preview_text = " ".join([p for p in [code, title] if p]).strip() or "Diagnosis"
    elif et == "procedure":
        code = (structured.get("icd_code") or structured.get("code") or "").strip()
        title = (structured.get("long_title") or structured.get("title") or structured.get("label") or "").strip()
        preview_text = " ".join([p for p in [code, title] if p]).strip() or "Procedure"
    elif et == "note":
        note_id = (structured.get("note_id") or structured.get("id") or "").strip()
        # keep it short; the formatter will show note_preview specifically
        preview_text = ((structured.get("note_preview") or structured.get("preview") or "")).strip()
        if not preview_text:
            # ultra-safe fallback: first line of note_text if present
            nt = (structured.get("note_text") or "").strip()
            preview_text = nt.splitlines()[0][:240] if nt else ""
    else:
        # keep something stable for unknown types
        preview_text = (structured.get("text") or structured.get("summary") or "").strip()

    payload = {
        "ts": ev.get("ts"),
        "event_type": et or "unknown",
        "domain": domain,
        # >>> THE IMPORTANT FIX <<<
        "text": preview_text,               # used by _format_structured_snapshot_for_context()
        "preview": preview_text,            # keep backward compatibility if anything else used this
    }
    if note_id:
        payload["note_id"] = note_id
        payload["note_preview"] = preview_text  # also used by formatter for notes

    bucket.append(payload)

def _format_structured_snapshot_for_context(
    snapshot: Dict[str, Any],
    max_chars: int = 8000,
) -> str:
    lines: List[str] = []

    # Event type counts
    etc = snapshot.get("event_type_counts") or []
    if etc:
        lines.append("## Event type counts (top)")
        for row in etc[:12]:
            lines.append(f"- {row.get('event_type', 'unknown')}: {row.get('count', 0)}")
        lines.append("")

    def _dump_bucket(label: str, key: str, max_items: int = 8):
        bucket = snapshot.get(key) or []
        if not bucket:
            return

        lines.append(f"## Representative {label}")
        for ev in bucket[:max_items]:
            ts = ev.get("ts") or "unknown time"
            et = (ev.get("event_type") if isinstance(ev, dict) else getattr(ev, "event_type", None)) or "unknown"
            domain = ev.get("domain")

            # Prefer richer preview fields for notes
            txt = (
                ev.get("note_preview")
                or ev.get("text")
                or ""
            ).strip()

            if not txt:
                txt = "[no preview available]"

            if len(txt) > 280:
                txt = txt[:280] + " [truncated]"

            # Convert timestamp to string if it's a datetime object
            if hasattr(ts, 'isoformat'):
                ts_str = ts.isoformat()
            elif isinstance(ts, str):
                ts_str = ts
            else:
                ts_str = str(ts)
            ts_short = ts_str.split("+")[0] if "+" in ts_str else ts_str

            if domain:
                lines.append(f"- [{ts_short}] {et} ({domain}): {txt}")
            else:
                lines.append(f"- [{ts_short}] {et}: {txt}")

        lines.append("")

    _dump_bucket("diagnosis / problem events", "diagnosis_events")
    _dump_bucket("lab events", "lab_events")
    _dump_bucket("ICU / critical care events", "icu_events")
    _dump_bucket("note / narrative events", "note_events")

    meds = snapshot.get("med_events") or []
    if meds:
        lines.append("\n### Recent medications / changes (most recent first)")
        for m in meds[:20]:
            name = m.get("med_name") or m.get("drug") or ""
            dose = m.get("dose") or ""
            route = m.get("route") or ""
            freq = m.get("freq") or ""
            status = m.get("status") or ""
            ts = m.get("ts") or "unknown time"
            # Convert timestamp to string if it's a datetime object
            if hasattr(ts, 'isoformat'):
                ts_str = ts.isoformat()
            elif isinstance(ts, str):
                ts_str = ts
            else:
                ts_str = str(ts)
            lines.append(f"- [{ts_str}] {name} {dose} {route} {freq} ({status})".strip())

    text = "\n".join(lines).strip()
    if len(text) > max_chars:
        text = text[: max_chars] + "\n[structured snapshot truncated]"
    return text


def _extract_json_from_choice(choice) -> Dict[str, Any]:
    # Newer SDKs may expose parsed JSON directly
    parsed = getattr(getattr(choice, "message", None), "parsed", None)
    if parsed is not None:
        return parsed

    raw = choice.message.content or "{}"
    raw = raw.strip()
    return json.loads(raw)


def _decode_timeline_summaries(raw: Dict[str, Any]) -> TimelineSummaries:
    """
    Normalize raw LLM JSON into TimelineSummaries.

    Supports both old and new field names, but strongly favors the new ones:
      - timeline_summary          (new; replaces full_timeline_summary, router_timeline_summary)
      - meds_and_labs_snapshot   (new; replaces meds_labs_snapshot, meds_andlabs_snapshot)
      - valyu_summary            (new; replaces valyu_timeline_summary, query_terms_timeline_summary)
    """
    def _clean(s: Any) -> str:
        if s is None:
            return ""
        if isinstance(s, list):
            # for valyu_summary we may get a list of strings
            return "\n".join(str(x).strip() for x in s if str(x).strip())
        return str(s).strip()

    # --- timeline_summary ---
    timeline_summary = _clean(
        raw.get("timeline_summary")
        or raw.get("full_timeline_summary")
        or raw.get("router_timeline_summary")
    )

    # --- meds_and_labs_snapshot ---
    meds_and_labs_snapshot = _clean(
        raw.get("meds_and_labs_snapshot")
        or raw.get("meds_labs_snapshot")
        or raw.get("meds_andlabs_snapshot")
    )

    # --- valyu_summary ---
    valyu_summary = _clean(
        raw.get("valyu_summary")
        or raw.get("valyu_timeline_summary")
        or raw.get("query_terms_timeline_summary")
    )

    return TimelineSummaries(
        timeline_summary=timeline_summary,
        meds_and_labs_snapshot=meds_and_labs_snapshot,
        valyu_summary=valyu_summary,
    )

def _should_use_rag_timeline_summary(
    total_chars: int,
    patient_id: str | None,
    pool: Any | None,
    enabled_flag: bool,
) -> bool:
    """
    Decide whether to use the probe+RAG path instead of the old hierarchical
    map/reduce summarizer.

    Requirements:
    - Global feature flag is enabled.
    - We have a patient_id and a DB pool (needed to RAG over ehr.patient_timeline).
    - Timeline is "large enough" that we care about optimizing.
    """
    if not enabled_flag:
        return False
    if not patient_id or pool is None:
        return False
    if total_chars <= SINGLE_PASS_CHAR_THRESHOLD:
        # For modest timelines we just use single-pass.
        return False
    return True

def _build_timeline_peek_text(
    timeline_text: str,
    max_chars: int = 16_000,
    n_middle_samples: int = 3,
    sample_span_chars: int = 1_500,
) -> str:
    """
    Build a "peek" over a very large timeline:

    - A slice from the start.
    - A slice from the end.
    - A few random slices from the middle.

    This gives the LLM enough global context to propose TS/ANN search terms and
    to keep a rough sense of chronology, without feeding the full 400k+ chars.
    """

    text = timeline_text.replace("\r\n", "\n")
    total = len(text)
    if total <= max_chars:
        return text

    parts: List[str] = []

    # Start slice
    start_slice = text[: min(4000, total)]
    parts.append("### TIMELINE START SLICE\n" + start_slice.strip() + "\n")

    # End slice
    end_slice = text[max(0, total - 4000) :]
    parts.append("### TIMELINE END SLICE\n" + end_slice.strip() + "\n")

    # Middle random samples
    if total > 10_000 and n_middle_samples > 0:
        middle_start = total // 4
        middle_end = (3 * total) // 4
        if middle_end > middle_start:
            for i in range(n_middle_samples):
                anchor = random.randint(middle_start, middle_end)
                half = sample_span_chars // 2
                lo = max(0, anchor - half)
                hi = min(total, anchor + half)
                snippet = text[lo:hi]
                parts.append(
                    textwrap.dedent(
                        f"""
                        ### TIMELINE RANDOM MIDDLE SAMPLE {i+1}
                        {snippet.strip()}
                        """
                    ).strip()
                    + "\n"
                )

    peek = "\n\n".join(parts).strip()

    # Hard cap if somehow huge
    if len(peek) > max_chars:
        peek = peek[:max_chars]

    return peek


def _preview_lab(s: Dict[str, Any]) -> str:
    name = (s.get("test_name") or s.get("label") or s.get("name") or "").strip()

    # Prefer numeric value, else value_text, else qualitative.
    v = s.get("value")
    vnum = None
    try:
        vnum = float(v) if v is not None and v != "" else None
    except Exception:
        vnum = None

    value_text = (s.get("value_text") or "").strip()
    qualitative = (s.get("qualitative") or "").strip()
    unit = (s.get("unit") or s.get("valueuom") or "").strip()
    flag = (s.get("flag") or "").strip()

    ref = (s.get("reference_range") or "").strip()
    lo = s.get("reference_low")
    hi = s.get("reference_high")
    if not ref and (lo is not None or hi is not None):
        ref = f"{'' if lo is None else lo}–{'' if hi is None else hi}".strip("–")

    parts = []
    if name:
        parts.append(name)

    if vnum is not None:
        parts.append(str(vnum).rstrip("0").rstrip("."))
    elif value_text:
        parts.append(value_text)
    elif qualitative:
        parts.append(qualitative)

    if unit:
        parts.append(unit)

    if flag:
        parts.append(f"(flag={flag})")

    if ref:
        parts.append(f"[ref {ref}]")

    return " ".join(parts).strip() or "[unparsed lab]"


def _preview_event(event_type: str, structured: Any) -> str:
    s = _ensure_structured_dict(structured)

    # diagnoses / procedures
    if event_type in ("diagnosis", "procedure"):
        code = (s.get("icd_code") or s.get("code") or "").strip()
        title = (s.get("title") or s.get("long_title") or s.get("name") or "").strip()
        if code and title:
            return f"{code} — {title}"
        if code:
            return code
        if title:
            return title
        return "[no dx/proc fields]"

    # notes
    if event_type == "note":
        nid = (s.get("note_id") or s.get("id") or "").strip()
        domain = (s.get("domain") or "").strip()
        if nid and domain:
            return f"{domain} note_id={nid}"
        if nid:
            return f"note_id={nid}"
        return "[no note_id]"

    # labs (see formatting fix section below; call into _preview_lab)
    if event_type == "lab":
        return _preview_lab(s)

    return "[no preview available]"


async def _build_structured_probe_snapshot(
    *,
    pool,                # keep keyword-only; matches how you call it
    patient_id: str,
    max_examples_each: int = 8,
) -> StructuredProbeSnapshot:
    # Pull from ehr.patient_timeline by patient_id (NOT by structured->subject_id)
    sql = """
      SELECT ts, event_type, structured
      FROM ehr.patient_timeline
      WHERE patient_id = $1
      ORDER BY ts
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, patient_id)

    counts = Counter((r["event_type"] or "unknown") for r in rows)

    def pick(et: str) -> List[SnapshotEvent]:
        out: List[SnapshotEvent] = []
        for r in rows:
            if (r["event_type"] or "").lower() != et:
                continue
            structured = _as_dict(r["structured"])
            try:
                preview = _preview_event(et, structured)
            except Exception:
                preview = "[no preview available]"
            
            out.append(SnapshotEvent(
                ts=str(r["ts"]),
                event_type=et,
                preview=preview,
            ))
            if len(out) >= max_examples_each:
                break
        return out

    return StructuredProbeSnapshot(
        patient_id=patient_id,
        counts=dict(counts),
        dx_examples=pick("diagnosis"),
        lab_examples=pick("lab"),
        note_examples=pick("note"),
    )

def render_probe_snapshot_md(s: StructuredProbeSnapshot) -> str:
    def fmt_events(title: str, evs: List[SnapshotEvent]) -> str:
        if not evs:
            return f"## {title}\n- (none)\n"
        lines = "\n".join(f"- [{e.ts}] {e.event_type}: {e.preview}" for e in evs)
        return f"## {title}\n{lines}\n"

    top = sorted(s.counts.items(), key=lambda x: x[1], reverse=True)[:10]
    top_lines = "\n".join(f"- {k}: {v}" for k, v in top) if top else "- (none)"

    return (
        "## Event type counts (top)\n"
        f"{top_lines}\n\n"
        f"{fmt_events('Representative diagnosis / problem events', s.dx_examples)}\n"
        f"{fmt_events('Representative lab events', s.lab_examples)}\n"
        f"{fmt_events('Representative note / narrative events', s.note_examples)}\n"
    )


async def _build_meds_and_labs_snapshot(
    *,
    pool: Any,
    patient_id: str,
    max_labs: int = 25,
    max_meds: int = 25,
    lookback_days: int = 365,
) -> str:
    """
    Produce a lightweight meds/labs snapshot for UI + downstream context.

    Design goals:
    - Never empty if labs exist (even if meds are absent in the source timeline).
    - Cheap and robust: bounded row reads, simple formatting.
    """
    if not patient_id:
        return ""

    sql = """
      SELECT ts, event_type, structured
      FROM ehr.patient_timeline
      WHERE patient_id = $1
        AND ts >= (NOW() - ($2::int || ' days')::interval)
        AND lower(event_type) IN ('lab','med','medication','rx','mar')
      ORDER BY ts DESC
      LIMIT 2000
    """
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, patient_id, lookback_days)
    except Exception:
        logger.exception("meds/labs snapshot: query failed")
        return ""

    labs: List[SnapshotEvent] = []
    meds: List[SnapshotEvent] = []

    for r in rows:
        et = (r.get("event_type") or "").lower().strip()
        structured = _as_dict(r.get("structured"))
        preview = _preview_event(et, structured)

        ts_val = r.get("ts")
        ts_str = ts_val.isoformat() if hasattr(ts_val, "isoformat") else str(ts_val)

        ev = SnapshotEvent(ts=ts_str, event_type=et, preview=preview)

        if et == "lab" and len(labs) < max_labs:
            labs.append(ev)
        elif et in ("med", "medication", "rx", "mar") and len(meds) < max_meds:
            meds.append(ev)

        if len(labs) >= max_labs and len(meds) >= max_meds:
            break

    if not labs and not meds:
        return ""

    def fmt(title: str, evs: List[SnapshotEvent]) -> str:
        if not evs:
            return f"## {title}\n- (none)\n"
        return "## " + title + "\n" + "\n".join(
            f"- [{e.ts}] {e.preview}" for e in evs
        ) + "\n"

    header = "## Meds & Labs Snapshot (last ~year, most recent first)\n"
    return (header + "\n" + fmt("Recent medications / therapies (if available)", meds) + "\n" + fmt("Recent labs", labs)).strip()
def build_probe_payload_for_llm(
    patient_id: str,
    span_days: int,
    snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "patient_id": patient_id,
        "span_days": span_days,
        "event_type_counts": snapshot.get("event_type_counts") or [],
        "diagnosis_events": snapshot.get("diagnosis_events") or [],
        "lab_events": snapshot.get("lab_events") or [],
        "icu_events": snapshot.get("icu_events") or [],
        "note_events": snapshot.get("note_events") or [],
    }


async def _call_timeline_probe_llm(
    client: Any,
    question: str,
    peek_text: str,
    structured_snapshot: Dict[str, Any],
    ann_preprobe_suite: Optional[List[Dict[str, Any]]] = None,
    max_ts_terms: int = TIMELINE_PROBE_MAX_TS_TERMS,
    max_ann_queries: int = TIMELINE_PROBE_MAX_ANN_QUERIES,
    max_citations: int = 12,
) -> Dict[str, Any]:
    """
    Use the Timeline Probe Planner LLM to propose:
      - ts_terms (TS search terms),
      - ann_queries (ANN queries),
      - timeline_filters (high-level retrieval buckets),
      - probe_citations (event_ids to highlight as anchor examples).

    The system prompt and JSON schema are defined by
    EOH_TIMELINE_PROBE_SYSTEM_PROMPT in stream_config.
    """

    payload = {
        "question": question,
        "patient_id": structured_snapshot.get("patient_id") or "",
        "timeline_peek": peek_text,
        "structured_probe_snapshot": structured_snapshot,
        "max_ts_terms": max_ts_terms,
        "max_ann_queries": max_ann_queries,
        "max_citations": max_citations,
        "ann_library": ann_library_for_llm(),
        "ann_preprobe_suite": ann_preprobe_suite,
    }

    messages = [
        {"role": "system", "content": EOH_TIMELINE_PROBE_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, cls=DateTimeJSONEncoder)},
    ]

    # Support both AsyncOpenAI and sync OpenAI clients.
    resp = await chat_completion_async(
        client=client,
        model=EOH_TIMELINE_SUMMARIZER_MODEL,
        messages=[
            {"role": "system", "content": EOH_TIMELINE_PROBE_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, cls=DateTimeJSONEncoder)},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},  # if you're using this
    )
    if iscoroutine(resp):
        resp = await resp

    raw = _safe_get_choice_content(resp)
    raw = (raw or "").strip()
    if not raw:
        logger.warning("Timeline probe LLM returned empty content; falling back to heuristics.")
        return {
            "ts_terms": [],
            "ann_queries": [],
            "timeline_filters": [],
            "probe_citations": [],
            "notes": "empty_response_fallback",
        }

    try:
        data = _extract_json_from_choice(resp.choices[0])
        ts_terms = data.get("ts_terms") or []
        ann_queries = data.get("ann_queries") or []

        if not isinstance(ts_terms, list):
            ts_terms = []
        if not isinstance(ann_queries, list):
            ann_queries = []

        # Normalize + dedupe
        ts_terms = list({str(t).strip() for t in ts_terms if str(t).strip()})[:max_ts_terms]
        ann_queries = list({str(t).strip() for t in ann_queries if str(t).strip()})[:max_ann_queries]

        timeline_filters = data.get("timeline_filters") or []
        probe_citations = data.get("probe_citations") or []
        timeline_overview = str(data.get("timeline_overview") or "").strip()

        return {
            "ts_terms": ts_terms,
            "ann_queries": ann_queries,
            "timeline_filters": timeline_filters,
            "probe_citations": probe_citations,
            "timeline_overview": timeline_overview,
            "notes": data.get("notes") or "",
            "probe_failed": False,
        }
    except Exception:
        logger.exception(
            "Timeline probe LLM JSON parse failed; using heuristic fallback. raw=%r",
            raw[:500] + ("..." if len(raw) > 500 else ""),
        )
        base_terms = [w.strip().lower() for w in question.replace("/", " ").split() if len(w.strip()) >= 4]
        base_terms = list(dict.fromkeys(base_terms))[:max_ts_terms]
        return {
            "ts_terms": base_terms,
            "ann_queries": [question],
            "timeline_filters": [],
            "probe_citations": [],
            "timeline_overview": "",
            "notes": "heuristic_fallback",
            "probe_failed": True,
        }

async def _search_timeline_ts_for_terms(
    pool: Any,
    patient_id: str,
    terms: List[str],
    limit_total: int = TIMELINE_TS_LIMIT_PER_TERM * 4,
) -> List[Dict[str, Any]]:
    """
    Very simple TS search over ehr.patient_timeline.text for a given patient.

    Assumptions:
    - Table: ehr.patient_timeline
    - Columns:
        id          BIGINT / UUID
        patient_id  TEXT
        ts          TIMESTAMPTZ
        event_type  TEXT
        text        TEXT        -- renderable clinical text for the event

    This implementation uses ILIKE OR chains; if you have a proper tsvector index
    and a helper function, you can swap this out later for better ranking.
    """
    if not terms:
        return []

    # Build dynamic OR predicate: text ILIKE $2 OR text ILIKE $3 ...
    ilike_clauses = []
    params: List[Any] = [patient_id]
    for idx, term in enumerate(terms, start=1):
        ilike_clauses.append(f"text ILIKE ${idx + 1}")
        params.append(f"%{term}%")

    sql = f"""
        SELECT id, patient_id, ts, event_type, text
        FROM ehr.patient_timeline
        WHERE patient_id = $1
          AND ({' OR '.join(ilike_clauses)})
        ORDER BY ts
        LIMIT ${len(params) + 1};
    """
    params.append(limit_total)

    rows: List[Dict[str, Any]] = []
    async with pool.acquire() as conn:
        recs = await conn.fetch(sql, *params)

    # Score rows based on how many terms they mention (very simple heuristic)
    for r in recs:
        t = (r["text"] or "").lower()
        hit_count = sum(1 for term in terms if term.lower() in t)
        score = float(hit_count) / float(len(terms) or 1)
        rows.append(
            {
                "id": r["id"],
                "source": "ehr.patient_timeline",
                "patient_id": r["patient_id"],
                "ts": r["ts"],
                "event_type": r["event_type"],
                "title": f"{r['ts']} [{r['event_type']}]",
                "text": r["text"],
                "score": score,
                "method": "ts",
            }
        )

    return rows


def _to_pgvector_literal(vec: List[float]) -> str:
    """
    Convert a Python list[float] embedding into a pgvector-compatible text literal.

    Example:
        [0.1, -0.2] -> "[0.100000,-0.200000]"
    """
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


def _dedupe_timeline_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate rows by (source, id), keeping the highest score.
    """
    best_by_key: Dict[tuple, Dict[str, Any]] = {}
    for r in rows:
        key = (r.get("source"), r.get("id"))
        prev = best_by_key.get(key)
        if prev is None or float(r.get("score", 0.0) or 0.0) > float(prev.get("score", 0.0) or 0.0):
            best_by_key[key] = r
    deduped = list(best_by_key.values())
    deduped.sort(key=lambda r: float(r.get("score", 0.0) or 0.0), reverse=True)
    return deduped


def _augment_rows_with_simple_gap_logic(
    primary_rows: List[Dict[str, Any]],
    all_rows_ts_ann: List[Dict[str, Any]],
    max_extra: int = 12,
) -> List[Dict[str, Any]]:
    """
    Very lightweight, heuristic "gap retrieval" for timeline:

    - Ensure at least a few ICU-like events appear if they exist at all.
    - Ensure at least a few labs and notes appear if they exist at all.

    This is intentionally simple; it can later be replaced or augmented with the
    full EoH gap retrieval planner if desired.
    """
    if not all_rows_ts_ann:
        return primary_rows

    def _ev_type(row: Dict[str, Any]) -> str:
        return str(row.get("event_type") or "").lower()

    have = {r["id"] for r in primary_rows}
    extra: List[Dict[str, Any]] = []

    # Check presence by rough event_type buckets
    has_icu = any("icu" in _ev_type(r) or "careunit" in _ev_type(r) for r in primary_rows)
    has_lab = any("lab" in _ev_type(r) or "hematology" in _ev_type(r) for r in primary_rows)
    has_note = any("note" in _ev_type(r) or "progress" in _ev_type(r) for r in primary_rows)

    def _pick_missing(kind_check, max_pick):
        picked = 0
        for r in all_rows_ts_ann:
            if picked >= max_pick:
                break
            if r["id"] in have:
                continue
            if kind_check(_ev_type(r)):
                extra.append(r)
                have.add(r["id"])
                picked += 1

    if not has_icu:
        _pick_missing(lambda et: "icu" in et or "careunit" in et, max_pick=3)
    if not has_lab:
        _pick_missing(lambda et: "lab" in et or "hematology" in et, max_pick=4)
    if not has_note:
        _pick_missing(lambda et: "note" in et or "progress" in et, max_pick=4)

    if not extra:
        return primary_rows

    augmented = primary_rows + extra
    augmented = _dedupe_timeline_rows(augmented)
    if len(augmented) > TIMELINE_MAX_DOCS:
        augmented = augmented[:TIMELINE_MAX_DOCS]
    return augmented


def _format_timeline_rows_for_context(
    rows: List[Dict[str, Any]],
    max_chars: int,
    label_prefix: str = "TL",
) -> str:
    """
    Turn fused timeline rows into a compact textual context for the summarizer LLM.

    Output shape (example):

        [TL-1] ts=2145-01-02T14:30:00Z event=ICU_ADMISSION
        Creatinine rose to 3.2, patient started on vasopressors ...

    """
    blocks: List[str] = []
    total = 0

    for idx, r in enumerate(rows, start=1):
        ts = r.get("ts")
        ev_type = r.get("event_type") or "unknown"
        title = r.get("title") or ""
        text = (r.get("text") or "").strip()

        # Trim individual text to keep per-block reasonable
        if len(text) > 900:
            text = text[:900] + " [truncated]"

        header = f"[{label_prefix}-{idx}] ts={ts} event_type={ev_type} | {title}".strip()
        block = f"{header}\n{text}"

        if total + len(block) + 2 > max_chars:
            blocks.append("[timeline_context_truncated]")
            break

        blocks.append(block)
        total += len(block) + 2

    return "\n\n".join(blocks)

async def _run_eoh_gap_retrieval_for_timeline(
    *,
    pool: Any,
    patient_id: str,
    question: str,
    current_context: List[Dict[str, Any]],
    max_slots: int,
    avoid_ts_terms: Optional[List[str]] = None,
    avoid_ann_queries: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Use the Timeline Gap Retrieval Planner to decide whether we need additional
    targeted retrievals from ehr.patient_timeline, and if so, which slots.

    We also support:
      - avoid_ts_terms / avoid_ann_queries: don't repeat probes already used upstream
      - ann_library: stable library of ANN query options (optional)
    """
    if not current_context:
        return {"needs_gap_retrieval": False, "slots": [], "reason": ""}

    # Compact the context (this is what the planner should see)
    compact_context: List[Dict[str, Any]] = []
    for r in current_context:
        compact_context.append(
            {
                "id": str(r.get("id") or ""),
                "source": str(r.get("source") or "ehr.patient_timeline"),
                "ts": str(r.get("ts") or ""),
                "event_type": str(r.get("event_type") or ""),
                "title": (r.get("title") or "")[:200],
                "snippet": (r.get("text") or r.get("snippet") or "")[:800],
            }
        )

    payload = {
        "question": question,
        "patient_id": patient_id,
        "current_context": compact_context,
        "max_slots": int(max_slots),
        "avoid_ts_terms": avoid_ts_terms or [],
        "avoid_ann_queries": avoid_ann_queries or [],
        "ann_library": ann_library_for_llm() if "ann_library_for_llm" in globals() else {},
        "current_context_compact": compact_context,
    }

    messages = [
        {"role": "system", "content": EOH_TIMELINE_GAP_RETRIEVAL_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, cls=DateTimeJSONEncoder)},
    ]

    resp = await chat_completion_async(
        client=_openai_client,
        model=TIMELINE_PROBE_MODEL,
        messages=messages,
        max_tokens=1024,
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    if iscoroutine(resp):
        resp = await resp

    raw = (_safe_get_choice_content(resp) or "").strip()
    if not raw:
        logger.warning("Timeline gap retrieval planner returned empty; skipping gap retrieval.")
        return {"needs_gap_retrieval": False, "slots": [], "reason": ""}

    try:
        data = _extract_json_from_choice(resp.choices[0])
        needs = bool(data.get("needs_gap_retrieval"))
        slots = data.get("slots") or []
        if not isinstance(slots, list):
            slots = []
        
        drop_ids = {str(x) for x in (data.get("drop_row_ids") or []) if str(x).strip()}
        if drop_ids:
            augmented_rows = [r for r in augmented_rows if str(r.get("id") or "") not in drop_ids]

        # Normalize avoid sets
        avoid_ts = {_norm_query(x) for x in (avoid_ts_terms or []) if _norm_query(x)}
        # avoid_ann_queries may be raw strings OR library IDs; resolve them to compare apples-to-apples
        avoid_ann = set()
        for x in (avoid_ann_queries or []):
            resolved, _meta = resolve_ann_query_item(x)
            nx = _norm_query(resolved)
            if nx:
                avoid_ann.add(nx)

        # Filter overlaps inside returned slots
        for slot in slots:
            # TS terms: filter by normalized term
            slot["ts_terms"] = filter_out_overlaps(slot.get("ts_terms") or [], avoid_ts)

            # ANN queries: keep original items, but filter by resolved normalized query
            filtered_ann: List[str] = []
            for item in slot.get("ann_queries") or []:
                resolved, _ = resolve_ann_query_item(item)
                nr = _norm_query(resolved)
                if nr and nr not in avoid_ann:
                    filtered_ann.append(item)
            slot["ann_queries"] = filtered_ann

        return {
            "needs_gap_retrieval": needs,
            "slots": slots,
            "reason": data.get("reason") or "",
        }

    except Exception:
        logger.exception(
            "Timeline gap retrieval planner JSON parse failed; ignoring. raw=%r",
            raw[:500] + ("..." if len(raw) > 500 else ""),
        )
        return {"needs_gap_retrieval": False, "slots": [], "reason": ""}

def _estimate_rows_chars_for_budget(rows: List[Dict[str, Any]]) -> int:
    total = 0
    for r in rows:
        total += len(str(r.get("event_type") or ""))
        total += len(str(r.get("ts") or ""))
        total += len(str(r.get("text") or ""))  # or your main narrative field
    return total


async def _build_timeline_rag_context_for_summary(
    *,
    pool: Any,
    patient_id: str,
    question: str,
    timeline_text: str,
    client: AsyncOpenAI,
    max_context_chars: int = 20_000,
) -> tuple[str, Dict[str, Any]]:
    """
    High-level RAG pipeline for timeline summarization.

    Steps (implemented):

      1. Build a "peek" over the full timeline: start/end slices + random samples.
      2. Call a probe LLM on (question + peek) to generate:
           - probe_ts_terms (TS keyword phrases)
           - probe_ann_queries (ANN query phrases)
      3. Run TS + ANN over ehr.patient_timeline for this patient_id using those probes.
      4. Fuse results (simple score-based dedupe + heuristic gap augmentation).
      5. Build a textual RAG context from those events plus the peek.

    We also respect a global max_context_chars budget so that the final context
    fits comfortably within the summarizer's context window.
    """

    # --- Step 1: big-picture peek over the raw timeline --------------------
    peek_text = _build_timeline_peek_text(timeline_text)
    peek_len = len(peek_text)

    # Reserve some budget for headings + notes.
    overhead_chars = 1_000
    # Ensure we leave *some* room for TS/ANN context.
    min_ctx_for_rag = 4_000

        # Track gap plan + final rows for debug payload:
    gap_plan: Dict[str, Any] = {
        "needs_gap_retrieval": False,
        "slots": [],
    }
    final_rows: List[Dict[str, Any]] = []

    # If peek itself is already too large, trim it to leave room for TS/ANN.
    if peek_len + min_ctx_for_rag + overhead_chars > max_context_chars:
        allowed_peek = max_context_chars - (min_ctx_for_rag + overhead_chars)
        allowed_peek = max(2_000, allowed_peek)  # never let peek be *too* tiny
        if allowed_peek < peek_len:
            peek_text = peek_text[:allowed_peek]
            peek_len = len(peek_text)

    rag_budget = max_context_chars - peek_len - overhead_chars
    if rag_budget < min_ctx_for_rag:
        rag_budget = min_ctx_for_rag

    logger.info(
        "Timeline RAG: peek_len=%d, rag_budget=%d (max_context_chars=%d)",
        peek_len,
        rag_budget,
        max_context_chars,
    )

    # Track gap plan + rows for debug / downstream instrumentation
    gap_plan: Dict[str, Any] = {
        "needs_gap_retrieval": False,
        "slots": [],
    }
    final_rows: List[Dict[str, Any]] = []
    ts_rows: List[Dict[str, Any]] = []
    ann_rows: List[Dict[str, Any]] = []

    structured_snapshot = {
        "patient_id": patient_id,
        "event_type_counts": [],
        "diagnosis_events": [],
        "lab_events": [],
        "icu_events": [],
        "note_events": [],
    }

    # --- Step 2: build structured DB snapshot for probe --------------------
    try:
        structured_snapshot = await _build_structured_probe_snapshot(
            pool=pool,
            patient_id=patient_id,
        )
    except Exception:
        logger.exception(
            "Timeline RAG: failed to build structured_probe_snapshot; using empty snapshot."
        )
        structured_snapshot = None
    
    # Human-readable snapshot we can also use as part of fallback summary
    if structured_snapshot is not None:
        snapshot_text = render_probe_snapshot_md(structured_snapshot)
    else:
        snapshot_text = "# PROBE SNAPSHOT (STRUCTURED OVERVIEW)\n\n(empty - snapshot build failed)\n"

    # --- Step 3: Pre-probe ANN suite (multi-query) -------------------------------
    try:
        ann_suite_payload, ann_suite_block = await _build_preprobe_ann_suite(
            pool=pool,
            client=client,
            patient_id=patient_id,
            question=question,
        )
    except Exception:
        logger.exception("Pre-probe ANN suite crashed; ignoring.")
        ann_suite_payload, ann_suite_block = [], ""

    # Inject into peek_text (human-readable; cheap + effective)
    if ann_suite_block:
        peek_text = peek_text + "\n\n" + ann_suite_block

    # --- Step 4: probe LLM for TS/ANN terms + filters + citations ---------
    # Convert dataclass to dict for backwards compatibility with probe LLM
    if structured_snapshot is not None:
        from dataclasses import asdict
        structured_snapshot_dict = {
            "patient_id": structured_snapshot.patient_id,
            "event_type_counts": [{"event_type": k, "n": v} for k, v in structured_snapshot.counts.items()],
            "diagnosis_events": [{"ts": e.ts, "event_type": e.event_type, "text": e.preview} for e in structured_snapshot.dx_examples],
            "lab_events": [{"ts": e.ts, "event_type": e.event_type, "text": e.preview} for e in structured_snapshot.lab_examples],
            "note_events": [{"ts": e.ts, "event_type": e.event_type, "text": e.preview} for e in structured_snapshot.note_examples],
        }
    else:
        structured_snapshot_dict = {}
    
    probe = await _call_timeline_probe_llm(
        client=client,
        question=question,
        peek_text=peek_text,
        structured_snapshot=structured_snapshot_dict,
    )
    ts_terms: List[str] = probe.get("ts_terms") or []
    ann_queries: List[str] = probe.get("ann_queries") or []
    timeline_filters = probe.get("timeline_filters") or []
    probe_citations = probe.get("probe_citations") or []
    probe_overview = (probe.get("timeline_overview") or "").strip()
    probe_failed = bool(probe.get("probe_failed"))

    logger.info(
        "Timeline RAG probe: ts_terms=%d, ann_queries=%d, filters=%d, citations=%d, notes=%r",
        len(ts_terms),
        len(ann_queries),
        len(timeline_filters),
        len(probe_citations),
        (probe.get("notes") or "")[:200],
    )

    logger.info(
        "Timeline RAG probe: ts_terms=%d, ann_queries=%d, filters=%d, citations=%d, notes=%r",
        len(ts_terms),
        len(ann_queries),
        len(timeline_filters),
        len(probe_citations),
        (probe.get("notes") or "")[:200],
    )

    # --- Step 5: TS + ANN retrieval over ehr.patient_timeline --------------
    try:
        ts_rows = await _search_timeline_ts_for_terms(
            pool=pool,
            patient_id=patient_id,
            terms=ts_terms,
            limit_total=TIMELINE_TS_LIMIT_PER_TERM * max(1, len(ts_terms)),
        )
    except Exception:
        logger.exception("Timeline RAG: TS search failed; continuing without TS rows.")
        ts_rows = []

    try:
        ann_rows = await _search_timeline_ann_for_queries(
            pool=pool,
            patient_id=patient_id,
            ann_queries=ann_queries,
            per_query_limit=TIMELINE_ANN_LIMIT_PER_QUERY,
        )
    except Exception:
        logger.exception("Timeline RAG: ANN search failed; continuing without ANN rows.")
        ann_rows = []

    all_ts_ann_rows = ts_rows + ann_rows
    ctx_blocks = ""  # Initialize to avoid UnboundLocalError
    augmented_rows: List[Dict[str, Any]] = []  # Initialize to avoid UnboundLocalError
    
    if not all_ts_ann_rows:
        logger.warning(
            "Timeline RAG: no TS/ANN rows retrieved; using peek-only context."
        )
        ctx_blocks = ""
    else:
        # --- Step 5: fuse + simple gap augmentation ------------------------
        primary_rows: List[Dict[str, Any]] = list(all_ts_ann_rows)

        try:
            primary_rows = _dedupe_timeline_rows(primary_rows)
            if len(primary_rows) > TIMELINE_MAX_DOCS:
                primary_rows = primary_rows[:TIMELINE_MAX_DOCS]

            # Heuristic gap logic: ensure some ICU/lab/note coverage.
            augmented_rows = _augment_rows_with_simple_gap_logic(
                primary_rows=primary_rows,
                all_rows_ts_ann=all_ts_ann_rows,
            )
        except Exception:
            logger.exception(
                "Timeline RAG: primary/augmented rows computation failed; using primary rows only."
            )
            augmented_rows = primary_rows
        
        probe_ts_terms = ts_terms[:]  # as produced by probe
        probe_ann_items = ann_queries[:]  # may include LIB:<id>

        # For avoid purposes, compare on resolved query strings too
        probe_ann_resolved = []
        for item in probe_ann_items:
            rq, _ = resolve_ann_query_item(item)
            if _norm_query(rq):
                probe_ann_resolved.append(rq)

        probe_ts_terms = ts_terms[:]                  # as produced by probe
        probe_ann_items = ann_queries[:]              # may include LIB:<id>

        probe_ann_resolved: List[str] = []
        for item in probe_ann_items:
            rq, _ = resolve_ann_query_item(item)
            if _norm_query(rq):
                probe_ann_resolved.append(rq)

    # --- Optional: run EoH-style gap retrieval planner for extra slots -----
    try:
        gap_plan = await _run_eoh_gap_retrieval_for_timeline(
            pool=pool,
            patient_id=patient_id,
            question=question,
            current_context=augmented_rows,
            max_slots=TIMELINE_GAP_MAX_SLOTS,
            avoid_ts_terms=probe_ts_terms,
            avoid_ann_queries=probe_ann_resolved,
        )
    except Exception:
        logger.exception("Timeline RAG: Timeline gap retrieval planner failed; ignoring.")
        gap_plan = {"needs_gap_retrieval": False, "slots": []}

    extra_rows: List[Dict[str, Any]] = []

    if gap_plan.get("needs_gap_retrieval"):
        slots = gap_plan.get("slots") or []
        logger.info("Timeline RAG: gap retrieval requested: %r", slots)

        # estimate current context chars from rows (ctx_blocks not built yet)
        current_ctx_chars_est = _estimate_rows_chars_for_budget(augmented_rows)

        remaining = compute_remaining_gap_budget(
            budget=RagBudget(
                max_rows=TIMELINE_MAX_DOCS,
                max_chars=rag_budget,
                max_ts_terms=TIMELINE_PROBE_MAX_TS_TERMS,
                max_ann_queries=TIMELINE_PROBE_MAX_ANN_QUERIES,
            ),
            probe_ts_terms=probe_ts_terms,
            probe_ann_queries=probe_ann_items,
            current_rows=augmented_rows,
            current_ctx_chars=current_ctx_chars_est,
        )

        ts_remaining = remaining.max_ts_terms
        ann_remaining = remaining.max_ann_queries

        for slot in slots:
            retrieval_mode = (slot.get("retrieval_mode") or "ts").lower()
            limit = int(slot.get("limit") or 4)
            limit = max(1, min(limit, 6))

            ts_terms_slot = (slot.get("ts_terms") or [])[:ts_remaining]
            ann_queries_slot = (slot.get("ann_queries") or [])[:ann_remaining]
            ts_remaining -= len(ts_terms_slot)
            ann_remaining -= len(ann_queries_slot)

            if retrieval_mode in ("ts", "both") and ts_terms_slot:
                try:
                    more_ts = await _search_timeline_ts_for_terms(
                        pool=pool,
                        patient_id=patient_id,
                        terms=[str(t) for t in ts_terms_slot if str(t).strip()],
                        limit_total=limit,
                    )
                    extra_rows.extend(more_ts)
                except Exception:
                    logger.exception("Timeline RAG: gap TS search failed for slot_id=%r", slot.get("slot_id"))

            if retrieval_mode in ("ann", "both") and ann_queries_slot:
                try:
                    more_ann = await _search_timeline_ann_for_queries(
                        pool=pool,
                        patient_id=patient_id,
                        ann_queries=[str(a) for a in ann_queries_slot if str(a).strip()],
                        per_query_limit=limit,
                    )
                    extra_rows.extend(more_ann)
                except Exception:
                    logger.exception("Timeline RAG: gap ANN search failed for slot_id=%r", slot.get("slot_id"))

            if ts_remaining <= 0 and ann_remaining <= 0:
                break

    if extra_rows:
        augmented_rows = _dedupe_timeline_rows(augmented_rows + extra_rows)

    # Format augmented_rows into ctx_blocks if we have rows
    if augmented_rows:
        ctx_blocks = _format_timeline_rows_for_context(
            augmented_rows,
            max_chars=rag_budget,
            label_prefix="TL",
        )
    elif not ctx_blocks:  # Only set if not already set (from the empty case)
        ctx_blocks = ""

    # --- Build final RAG context (peek + TS/ANN context) -------------------
    rag_context = textwrap.dedent(
        f"""
        # PROBE SNAPSHOT (STRUCTURED OVERVIEW)

        {snapshot_text or "[no_snapshot_available]"}

        # PROBE LLM TIMELINE OVERVIEW

        {probe_overview or "[no_probe_overview_available]"}

        # TIMELINE PEEK (BIG PICTURE)

        {peek_text}

        # HIGH-YIELD TIMELINE CONTEXT (TS/ANN + GAP)

        {ctx_blocks or '[no_ts_ann_context_available]'}

        # NOTE
        You are seeing:
        - a structured snapshot summarizing event types and representative cases
        - a natural language probe overview (if available)
        - a sampled "peek" over the full timeline (start, end, and middle slices)
        - a curated set of high-yield events selected via text search (TS) and
          ANN embedding search, with some heuristic gap coverage (ICU, labs, notes).

        DO NOT assume that absence of evidence here means an event did not happen.
        When in doubt, be explicit about what is or is not clearly supported by
        this context, and prefer conservative clinical statements.
        """
    ).strip()

    if len(rag_context) > max_context_chars:
        rag_context = rag_context[:max_context_chars]

    probe_debug: Dict[str, Any] = {
        "question": question,
        "patient_id": patient_id,
        "peek_len": peek_len,
        "snapshot_present": bool(snapshot_text),
        "ts_terms": ts_terms,
        "ann_queries": ann_queries,
        "timeline_filters": timeline_filters,
        "probe_citations": probe_citations,
        "probe_overview": probe_overview,
        "probe_failed": probe_failed,
        "gap_plan": gap_plan,
        "ts_rows_count": len(ts_rows),
        "ann_rows_count": len(ann_rows),
        "final_rows_count": len(final_rows),
    }

    return rag_context, probe_debug


async def _call_timeline_summarizer_model(
    client: Any,
    question: str,
    payload: Dict[str, Any],
    max_tokens: int,
    extra_system_hint: str = "",
    fallback_context: str | None = None,
) -> TimelineSummaries:
    """
    Call the LLM to summarize a timeline segment (or reduce multiple segments).

    This matches how summarize_timeline_for_eoh() is calling it:
        _call_timeline_summarizer_model(
            client,
            question=...,
            payload=...,
            max_tokens=...,
            extra_system_hint=...,
        )

    It is best-effort:
    - Tries to parse JSON.
    - On failure, falls back to treating the raw text as the summary.
    """

    # Mode is just metadata for the prompt; we don't need a separate arg.
    mode = payload.get("mode", "single_pass")

    # System prompt with optional extra hint for map/reduce stages.
    system_content = EOH_TIMELINE_SUMMARIZER_SYSTEM_PROMPT
    if extra_system_hint:
        system_content = f"{system_content}\n\n{extra_system_hint}"

    # User content is ALWAYS a JSON blob the model should treat as input.
    user_content = json.dumps(
        {
            "mode": mode,
            "question": question,
            **payload,
        }
    )

    messages = [
        {
            "role": "system",
            "content": system_content,
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]

    # Support both AsyncOpenAI and sync-style clients.
    resp = await chat_completion_async(
        client=client,
        model=EOH_TIMELINE_SUMMARIZER_MODEL,
        messages=messages,
        max_tokens=4096,
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    if iscoroutine(resp):
        resp = await resp

    raw = _safe_get_choice_content(resp)
    raw = (raw or "").strip()

    if not raw:
        logger.error("Timeline summarizer: empty response from model")
        return TimelineSummaries(
            timeline_summary="",
            meds_and_labs_snapshot="",
        )

    # ------------------------------------------------------------------
    # Best-effort JSON parse; on failure, optionally use a known-safe
    # fallback context (e.g., probe+RAG context) instead of raw model text.
    # ------------------------------------------------------------------
    if raw.lstrip().startswith("{"):
        try:
            data = json.loads(raw)
            return _decode_timeline_summaries(data)
        except Exception:
            logger.exception(
                "Failed to parse timeline summarizer JSON; treating raw as free-text or using fallback_context. raw=%r",
                raw[:500] + ("..." if len(raw) > 500 else ""),
            )

            if fallback_context:
                canonical = fallback_context.strip()
            else:
                # Truncate raw to a safe size; this becomes the canonical story.
                canonical = raw[:SINGLE_PASS_CHAR_THRESHOLD].strip()

            logger.info("Timeline summarizer: using canonical fallback summary after JSON parse failure (len=%d).", len(canonical))

            return TimelineSummaries(
                timeline_summary=canonical,
                meds_and_labs_snapshot="",
            )
    else:
        # Model ignored response_format and just wrote prose.
        logger.warning(
            "Timeline summarizer: non-JSON response; using raw text or fallback_context. raw=%r",
            raw[:500] + ("..." if len(raw) > 500 else ""),
        )

        if fallback_context:
            canonical = fallback_context.strip()
        else:
            canonical = raw.strip()

        logger.info("Timeline summarizer: using canonical fallback summary for non-JSON response (len=%d).", len(canonical))

        return TimelineSummaries(
            timeline_summary=canonical,
            meds_and_labs_snapshot="",
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def summarize_timeline_for_eoh(
    client: AsyncOpenAI,
    question: str,
    timeline_text: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    pool: Any | None = None,
    patient_id: str | None = None,
    use_timeline_rag: bool | None = None,
) -> TimelineSummaries:
    """
    Main entrypoint used by the EoH stack.

    Behavior:
    - If `timeline_text` is relatively small, we do a single-pass JSON summary.
    - If it is very large, we PREFER:
        1) Probe + RAG over the patient's timeline (TS + ANN + gap), then
        2) A single summarizer call over the RAG context (plus a big-picture peek).

      If RAG is disabled or fails, we fall back to:
        1) Split into N chronological chunks.
        2) Run per-chunk "map" summaries.
        3) Run a final "reduce" summary.

    - On *any* catastrophic failure, we fall back to a truncated raw timeline.
    """
    try:
        if not timeline_text or not timeline_text.strip():
            logger.warning("Timeline summarizer received empty timeline_text.")
            return TimelineSummaries(
                timeline_summary="",
                meds_and_labs_snapshot="",
            )

        # Normalize whitespace a bit (helps with chunking).
        timeline_text = timeline_text.replace("\r\n", "\n")

        total_chars = len(timeline_text)
        logger.info(
            "Timeline summarizer: received timeline of %d characters for question=%r",
            total_chars,
            question[:120],
        )

        # -------------------------------------------------------------------
        # 1) Simple path: single-pass summary for modest timelines
        # -------------------------------------------------------------------
        if total_chars <= SINGLE_PASS_CHAR_THRESHOLD:
            logger.info(
                "Timeline summarizer: using SINGLE-PASS mode (chars=%d <= %d).",
                total_chars,
                SINGLE_PASS_CHAR_THRESHOLD,
            )
            payload = {
                "mode": "single_pass",
                "timeline_text": timeline_text,
            }
            return await _call_timeline_summarizer_model(
                client,
                question=question,
                payload=payload,
                max_tokens=max_tokens,
                extra_system_hint=(
                    "You are seeing the patient's full timeline in one block. "
                    "Produce concise but information-dense JSON fields as specified."
                ),
            )

        # -------------------------------------------------------------------
        # 1b) Probe+RAG path for very large timelines (preferred)
        # -------------------------------------------------------------------
        
        effective_flag = (
            EOH_TIMELINE_RAG_SUMMARY_ENABLED
            if use_timeline_rag is None
            else bool(use_timeline_rag)
        )

        if _should_use_rag_timeline_summary(
            total_chars=total_chars,
            patient_id=patient_id,
            pool=pool,
            enabled_flag=effective_flag,
        ):
            logger.info(
                "Timeline summarizer: using PROBE+RAG mode for patient_id=%r (chars=%d).",
                patient_id,
                total_chars,
            )
            try:
                rag_context, probe_debug = await _build_timeline_rag_context_for_summary(
                    pool=pool,  # type: ignore[arg-type]
                    patient_id=patient_id or "",
                    question=question,
                    timeline_text=timeline_text,
                    client=client,
                    max_context_chars=min(40_000, total_chars),
                )

                canonical = rag_context.strip()
                if len(canonical) > SUMMARY_MAX_CHARS:
                    canonical = canonical[:SUMMARY_MAX_CHARS]

                meds_labs = ""
                try:
                    if pool is not None and patient_id:
                        meds_labs = await _build_meds_and_labs_snapshot(
                            pool=pool, patient_id=patient_id
                        )
                except Exception:
                    logger.debug("Timeline summarizer: meds/labs snapshot build failed", exc_info=True)

                return TimelineSummaries(
                    timeline_summary=canonical,
                    meds_and_labs_snapshot=meds_labs,
                )

            except Exception:
                logger.exception(
                    "Timeline summarizer: PROBE+RAG mode failed; using truncated raw timeline as canonical summary (no hierarchical map/reduce)."
                )
                canonical = (timeline_text or "")[:SUMMARY_MAX_CHARS].strip()
                return TimelineSummaries(
                    timeline_summary=canonical,
                    meds_and_labs_snapshot="",
                )

        # -------------------------------------------------------------------
        # 2) Hierarchical path: map-reduce over large timelines (fallback)
        # -------------------------------------------------------------------
        logger.info(
            "Timeline summarizer: using HIERARCHICAL mode (chars=%d > %d).",
            total_chars,
            SINGLE_PASS_CHAR_THRESHOLD,
        )
        chunks = []

        # chunks = _split_timeline_into_chunks(
        #     timeline_text,
        #     target_chars=CHUNK_TARGET_CHAR_LEN,
        #     max_chunks=MAX_CHUNKS,
        # )
        n_chunks = len(chunks)
        logger.info(
            "Timeline summarizer: split into %d chunk(s) (target=%d chars, max_chunks=%d).",
            n_chunks,
            CHUNK_TARGET_CHAR_LEN,
            MAX_CHUNKS,
        )

        # Map step: summarize each chunk.
        chunk_summaries: List[TimelineSummaries] = []
        for idx, chunk_text in enumerate(chunks):
            logger.info(
                "Timeline summarizer: summarizing chunk %d/%d (chars=%d).",
                idx + 1,
                n_chunks,
                len(chunk_text),
            )

            # Slightly more focused question for the chunk.
            chunk_question = textwrap.dedent(
                f"""
                {question}

                You are only seeing segment {idx + 1} of {n_chunks} of the patient's
                longitudinal timeline. Focus on:
                - key clinical arcs and inflection points in THIS segment;
                - notable ICU stays, organ injuries, new diagnoses, and major treatment
                  changes evident in this segment;
                - any clear shifts in the patient's Ethos-of-Health terrain.

                Keep JSON fields concise and local to this segment, but preserve time
                anchors so a later reducer can stitch the story across segments.
                """
            ).strip()

            payload = {
                "mode": "segment_map",
                "segment_index": idx,
                "segment_count": n_chunks,
                "segment_timeline_text": chunk_text,
            }

            try:
                seg_summary = await _call_timeline_summarizer_model(
                    client,
                    question=chunk_question,
                    payload=payload,
                    max_tokens=min(MAP_STEP_MAX_TOKENS, max_tokens),
                    extra_system_hint=(
                        "You are summarizing ONE SEGMENT of a longer timeline. "
                        "Make the JSON fields reflect only information visible in this segment, "
                        "but include temporal cues (dates/relative timing) where possible."
                    ),
                )
                chunk_summaries.append(seg_summary)
            except Exception:
                logger.exception(
                    "Timeline summarizer: map-step failed for chunk %d/%d; continuing.",
                    idx + 1,
                    n_chunks,
                )
                # Even if one segment fails, continue with what we have.
                continue

        if not chunk_summaries:
            logger.error(
                "Timeline summarizer: all map-step calls failed; falling back to raw timeline."
            )
            raise RuntimeError("no_chunk_summaries")

        # Reduce step: aggregate chunk-level summaries into a global view.
        reduce_payload = {
            "mode": "reduce",
            "segments": [
                {
                    "segment_index": i,
                    "segment_count": n_chunks,
                    "full_timeline_summary": s.full_timeline_summary,
                    "router_timeline_summary": s.router_timeline_summary,
                    "valyu_timeline_summary": s.valyu_timeline_summary,
                    "query_terms_timeline_summary": s.query_terms_timeline_summary,
                    "meds_and_labs_snapshot": s.meds_and_labs_snapshot,
                }
                for i, s in enumerate(chunk_summaries)
            ],
        }

        reduce_hint = textwrap.dedent(
            """
            You are now aggregating multiple per-segment summaries into a SINGLE,
            COHERENT global view of the patient's clinical trajectory.

            - Merge overlapping details and avoid repetition.
            - Preserve chronology and highlight major shifts in the diagnostic landscape.
            - Produce:
              * full_timeline_summary: a readable longitudinal story.
              * router_timeline_summary: an even more structured view emphasizing
                questions the EoH router should care about (diagnostic axes, flares
                vs noise, organ systems at stake, etc.).
              * valyu_timeline_summary: key facts that should condition external
                research queries (e.g., severe ILD, CTD overlap, biologic exposure).
              * query_terms_timeline_summary: a compact list or narrative of search
                terms/phrases that will be useful to query this patient's timeline
                and external guidelines/research.
              * meds_and_labs_snapshot: concise summary of critical meds, lab trends,
                and monitoring issues.
            """
        ).strip()

        final_summaries = await _call_timeline_summarizer_model(
            client,
            question=question,
            payload=reduce_payload,
            max_tokens=max_tokens,
            extra_system_hint=reduce_hint,
        )

        return final_summaries

    except Exception as e:
        logger.error("Timeline summarizer call failed; falling back to truncated timeline: %s", e)

        canonical = (timeline_text or "")[:SUMMARY_MAX_CHARS].strip()

        return TimelineSummaries(
            timeline_summary=canonical,
            meds_and_labs_snapshot="",
        )