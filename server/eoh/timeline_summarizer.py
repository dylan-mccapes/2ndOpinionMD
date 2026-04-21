from __future__ import annotations

import asyncio
import itertools
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
from datetime import datetime, timedelta, date, timezone
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Union

from collections import Counter, defaultdict

from server.api.stream_config import (
    EOH_TIMELINE_SUMMARIZER_SYSTEM_PROMPT,
    EOH_TIMELINE_SUMMARIZER_MODEL,
    INGESTION_MODEL,
    INGESTION_GPT41_MAX_OUTPUT_TOKENS,
    INGESTION_GPT41_INPUT_FILL_RATIO,
    INGESTION_GPT41_SYSTEM_PROMPT_TOKEN_RESERVE,
    OLLAMA_BASE_URL,
    EOH_TIMELINE_GAP_MODEL,
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

# PatientTimelineVision for provenance tracking
from server.eoh.patient_timeline_vision import (
    PatientTimelineVision,
    TimelineEventVision,
    seed_from_structured_probe_snapshot,
    add_events_from_pdf_page,
    load_timeline_vision,
    save_timeline_vision,
)
from server.eoh.graph_enrichment import enrich_graph_opportunistic, OPPORTUNISTIC_MAX_CHARS

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
    - vision_path: optional path to PatientTimelineVision json (session temp snapshot)
    - graph_out_path: optional durable path when caller requested explicit graph export
    - timeline_enrichment: optional probe / PDF gap-synthesis-connascence payload for JSON export
    """
    timeline_summary: str = ""
    meds_and_labs_snapshot: str = ""
    valyu_summary: str = ""
    vision_path: Optional[str] = None
    graph_out_path: Optional[str] = None
    timeline_enrichment: Optional[Dict[str, Any]] = None

    # Map/reduce and legacy prompts use these names; keep aliases on one canonical story.
    @property
    def full_timeline_summary(self) -> str:
        return self.timeline_summary

    @property
    def router_timeline_summary(self) -> str:
        return self.timeline_summary

    @property
    def valyu_timeline_summary(self) -> str:
        return self.valyu_summary

    @property
    def query_terms_timeline_summary(self) -> str:
        return self.valyu_summary


# ---------------------------------------------------------------------------
# Tuning knobs
# ---------------------------------------------------------------------------

# Default max tokens for a *single* summarizer call.
# GPT-4.1 supports 32K output tokens; 4096 is a reasonable synthesis budget.
DEFAULT_MAX_TOKENS = 4096

# Hard cap on how much raw timeline text we ever include in a "fallback" summary.
FALLBACK_MAX_CHARS = 400_000

# If the timeline is shorter than this many characters, we do a single-pass summary.
# GPT-4.1 has 1M token context (~3M chars). 800K chars ≈ 80% capacity.
SINGLE_PASS_CHAR_THRESHOLD = 800_000

# GPT-4.1 context: 1M tokens ~= 3M chars. Reserve ~200K chars for system prompt,
# messages overhead, and 4096-token output. 700K chars ≈ 175K tokens — safe per chunk.
# At 700K chars, a 6M-char timeline splits into ~9 chunks instead of 31.
CHUNK_TARGET_CHAR_LEN = 700_000

# Minimum map segments for hierarchical mode; actual count scales up with timeline size
# (see _split_timeline_into_chunks) up to HIERARCHICAL_MAX_CHUNKS_CAP.
MAX_CHUNKS = 4
HIERARCHICAL_MAX_CHUNKS_CAP = 128

# Map step: each segment still emits full JSON summary fields; keep headroom.
MAP_STEP_MAX_TOKENS = 4096

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


def _compose_summaries_for_graph_enrichment(
    summaries: TimelineSummaries,
    max_chars: int = OPPORTUNISTIC_MAX_CHARS,
) -> str:
    """Merge summarizer outputs into one block for opportunistic graph enrichment."""
    parts: List[str] = []
    if summaries.timeline_summary:
        parts.append("# TIMELINE SUMMARY\n" + summaries.timeline_summary)
    if summaries.meds_and_labs_snapshot:
        parts.append("# MEDS AND LABS\n" + summaries.meds_and_labs_snapshot)
    if summaries.valyu_summary:
        parts.append("# VALYU / QUERY SIGNALS\n" + summaries.valyu_summary)
    text = "\n\n".join(parts).strip()
    if len(text) > max_chars:
        text = text[:max_chars]
    return text


async def _enrich_patient_timeline_vision_from_summarizer(
    patient_id: Optional[str],
    question: str,
    summaries: TimelineSummaries,
    step_id: str,
    *,
    timeline_vision: Optional[PatientTimelineVision] = None,
) -> None:
    """
    Load or create PatientTimelineVision and run opportunistic graph enrichment from
    summarizer outputs. Persists when the vision is not session_only.
    """
    if not patient_id:
        return
    answer = _compose_summaries_for_graph_enrichment(summaries)
    if not answer.strip():
        logger.debug(
            "Timeline summarizer vision enrich: no composed text (step=%s), skip",
            step_id,
        )
        return
    try:
        if timeline_vision is not None:
            vision = timeline_vision
            if not getattr(vision, "patient_id", None):
                vision.patient_id = patient_id
        else:
            vision = load_timeline_vision(patient_id)
            if not vision.patient_id:
                vision = PatientTimelineVision(
                    patient_id=patient_id,
                    built_at=datetime.now(timezone.utc).isoformat(),
                    session_only=False,
                    metadata={"source": "timeline_summarizer"},
                )
        await enrich_graph_opportunistic(
            step_id=step_id,
            step_question=question,
            step_answer=answer,
            step_citations=None,
            patient_id=patient_id,
            vision=vision,
            discovered_by_prefix="timeline_summarizer",
        )
        if not vision.session_only:
            save_timeline_vision(vision)
    except Exception:
        logger.warning(
            "Timeline summarizer: opportunistic vision enrichment failed (step=%s)",
            step_id,
            exc_info=True,
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
            current_context = [r for r in current_context if str(r.get("id") or "") not in drop_ids]

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


def _compact_rows_for_gap_context(
    rows: List[Dict[str, Any]],
    cap: int = 80,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in rows[:cap]:
        out.append(
            {
                "id": str(r.get("id", r.get("note_id", r.get("event_id", "")))),
                "event_type": r.get("event_type", r.get("kind", "")),
                "ts": str(r.get("ts", r.get("timestamp", ""))),
                "title": str(r.get("title", ""))[:120],
                "text": (r.get("text") or r.get("snippet") or r.get("body", ""))[:500],
            }
        )
    return out


def _existing_context_rows_from_vision(
    vision: PatientTimelineVision,
    cap: int = 60,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for ev in list(vision.events.values())[:cap]:
        prev = (ev.preview or "").strip()
        rows.append(
            {
                "id": ev.event_id,
                "event_type": ev.event_type,
                "ts": str(ev.timestamp or ""),
                "title": prev[:120],
                "text": prev[:500],
            }
        )
    return rows


def _apply_gap_opportunistic_edges(
    vision: PatientTimelineVision,
    gap_analysis: Dict[str, Any],
) -> None:
    for edge_data in gap_analysis.get("opportunistic_edges") or []:
        try:
            vision.add_edge(
                source_event_id=edge_data["source_event_id"],
                target_event_id=edge_data["target_event_id"],
                connascence_type=edge_data["connascence_type"],
                strength=edge_data.get("strength", 1.0),
                discovered_by="gap_agent_opportunistic",
                metadata={"reasoning": edge_data.get("reasoning", "")},
            )
        except Exception:
            logger.debug("skip bad opportunistic edge %r", edge_data, exc_info=True)


def _apply_enrichment_synthesis_to_vision(
    vision: PatientTimelineVision,
    enrichment_synthesis: Optional[Dict[str, Any]],
) -> None:
    if not enrichment_synthesis:
        return
    for edge_data in enrichment_synthesis.get("new_edges", []) or []:
        try:
            vision.add_edge(
                source_event_id=edge_data["source_event_id"],
                target_event_id=edge_data["target_event_id"],
                connascence_type=edge_data["connascence_type"],
                strength=edge_data.get("strength", 1.0),
                discovered_by="synthesis_agent",
                metadata={"reasoning": edge_data.get("reasoning", "")},
            )
        except Exception:
            logger.debug("skip bad synthesis edge %r", edge_data, exc_info=True)
    for update_data in enrichment_synthesis.get("metadata_updates", []) or []:
        event_id = update_data.get("event_id")
        if not event_id or event_id not in vision.events:
            continue
        event = vision.events[event_id]
        updates = update_data.get("updates", {})
        if "timestamp" in updates:
            event.timestamp = updates["timestamp"]
        if "annotations" in updates:
            event.annotations.update(updates["annotations"])


async def _run_timeline_enrichment_gap_synthesis_connascence(
    *,
    client: AsyncOpenAI,
    vision: PatientTimelineVision,
    patient_id: str,
    pool: Any | None,
    question: str,
    existing_context: List[Dict[str, Any]],
    artifact_base_path: Optional[str],
    phase_label: str,
    ingestion_client: Optional[AsyncOpenAI] = None,
    ingestion_model: str = INGESTION_MODEL,
    force_json_format: bool = True,
) -> Dict[str, Any]:
    from server.eoh.timeline_enrichment_gap_agent import analyze_timeline_enrichment_gaps
    from server.eoh.timeline_enrichment_synthesis_agent import synthesize_timeline_enrichment

    artifact: Dict[str, Any] = {
        "phase_label": phase_label,
        "edges_start": vision.count_edges(),
        "events": len(vision.events),
    }
    gap_analysis: Optional[Dict[str, Any]] = None
    enrichment_synthesis: Optional[Dict[str, Any]] = None

    if not vision.events:
        artifact["skipped"] = "no_events"
        return artifact

    # Gap agent + synthesis require a DB (pool) for retrieval — without it every
    # call produces 0 results and wastes two LLM round-trips.  Skip straight to
    # connascence enrichment when running in PDF session-only mode.
    if pool is None:
        logger.info(
            "Gap/synthesis skipped (no DB pool — PDF session mode); running connascence only (%s)",
            phase_label,
        )
        artifact["gap_analysis"] = {"skipped": "no_db_pool"}
        artifact["gap_retrieval_row_count"] = 0
        artifact["edges_after_gap_opportunistic"] = vision.count_edges()
        artifact["edges_after_synthesis"] = vision.count_edges()
    else:
        snapshot_counts = {
            "total_events": len(vision.events),
            "total_edges": vision.count_edges(),
        }
        try:
            gap_analysis = await analyze_timeline_enrichment_gaps(
                client=client,
                patient_timeline_vision=vision,
                timeline_snapshot=snapshot_counts,
                existing_context=existing_context,
                patient_id=patient_id,
            )
            artifact["gap_analysis"] = gap_analysis
        except Exception:
            logger.exception("timeline enrichment gap analysis failed (%s)", phase_label)
            artifact["gap_analysis_error"] = "failed"
            return artifact

        _apply_gap_opportunistic_edges(vision, gap_analysis)
        artifact["edges_after_gap_opportunistic"] = vision.count_edges()

        gap_retrieval_results: List[Dict[str, Any]] = []
        gap_queries = gap_analysis.get("gap_queries") or {}
        ts_terms = gap_queries.get("ts_terms") or []
        if ts_terms and gap_analysis.get("needs_enrichment", False):
            try:
                gap_retrieval_results = await _search_timeline_ts_for_terms(
                    pool=pool,
                    patient_id=patient_id,
                    terms=ts_terms,
                    limit_total=100,
                )
            except Exception:
                logger.exception("gap TS retrieval failed (%s)", phase_label)
        artifact["gap_retrieval_row_count"] = len(gap_retrieval_results)

        if gap_analysis.get("needs_enrichment", False) or gap_retrieval_results:
            try:
                enrichment_synthesis = await synthesize_timeline_enrichment(
                    client=client,
                    patient_timeline_vision=vision,
                    gap_analysis=gap_analysis,
                    gap_retrieval_results=gap_retrieval_results,
                    timeline_snapshot=snapshot_counts,
                    patient_id=patient_id,
                )
                artifact["synthesis"] = enrichment_synthesis
            except Exception:
                logger.exception("timeline enrichment synthesis failed (%s)", phase_label)
                artifact["synthesis_error"] = "failed"

        _apply_enrichment_synthesis_to_vision(vision, enrichment_synthesis)
        artifact["edges_after_synthesis"] = vision.count_edges()

    try:
        _conn_client = ingestion_client if ingestion_client is not None else client
        await _enrich_timeline_vision_connascence(
            vision, _conn_client, question, model=ingestion_model,
            force_json_format=force_json_format,
        )
    except Exception:
        logger.exception("connascence rubric enrichment failed (%s)", phase_label)

    artifact["edges_end"] = vision.count_edges()

    if artifact_base_path and "patient_timeline_vision_" in artifact_base_path:
        try:
            if gap_analysis is not None:
                gap_path = artifact_base_path.replace(
                    "patient_timeline_vision_", f"gap_analysis_{phase_label}_", 1
                )
                with open(gap_path, "w", encoding="utf-8") as f:
                    json.dump(gap_analysis, f, indent=2, ensure_ascii=False)
                artifact["gap_analysis_path"] = gap_path
            if enrichment_synthesis is not None:
                syn_path = artifact_base_path.replace(
                    "patient_timeline_vision_", f"enrichment_synthesis_{phase_label}_", 1
                )
                with open(syn_path, "w", encoding="utf-8") as f:
                    json.dump(enrichment_synthesis, f, indent=2, ensure_ascii=False)
                artifact["synthesis_path"] = syn_path
        except Exception:
            logger.exception("failed to write timeline enrichment artifacts (%s)", phase_label)

    return artifact


async def _enrich_timeline_vision_after_rag_probe(
    *,
    client: AsyncOpenAI,
    timeline_vision: Optional[PatientTimelineVision],
    patient_id: str,
    question: str,
    rag_context: str,
    augmented_rows: List[Dict[str, Any]],
    pool: Any,
) -> Optional[Dict[str, Any]]:
    if timeline_vision is None or not patient_id:
        return None
    out: Dict[str, Any] = {}
    try:
        snippet = rag_context[:OPPORTUNISTIC_MAX_CHARS]
        cites = _compact_rows_for_gap_context(augmented_rows, cap=25)
        cite_msgs = [
            {"title": str(c.get("title") or c.get("id")), "snippet": str(c.get("text", ""))[:400]}
            for c in cites
        ]
        await enrich_graph_opportunistic(
            step_id="probe_rag_context",
            step_question=question,
            step_answer=snippet,
            step_citations=cite_msgs or None,
            patient_id=patient_id,
            vision=timeline_vision,
            discovered_by_prefix="timeline_probe_rag",
        )
        out["opportunistic_probe_rag"] = {"ok": True}
    except Exception:
        logger.exception("opportunistic enrich after RAG probe failed")
        out["opportunistic_probe_rag"] = {"ok": False}

    try:
        ctx = _compact_rows_for_gap_context(augmented_rows)
        pipe = await _run_timeline_enrichment_gap_synthesis_connascence(
            client=client,
            vision=timeline_vision,
            patient_id=patient_id,
            pool=pool,
            question=question,
            existing_context=ctx,
            artifact_base_path=None,
            phase_label="probe_rag",
        )
        out["gap_synthesis_connascence"] = pipe
    except Exception:
        logger.exception("gap/synthesis/connascence after RAG probe failed")
        out["gap_synthesis_connascence_error"] = "failed"

    return out


async def _build_timeline_rag_context_for_summary(
    *,
    pool: Any,
    patient_id: str,
    question: str,
    timeline_text: str,
    client: AsyncOpenAI,
    max_context_chars: int = 20_000,
    timeline_vision: Optional[PatientTimelineVision] = None,
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

    probe_ts_terms: List[str] = list(ts_terms or [])
    probe_ann_items: List[str] = list(ann_queries or [])
    probe_ann_resolved: List[str] = []
    for item in probe_ann_items:
        rq, _ = resolve_ann_query_item(item)
        if _norm_query(rq):
            probe_ann_resolved.append(rq)

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
        "final_rows_count": len(augmented_rows),
    }

    if timeline_vision is not None:
        try:
            probe_debug["timeline_enrichment"] = await _enrich_timeline_vision_after_rag_probe(
                client=client,
                timeline_vision=timeline_vision,
                patient_id=patient_id,
                question=question,
                rag_context=rag_context,
                augmented_rows=augmented_rows,
                pool=pool,
            )
        except Exception:
            logger.exception("timeline vision probe enrichment hook failed")
            probe_debug["timeline_enrichment"] = {"error": "hook_failed"}

    return rag_context, probe_debug


async def _call_timeline_summarizer_model(
    client: Any,
    question: str,
    payload: Dict[str, Any],
    max_tokens: int,
    extra_system_hint: str = "",
    fallback_context: str | None = None,
    use_claude: bool = False,
    summarizer_model: str | None = None,
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

    When ``use_claude=True``, calls Claude Opus via the Anthropic SDK
    instead of using the OpenAI-compatible ``client``.
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

    if use_claude:
        from server.llm.llm_client import claude_chat_async, CLAUDE_SYNTHESIS_MODEL
        claude_system = (
            system_content
            + "\n\nIMPORTANT: You MUST respond with valid JSON only. "
            "No markdown, no code fences, no prose — just a single JSON object."
        )
        raw = await claude_chat_async(
            messages=[{"role": "user", "content": user_content}],
            system=claude_system,
            model=CLAUDE_SYNTHESIS_MODEL,
            max_tokens=max_tokens,
            temperature=0.0,
        )
        raw = (raw or "").strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines).strip()
    else:
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

        _model = summarizer_model or EOH_TIMELINE_SUMMARIZER_MODEL
        resp = await chat_completion_async(
            client=client,
            model=_model,
            messages=messages,
            max_tokens=max_tokens,
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
# PDF Import Support (Session-Only)
# ---------------------------------------------------------------------------

# Batched PDF event extraction: target ~60% of a GPT-4.1–class 1M-token context
# for *input* (pages JSON), with explicit reserves for system prompt and large JSON output.
# (Same spirit as server/eoh/graph_enrichment.py BATCH_MAX_CHARS / ENRICHMENT_CONTEXT_FILL_RATIO.)
# GPT-4.1 context / output limits for per-page event extraction.
#
# Output budget math:
#   GPT-4.1 hard cap = 32,768 output tokens.
#   Target ~150-180 tokens of output per page (enough for typed JSON events).
#   → max pages per batch ≈ 32,768 / 160 ≈ 200 pages.
#
# Context fill ratio of 0.10 yields:
#   input ≈ (1,048,576 × 0.10 − 6,000 − 32,768) × 4 ≈ 264 K input chars
#   ≈ 183 pages/batch → ~179 output tokens per page.
#
# Raising the ratio above ~0.12 collapses output budget below ~130 tokens/page
# and causes the model to fall back to generic "note" / "page" event types.
_PDF_EXTRACTION_GPT41_MAX_CONTEXT_TOKENS = 1_048_576
_PDF_EXTRACTION_CONTEXT_FILL_RATIO = 0.10
_PDF_EXTRACTION_SYSTEM_PROMPT_TOKENS_RESERVE = 6_000
_PDF_EXTRACTION_OUTPUT_TOKENS_RESERVE = 32_768
_PDF_EXTRACTION_CHARS_PER_TOKEN_ESTIMATE = 4
# Per page: wrapper keys in JSON (~40) + small margin
_PDF_EXTRACTION_PER_PAGE_JSON_OVERHEAD_CHARS = 64


def _ingestion_is_full_gpt41(model: Optional[str]) -> bool:
    """True for GPT-4.1 (not gpt-4.1-mini) — long prompt + 60% input / large completion budget."""
    if not model:
        return False
    m = model.lower().strip()
    return m.startswith("gpt-4.1") and not m.startswith("gpt-4.1-mini")


def _ollama_num_ctx_default() -> int:
    """
    Ollama KV cache size (options.num_ctx) for PDF batch extraction.

    Default matches ``eoh-llama3.1:8b.Modelfile`` (``PARAMETER num_ctx 32768``).
    Override: ``OLLAMA_NUM_CTX`` or ``INGESTION_OLLAMA_CONTEXT_TOKENS``.
    """
    from server.api.stream_config import INGESTION_OLLAMA_CONTEXT_TOKENS

    raw = os.getenv("OLLAMA_NUM_CTX")
    if raw:
        return max(2048, int(raw))
    return max(2048, int(INGESTION_OLLAMA_CONTEXT_TOKENS))


def _ollama_max_predict_tokens(ollama_num_ctx: Optional[int]) -> int:
    """
    Max new tokens per PDF extraction batch (``num_predict``).

    Derived from the 30% output fill ratio in ``stream_config`` so it scales with
    ``num_ctx``. ``OLLAMA_MAX_PREDICT`` is still respected as an explicit override.
    """
    from server.api.stream_config import ingestion_ollama_max_output_tokens

    ctx = ollama_num_ctx if ollama_num_ctx is not None else _ollama_num_ctx_default()
    env_override = os.getenv("OLLAMA_MAX_PREDICT")
    if env_override:
        return max(1024, int(env_override))
    return ingestion_ollama_max_output_tokens(ctx)


def _ollama_max_pages_per_batch() -> int:
    """
    Safety ceiling on pages per Ollama extraction batch.

    With chapter-aware batching the real limit is the input-token budget
    (``INGESTION_OLLAMA_INPUT_FILL_RATIO`` × ``num_ctx``). This cap exists only
    to keep pathological chapters (a 200-page administrative-forms run) from
    being dispatched as a single call.
    """
    return max(1, min(80, int(os.getenv("OLLAMA_MAX_PAGES_PER_BATCH", "40"))))


def _ollama_output_tokens_per_page_estimate() -> int:
    """
    Used only to derive max pages per batch for small-context models.
    Higher = assume more output per page = smaller batches.
    Default 1200 pairs with default num_predict (~6144): ~5 pages/batch without
    starving JSON. Raise via env if batches hit max_tokens / truncated JSON.
    """
    return max(800, int(os.getenv("OLLAMA_OUTPUT_TOKENS_PER_PAGE_ESTIMATE", "1200")))


PDF_EVENT_BATCH_MAX_INPUT_CHARS: int = int(
    (
        _PDF_EXTRACTION_GPT41_MAX_CONTEXT_TOKENS * _PDF_EXTRACTION_CONTEXT_FILL_RATIO
        - _PDF_EXTRACTION_SYSTEM_PROMPT_TOKENS_RESERVE
        - _PDF_EXTRACTION_OUTPUT_TOKENS_RESERVE
    )
    * _PDF_EXTRACTION_CHARS_PER_TOKEN_ESTIMATE
)


# ---------------------------------------------------------------------------
# Page selection strategies for graph event extraction
# ---------------------------------------------------------------------------

#: Sentinel string used with --extraction-mode.
PDF_EXTRACTION_MODE_FULL = "full"
PDF_EXTRACTION_MODE_LITE = "lite"

# Lite-mode defaults: pages drawn from the three zones.
_LITE_HEAD_PAGES = 200
_LITE_TAIL_PAGES = 200
_LITE_MC_MIDDLE_PAGES = 400


def _select_pages_lite(
    page_entries: List[Tuple[int, str]],
    head: int = _LITE_HEAD_PAGES,
    tail: int = _LITE_TAIL_PAGES,
    mc_middle: int = _LITE_MC_MIDDLE_PAGES,
) -> List[Tuple[int, str]]:
    """
    Lite extraction strategy: head + tail + Monte Carlo sample of middle pages.

    Rationale:
    - Head covers problem lists, demographics, chronic conditions.
    - Tail covers the most recent events and discharge summaries.
    - Monte Carlo middle ensures sparse but representative coverage of the arc.

    The full timeline_text still flows to the summarizer unchanged — this only
    controls which pages get expensive per-page graph event extraction.
    """
    import random

    n = len(page_entries)
    if n <= head + tail:
        # Short record — take everything.
        return list(page_entries)

    head_entries = page_entries[:head]
    tail_entries = page_entries[n - tail :]
    middle_pool = page_entries[head : n - tail]

    # Sample without replacement; reproducible only within a run (no fixed seed
    # by design — Monte Carlo is intentionally stochastic across runs).
    mc_sample = random.sample(middle_pool, min(mc_middle, len(middle_pool)))

    # Merge and restore chronological page order.
    selected = list({e[0]: e for e in head_entries + mc_sample + tail_entries}.values())
    selected.sort(key=lambda x: x[0])

    return selected


def _iter_pdf_event_extraction_batches(
    page_entries: List[Tuple[int, str]],
    max_chars: Optional[int] = None,
    max_pages: Optional[int] = None,
) -> List[List[Tuple[int, str]]]:
    """
    Group (pdf_page_num, text) tuples into batches that fit under max_chars
    AND under max_pages (whichever is reached first).

    max_chars: cap on total input chars per batch (default: GPT-4.1 sized).
    max_pages: cap on page count per batch.  Use this to keep the output
               token budget from overflowing on small models that generate
               ~800-1000 tokens per page.
    """
    if not page_entries:
        return []

    max_chars = max_chars if max_chars is not None else PDF_EVENT_BATCH_MAX_INPUT_CHARS
    overhead = _PDF_EXTRACTION_PER_PAGE_JSON_OVERHEAD_CHARS
    batches: List[List[Tuple[int, str]]] = []
    current: List[Tuple[int, str]] = []
    current_size = 0

    for page_num, text in page_entries:
        need = len(text) + overhead
        if need > max_chars:
            logger.warning(
                "PDF page %d: text+overhead (%d chars) exceeds batch cap (%d); truncating page text",
                page_num,
                need,
                max_chars,
            )
            text = text[: max(0, max_chars - overhead)]
            need = len(text) + overhead

        chars_full = current and current_size + need > max_chars
        pages_full = max_pages and len(current) >= max_pages
        if current and (chars_full or pages_full):
            batches.append(current)
            current = []
            current_size = 0

        current.append((page_num, text))
        current_size += need

    if current:
        batches.append(current)

    return batches


def _strip_markdown_fences(text: str) -> str:
    """Strip markdown fences and any preamble text that local models wrap around JSON.

    Handles three cases:
      1. ````` at the very start  (```json\\n{...}```)
      2. Preamble text before a fence  ("Here is the JSON:\\n\\n```json\\n{...}```")
      3. No fences — try to find the first ``{`` and extract from there
    """
    text = text.strip()

    # Fast path: if it already looks like JSON, return as-is.
    if text.startswith("{") or text.startswith("["):
        return text

    # Find the first ``` fence (may not be at position 0).
    fence_start = text.find("```")
    if fence_start != -1:
        after_fence = text[fence_start:]
        parts = after_fence.split("```")
        if len(parts) >= 3:
            inner = parts[1]
            # Strip optional language tag (e.g. "json\n")
            if inner and not inner.lstrip().startswith(("{", "[")):
                newline = inner.find("\n")
                inner = inner[newline + 1:] if newline != -1 else inner
            stripped = inner.strip()
            if stripped:
                return stripped

    # No fences found (or malformed). Try to extract JSON object/array directly.
    brace = text.find("{")
    bracket = text.find("[")
    candidates = [i for i in (brace, bracket) if i != -1]
    if candidates:
        start = min(candidates)
        return text[start:].strip()

    return text


async def _ollama_chat_direct(
    base_url: str,
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 8192,
    temperature: float = 0.1,
    num_ctx: Optional[int] = None,
    timeout: float = 900.0,
) -> str:
    """
    Call Ollama via its **native** ``/api/chat`` endpoint using httpx.

    Previous attempts used the OpenAI-compatible ``/v1/chat/completions``
    endpoint, which silently ignores ``options.num_ctx``.  Without an explicit
    context size the model falls back to Ollama's default (often 2048), and
    the ~6K-token extraction batches overflow the context — producing either
    truncated output or empty bodies that surface as ``JSONDecodeError``.

    The native endpoint properly handles ``options.num_ctx`` and
    ``options.num_predict`` (the equivalent of ``max_tokens``).

    *base_url* may be either ``http://host:11434/v1`` (from the OpenAI-compat
    client) or ``http://host:11434`` — both are normalised to the bare host.
    """
    import httpx

    ollama_host = base_url.rstrip("/")
    for suffix in ("/v1/chat/completions", "/v1"):
        if ollama_host.endswith(suffix):
            ollama_host = ollama_host[: -len(suffix)]
            break
    endpoint = ollama_host + "/api/chat"

    opts: Dict[str, Any] = {"temperature": temperature}
    if num_ctx:
        opts["num_ctx"] = num_ctx
    if max_tokens:
        opts["num_predict"] = max_tokens

    body: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": opts,
    }

    logger.info(
        "Ollama native call: model=%s  num_ctx=%s  num_predict=%s  msgs=%d  endpoint=%s",
        model, num_ctx, max_tokens, len(messages), endpoint,
    )

    async with httpx.AsyncClient(timeout=timeout) as http:
        resp = await http.post(endpoint, json=body)
        raw_bytes = resp.content
        status_code = resp.status_code

    if status_code != 200:
        snippet = raw_bytes[:500].decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama HTTP {status_code}: {snippet}")

    if not raw_bytes or not raw_bytes.strip():
        raise ValueError(
            f"Ollama returned HTTP 200 with empty body "
            f"(model={model}, num_predict={max_tokens}, num_ctx={num_ctx}). "
            "Try reducing batch size or num_ctx."
        )

    logger.info("Ollama response: %d bytes (first 300): %s",
                len(raw_bytes), raw_bytes[:300].decode("utf-8", errors="replace"))

    data = json.loads(raw_bytes)

    if "error" in data:
        raise RuntimeError(f"Ollama returned error in body: {data['error']}")

    msg = data.get("message")
    if not msg or not isinstance(msg, dict):
        logger.warning(
            "Ollama /api/chat: no 'message' in response. Keys: %s | body[:400]: %s",
            list(data.keys()),
            raw_bytes[:400].decode("utf-8", errors="replace"),
        )
        raise ValueError(f"Ollama response missing 'message' (keys: {list(data.keys())})")

    content = msg.get("content") or ""
    if not content:
        done_reason = data.get("done_reason", "unknown")
        logger.warning(
            "Ollama returned empty content. done_reason=%s  eval_count=%s  total_duration=%s",
            done_reason,
            data.get("eval_count"),
            data.get("total_duration"),
        )
    else:
        eval_count = data.get("eval_count", "?")
        total_ns = data.get("total_duration", 0)
        total_s = total_ns / 1e9 if isinstance(total_ns, (int, float)) else 0
        logger.info("Ollama generation complete: %s tokens in %.1fs", eval_count, total_s)

    return content


def _close_truncated_string(raw: str) -> str:
    """If *raw* ends inside an unterminated JSON string, close the string.

    Walks through the raw text tracking whether we're inside a string
    literal (handling backslash escapes).  If we end up inside a string,
    truncate back to the opening quote and close it, which lets the
    structural-repair pass find a valid ``}`` to close against.
    """
    in_string = False
    last_open_quote = -1
    i = 0
    while i < len(raw):
        c = raw[i]
        if c == '\\' and in_string:
            i += 2
            continue
        if c == '"':
            if not in_string:
                last_open_quote = i
            in_string = not in_string
        i += 1
    if in_string and last_open_quote >= 0:
        return raw[:last_open_quote] + '""'
    return raw


def _extract_complete_page_objects(raw: str) -> list:
    """Regex-extract complete ``{"page_num": N, "events": [...]}`` objects.

    Last-resort salvage: even when the overall JSON structure is
    irrecoverable, individual page objects that were fully generated
    before the truncation point can still be parsed.
    """
    import re
    pages: list = []
    for m in re.finditer(r'\{\s*"page_num"\s*:', raw):
        start = m.start()
        depth = 0
        pos = start
        while pos < len(raw):
            c = raw[pos]
            if c == '"':
                pos += 1
                while pos < len(raw) and raw[pos] != '"':
                    if raw[pos] == '\\':
                        pos += 1
                    pos += 1
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    candidate = raw[start:pos + 1]
                    try:
                        obj = json.loads(candidate)
                        if isinstance(obj, dict) and "page_num" in obj:
                            pages.append(obj)
                    except json.JSONDecodeError:
                        pass
                    break
            pos += 1
    return pages


def _repair_truncated_extraction_json(raw: str) -> dict:
    """Salvage a truncated JSON extraction response.

    When the model hits num_predict and the output is cut mid-JSON, try
    three repair strategies in order:

    1. Walk backwards from the truncation point, closing structure at
       each ``}`` character.
    2. Close any unterminated string literal first, then retry (1).
    3. Regex-extract individually complete page objects and reconstruct.
    """
    def _try_walk_backwards(text: str, strategy_label: str) -> dict | None:
        for i in range(len(text) - 1, max(0, len(text) - 10000), -1):
            if text[i] != "}":
                continue
            for suffix in ("\n]}", "]}"):
                candidate = text[: i + 1] + suffix
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict) and isinstance(parsed.get("pages"), list):
                        logger.warning(
                            "Repaired truncated JSON (%s): salvaged %d page(s) "
                            "(cut at char %d of %d)",
                            strategy_label,
                            len(parsed["pages"]), i + 1, len(raw),
                        )
                        return parsed
                except json.JSONDecodeError:
                    continue
        return None

    # Strategy 1: walk-backwards on raw text
    result = _try_walk_backwards(raw, "close-brace")
    if result is not None:
        return result

    # Strategy 2: close unterminated string literal, then walk-backwards
    closed = _close_truncated_string(raw)
    if closed != raw:
        result = _try_walk_backwards(closed, "close-string")
        if result is not None:
            return result

    # Strategy 3: regex-extract individually complete page objects
    pages = _extract_complete_page_objects(raw)
    if pages:
        logger.warning(
            "Repaired truncated JSON (regex-extract): salvaged %d page(s) "
            "from %d chars of output",
            len(pages), len(raw),
        )
        return {"pages": pages}

    raise json.JSONDecodeError(
        "Could not repair truncated extraction JSON", raw, len(raw) - 1
    )


async def _extract_events_from_pages_batch(
    client: AsyncOpenAI,
    pages: List[Tuple[int, str]],
    model: str = INGESTION_MODEL,
    force_json_format: bool = True,
    ollama_num_ctx: Optional[int] = None,
    ollama_native_api: bool = False,
    heuristic_results: Optional[Dict[int, Any]] = None,
) -> Dict[int, List[Dict[str, Any]]]:
    """
    One LLM call for many PDF pages. Returns map pdf_page_num -> event dicts.
    Pass an Ollama client + a local model name for zero-cost extraction.
    Set force_json_format=False for Ollama — grammar-constrained sampling is
    5-10x slower than normal generation and causes timeout failures.
    Set ollama_num_ctx to override Ollama's KV cache size (e.g. 65536 halves
    the default 16 GB KV cache to 8 GB, leaving headroom for generation).
    Set ollama_native_api=True only for localhost Ollama (validated on M2 Ultra).
    Remote Ollama should use ollama_native_api=False (OpenAI-compat with extra_body).
    """
    if not pages:
        return {}

    # Ollama (small local models) gets a compact prompt that:
    #   - Uses shorter field names and capped preview length to save output tokens
    #   - Lists MEDICATION as the absolute first extraction priority
    #   - Makes drug_name, drug_dosage, drug_route mandatory on medication events
    #   - Keeps total instruction tokens low so more budget goes to actual output
    _SYSTEM_PROMPT_FULL = textwrap.dedent("""
        You are a precise medical event extraction agent.
        You receive multiple pages from a patient record PDF as JSON: a "pages" array.
        For EACH page, extract timeline events found ONLY in that page's text.

        Event rules (per event):
        - `event_type`: one of ["diagnosis", "medication", "lab", "procedure", "symptom", "clinical_note", "vital_signs", "imaging", "immunization", "administrative"]
          NEVER use "page" or a bare "note" — always pick a medically meaningful type.
          "administrative" is only for pages with no clinical content (release-of-info, consent forms, pure demographics).
        - `timestamp`: YYYY-MM-DD if present in text, else "unknown"
        - `preview`: 2 sentences, ≤240 characters. Sentence 1 states WHAT (name/value/finding/drug+dose). Sentence 2 states WHY/CONTEXT (indication, change rationale, site, clinician) when the page states it; otherwise omit sentence 2. Never fabricate context.
        - `drug_name`: (medication events ONLY) the generic drug name exactly as written
          in the text, e.g. "prednisone", "pyridostigmine", "mycophenolate mofetil".
          REQUIRED for every medication event. Use generic name when brand also present.
        - `drug_dosage`: (medication events ONLY, optional) dose string exactly as written,
          e.g. "60 mg", "500 mg twice daily". Include when present.
        - `drug_route`: (medication events ONLY, optional) one of oral|IV|IM|SC|topical|inhaled|other.
          Include when route is stated or clearly implied.
        Do not hallucinate. If a page has no clear clinical events, use "events": [].

        Output MUST be a single JSON object:
        {
          "pages": [
            { "page_num": <int>, "events": [
                { "event_type": "...", "timestamp": "...", "preview": "..." },
                { "event_type": "medication", "timestamp": "...", "preview": "...",
                  "drug_name": "prednisone", "drug_dosage": "20 mg", "drug_route": "oral" },
                ...
            ] },
            ...
          ]
        }

        Include exactly one entry in "pages" for every input page_num, in ascending page_num order.
        Do not merge events across pages. Do not include markdown or commentary outside JSON.

        Some pages may include a "pre_extracted" field with events already found by
        regex heuristics (dates, ICD codes, medication patterns). When present:
        - Correct any misclassified events
        - Add events the heuristics missed (especially symptoms, clinical notes, procedures)
        - Improve previews where the heuristic preview is poor
        - Do NOT re-emit events that the heuristics already captured correctly
        Focus your output tokens on what the heuristics MISSED.
    """).strip()

    # GPT-4.1 long-context path: maximize recall and clinical detail for the graph.
    _SYSTEM_PROMPT_GPT41_HIGH_DETAIL = textwrap.dedent("""
        You are an exhaustive clinical timeline extractor for a longitudinal patient record.
        You receive multiple PDF pages as JSON with a "pages" array (each item: page_num, text,
        and optionally pre_extracted heuristic hints).

        GOAL: Emit AS MANY distinct, clinically meaningful events as the text supports — prefer
        splitting separate findings, visits, medication changes, labs, imaging, procedures,
        diagnoses, and symptoms into separate events rather than collapsing them.

        For EACH page, extract ONLY what appears on that page. Never merge across pages.

        Per event (use every applicable field; do not omit optional fields when the text supports them):
        - event_type: one of diagnosis | medication | lab | procedure | symptom | clinical_note | vital_signs | imaging | immunization | administrative.
          NEVER use "page" or a bare "note" — always pick a medically meaningful type.
          "administrative" is only for pages with no clinical content (release-of-info forms, page boilerplate, pure demographics).
        - timestamp: YYYY-MM-DD if explicitly anchored on that page; else "unknown". Never invent dates.
        - preview: 2–4 sentences when warranted, up to ~800 characters — include values, trends,
          indication, clinician name or setting ONLY if stated in the page text. Minimum 2 sentences whenever the page supports it.
        - detail: (optional) longer structured narrative for complex rows (differential, reasoning,
          multi-step plans) — up to ~2000 characters when the page is dense; omit if preview suffices.
        - drug_name: (medication only) generic name as written; REQUIRED for every medication event.
        - drug_dosage: (medication only) dose, frequency, changes, as written.
        - drug_route: (medication only) oral|IV|IM|SC|topical|inhaled|other when known.

        Quality rules:
        - Capture labs with names and numeric results when present; procedures with laterality/site when stated.
        - Immunizations and vaccinations are "procedure", not "lab".
        - Do not hallucinate; empty administrative-only pages → "events": [].

        Output MUST be a single JSON object:
        {
          "pages": [
            { "page_num": <int>, "events": [
                { "event_type": "...", "timestamp": "...", "preview": "...",
                  "detail": "...", "drug_name": "...", "drug_dosage": "...", "drug_route": "..." },
                ...
            ] },
            ...
          ]
        }

        Include exactly one "pages" entry per input page_num in ascending order.
        No markdown or commentary outside JSON.

        When "pre_extracted" is present: fix misclassifications, enrich previews, and ADD everything
        material the heuristics missed. Do NOT duplicate correctly captured heuristic events verbatim.
    """).strip()

    # Compact prompt for Ollama / small models.
    # Priority-ordered and structured to fit within output budgets while
    # still yielding medically informative previews.
    # preview is a 2-sentence clinical summary (≤240 chars).
    # drug_name is MANDATORY for medication events.
    _SYSTEM_PROMPT_OLLAMA = textwrap.dedent("""
        You are a medical event extractor. Extract events from each page of a patient record.

        PRIORITY ORDER — emit events in this order within each page:
        1. medication (ALWAYS emit; drug_name REQUIRED)
        2. diagnosis
        3. lab
        4. procedure (includes vaccinations/immunizations, imaging, surgery)
        5. symptom
        6. clinical_note (visit notes, assessments, plans)
        7. vital_signs (BP, HR, temp, weight, SpO2)
        8. administrative (release-of-info, consent forms, boilerplate — ONLY if page has no clinical content)

        Fields per event:
        - event_type: medication|diagnosis|lab|procedure|symptom|clinical_note|vital_signs|imaging|immunization|administrative
        - timestamp: YYYY-MM-DD extracted from the page text, or "unknown" if no date is present. NEVER invent a date.
        - preview: A 2-sentence clinical summary (≤240 chars). Sentence 1: WHAT happened (name, value, finding, drug + dose). Sentence 2: WHY / CONTEXT (indication, change rationale, site, ordering clinician, abnormal flag) when the page states it; otherwise omit sentence 2. Never fabricate context.
        - drug_name: REQUIRED for medication — generic name (e.g. "pyridostigmine"). NEVER omit.
        - drug_dosage: medication only, optional — dose as written (e.g. "60 mg daily")
        - drug_route: medication only, optional — oral|IV|IM|SC|topical|inhaled|other

        Output ONLY this JSON (no markdown, no explanation):
        {"pages":[{"page_num":<int>,"events":[
          {"event_type":"medication","timestamp":"2023-05-15","preview":"Started pyridostigmine 60 mg TID for myasthenia gravis. Ordered by Dr. Chen (neurology) at follow-up.","drug_name":"pyridostigmine","drug_dosage":"60 mg TID","drug_route":"oral"},
          {"event_type":"diagnosis","timestamp":"2023-05-15","preview":"Myasthenia gravis confirmed by positive AChR antibody and clinical exam. Recommended initiation of cholinesterase inhibitor therapy."}
        ]},{"page_num":<int>,"events":[]},...]}

        Rules:
        - One entry per input page_num, in order
        - If a page is truly empty or structurally blank → "events": []
        - If a page is boilerplate (release-of-info, page footer, patient-demographics-only) emit ONE "administrative" event summarizing the form type. Do NOT emit "clinical_note" for non-clinical text.
        - NEVER use the event_type "page" or "note" — always pick a medically meaningful type.
        - Do NOT merge events across pages
        - NEVER omit drug_name for any medication event
        - Vaccinations and immunizations are type "procedure" or "immunization", NOT "lab"
        - Timestamps must come from the actual page text — do not copy dates from these instructions
        - If a page has "pre_extracted" data, correct misclassifications and ADD what was missed (symptoms, clinical_notes, procedures); do not duplicate correct heuristic events.
    """).strip()

    _gpt41_extract = bool(force_json_format and _ingestion_is_full_gpt41(model))
    if not force_json_format:
        system_prompt = _SYSTEM_PROMPT_OLLAMA
    elif _gpt41_extract:
        system_prompt = _SYSTEM_PROMPT_GPT41_HIGH_DETAIL
    else:
        system_prompt = _SYSTEM_PROMPT_FULL

    # Build payload — include heuristic skeleton when available so the LLM
    # can correct/supplement rather than extracting from scratch.
    page_dicts = []
    for pn, txt in pages:
        d: Dict[str, Any] = {"page_num": pn, "text": txt}
        if heuristic_results and pn in heuristic_results:
            from server.eoh.heuristic_page_extract import skeleton_for_llm
            skel = skeleton_for_llm(pn, txt, heuristic_results[pn])
            if skel:
                d["pre_extracted"] = skel
        page_dicts.append(d)

    payload = {"pages": page_dicts}
    user_content = json.dumps(payload, ensure_ascii=False)
    input_page_nums = {pn for pn, _ in pages}

    try:
        if force_json_format:
            # OpenAI: GPT-4.1 uses env-tuned completion budget for large graph JSON.
            if _gpt41_extract:
                _max_tok = max(4096, min(INGESTION_GPT41_MAX_OUTPUT_TOKENS, 262_144))
            else:
                _max_tok = min(32768, _PDF_EXTRACTION_OUTPUT_TOKENS_RESERVE + 4096)
            call_kwargs: Dict[str, Any] = dict(
                max_tokens=_max_tok,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            resp = await _llm_chat_completion_async(
                client=client,
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                **call_kwargs,
            )
            raw_content = _safe_get_choice_content(resp) or ""
        elif ollama_native_api:
            # Localhost Ollama: bypass the OpenAI SDK and use httpx directly so
            # that empty-body HTTP 200 responses surface a meaningful error
            # rather than a cryptic JSONDecodeError inside the SDK's Pydantic
            # layer.  Only safe on localhost — remote Ollama (e.g. RTX 4090 over
            # LAN) has shown silent httpx.ReadError failures with this path.
            _max_tok = _ollama_max_predict_tokens(ollama_num_ctx)
            _ollama_url = str(client.base_url).rstrip("/")
            logger.info(
                "Ollama native /api/chat: model=%s  num_ctx=%s  num_predict=%s  pages=%s",
                model, ollama_num_ctx, _max_tok, [p for p, _ in pages],
            )
            raw_content = await _ollama_chat_direct(
                base_url=_ollama_url,
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=_max_tok,
                temperature=0.1,
                num_ctx=ollama_num_ctx,
            )
        else:
            # Remote Ollama (or any non-native Ollama): OpenAI-compat path
            # /v1/chat/completions WITHOUT response_format (grammar-constrained
            # mode is 5-10x slower).  Pass num_ctx and num_predict via
            # extra_body["options"] so Ollama respects our context budget.
            _max_tok = _ollama_max_predict_tokens(ollama_num_ctx)
            _extra: Optional[Dict[str, Any]] = None
            if ollama_num_ctx:
                _extra = {"options": {"num_ctx": ollama_num_ctx, "num_predict": _max_tok}}
            logger.info(
                "Ollama OpenAI-compat /v1/chat/completions: model=%s  num_ctx=%s  num_predict=%s  pages=%s",
                model, ollama_num_ctx, _max_tok, [p for p, _ in pages],
            )
            resp = await _llm_chat_completion_async(
                client=client,
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=_max_tok,
                temperature=0.1,
                extra_body=_extra,
            )
            raw_content = _safe_get_choice_content(resp) or ""

        raw_content = _strip_markdown_fences(raw_content)

        if not raw_content.strip():
            raise ValueError("LLM returned empty content after fence-stripping")

        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError:
            parsed = _repair_truncated_extraction_json(raw_content)

        if not isinstance(parsed, dict):
            raise ValueError("expected JSON object")

        rows = parsed.get("pages")
        if not isinstance(rows, list):
            raise ValueError("missing pages array")

        out: Dict[int, List[Dict[str, Any]]] = {pn: [] for pn, _ in pages}

        for row in rows:
            if not isinstance(row, dict):
                continue
            pn = row.get("page_num")
            if not isinstance(pn, int):
                try:
                    pn = int(pn)
                except (TypeError, ValueError):
                    continue
            evs = row.get("events")
            if not isinstance(evs, list):
                evs = []
            cleaned: List[Dict[str, Any]] = []
            for e in evs:
                if not isinstance(e, dict):
                    continue
                _prev_cap = 2000 if _gpt41_extract else 400
                ev_dict: Dict[str, Any] = {
                    "event_type": str(e.get("event_type", "note")),
                    "timestamp": str(e.get("timestamp", "unknown")),
                    "preview": str(e.get("preview", ""))[:_prev_cap],
                }
                _detail = e.get("detail")
                if _detail and isinstance(_detail, str) and _detail.strip():
                    ev_dict.setdefault("annotations", {})["extraction_detail"] = _detail.strip()[:4000]
                drug = e.get("drug_name")
                if drug and isinstance(drug, str) and drug.strip():
                    ev_dict["drug_name"] = drug.strip()
                dosage = e.get("drug_dosage")
                if dosage and isinstance(dosage, str) and dosage.strip():
                    ev_dict["drug_dosage"] = dosage.strip()[:100]
                route = e.get("drug_route")
                if route and isinstance(route, str) and route.strip():
                    ev_dict["drug_route"] = route.strip().lower()[:30]
                cleaned.append(ev_dict)
            if pn in out:
                out[pn] = cleaned

        # Any input page missing from model output → generic fallback for that page
        for pn, txt in pages:
            if not out[pn]:
                out[pn] = [
                    {
                        "event_type": "administrative",
                        "timestamp": "unknown",
                        "preview": (txt[:200] if txt.strip() else "(no events extracted)"),
                        "event_id": f"pdf_p{pn:04d}_generic",
                    }
                ]
            else:
                for idx, event in enumerate(out[pn]):
                    if "event_id" not in event:
                        event["event_id"] = f"pdf_p{pn:04d}_e{idx:04d}"

        return out

    except Exception as e:
        # Retry with single-page batches when the multi-page batch fails.
        # The most common failure mode is output truncation on dense pages;
        # processing one page at a time keeps the output well within budget.
        if len(pages) > 1:
            logger.warning(
                "Batch extraction failed for pages %s (%s) — retrying %d pages individually",
                [p for p, _ in pages], type(e).__name__, len(pages),
            )
            out: Dict[int, List[Dict[str, Any]]] = {}
            for pn, txt in pages:
                try:
                    single_result = await _extract_events_from_pages_batch(
                        client,
                        [(pn, txt)],
                        model=model,
                        force_json_format=force_json_format,
                        ollama_num_ctx=ollama_num_ctx,
                        ollama_native_api=ollama_native_api,
                        heuristic_results=(
                            {pn: heuristic_results[pn]}
                            if heuristic_results and pn in heuristic_results
                            else None
                        ),
                    )
                    out.update(single_result)
                except Exception as e2:
                    logger.warning(
                        "Single-page retry also failed for page %d: %s",
                        pn, type(e2).__name__,
                    )
                    out[pn] = [{
                        "event_type": "administrative",
                        "timestamp": "unknown",
                        "preview": txt[:200],
                        "event_id": f"pdf_p{pn:04d}_extract_fail",
                    }]
            return out

        # Single-page batch failed — nothing left to split.
        logger.warning(
            "PDF event extraction failed for page %s: %s",
            input_page_nums, type(e).__name__,
        )
        return {
            pn: [
                {
                    "event_type": "administrative",
                    "timestamp": "unknown",
                    "preview": txt[:200],
                    "event_id": f"pdf_p{pn:04d}_extract_fail",
                }
            ]
            for pn, txt in pages
        }


async def _extract_events_from_page_text(
    client: AsyncOpenAI,
    page_text: str,
    page_num: int,
) -> List[Dict[str, Any]]:
    """
    Extract events from PDF page text using LLM extraction.

    **Design Principle:** LLMs are heuristic management infrastructure.
    Rather than maintaining fragile regex patterns and keyword lists,
    delegate event extraction to a capable agent with clear instructions.

    Args:
        client: OpenAI async client
        page_text: Raw text from PDF page
        page_num: Page number for provenance

    Returns:
        List of event dicts with event_type, timestamp, preview, event_id
    """
    if not page_text.strip():
        # Empty page: return generic page event
        return [{
            "event_type": "administrative",
            "timestamp": "unknown",
            "preview": "(empty page)",
            "event_id": f"pdf_p{page_num:04d}_empty",
        }]

    EVENT_EXTRACTION_SYSTEM_PROMPT = textwrap.dedent("""
        You are a precise medical event extraction agent (GPT-5.1 equivalent).
        Your task is to extract structured medical timeline events from patient document pages.

        **Instructions:**
        1. Review the provided page text carefully.
        2. Identify all medically relevant events, including:
           - Diagnoses (confirmed, suspected, ruled out)
           - Medications (started, stopped, changed, listed, allergies)
           - Lab results (tests, values, interpretations)
           - Procedures (surgeries, imaging, interventions)
           - Symptoms (patient-reported complaints)
           - Clinical notes (visit summaries, assessments)
        3. For each event, extract:
           - `event_type`: One of ["diagnosis", "medication", "lab", "procedure", "symptom", "note"]
           - `timestamp`: Date in YYYY-MM-DD format if available, otherwise "unknown"
           - `preview`: A concise 1-2 sentence summary of the event (max 200 chars)
           - `drug_name`: (medication events ONLY) the generic drug name exactly as it
             appears in the text, e.g. "prednisone", "pyridostigmine". Use the generic
             name when both generic and brand are present. REQUIRED; omit for non-medication events.
           - `drug_dosage`: (medication events ONLY, optional) dose string exactly as written,
             e.g. "60 mg TID", "500 mg twice daily". Include when dose is present in text.
           - `drug_route`: (medication events ONLY, optional) route of administration —
             one of oral|IV|IM|SC|topical|inhaled|other. Include when stated or clearly implied.
        4. Output a JSON array of events. Each event must have these exact fields.
        5. If no clear events are present, return an empty array [].
        6. Do NOT hallucinate events. Only extract what is explicitly present.
        7. Preserve all dates exactly as they appear (convert to YYYY-MM-DD if possible).

        **Example Output:**
        ```json
        [
          {
            "event_type": "diagnosis",
            "timestamp": "2023-05-15",
            "preview": "Diagnosed with Myasthenia Gravis based on positive AChR antibody and clinical presentation."
          },
          {
            "event_type": "medication",
            "timestamp": "2023-05-15",
            "preview": "Started Pyridostigmine 60mg TID for myasthenia gravis.",
            "drug_name": "pyridostigmine",
            "drug_dosage": "60 mg TID",
            "drug_route": "oral"
          },
          {
            "event_type": "lab",
            "timestamp": "2023-05-10",
            "preview": "AChR antibody positive (titer 12.5 nmol/L, ref <0.4)."
          }
        ]
        ```

        **Important:**
        - Only output valid JSON.
        - Do not include explanations or commentary.
        - If uncertain about event_type, use "note" as default.
        - If date is ambiguous or partial, use "unknown".
        - For medication events, always include drug_name if a drug is named in the text.
        - Include drug_dosage and drug_route whenever the information is present.
    """)

    payload = {
        "page_num": page_num,
        "page_text": page_text[:4000],  # Limit to 4000 chars to avoid token overflow
    }

    messages = [
        {"role": "system", "content": EVENT_EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]

    try:
        resp = await _llm_chat_completion_async(
            client=client,
            model=EOH_TIMELINE_SUMMARIZER_MODEL,
            messages=messages,
            max_tokens=2048,
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        raw_content = _safe_get_choice_content(resp)
        parsed = json.loads(raw_content)

        # Handle both array and object with "events" key
        if isinstance(parsed, list):
            events = parsed
        elif isinstance(parsed, dict) and "events" in parsed:
            events = parsed["events"]
        else:
            logger.warning(f"Unexpected LLM response format for page {page_num}: {raw_content[:200]}")
            events = []

        # Add event_id to each event
        for idx, event in enumerate(events):
            if "event_id" not in event:
                event["event_id"] = f"pdf_p{page_num:04d}_e{idx:04d}"

        # If no events extracted, create a generic page event
        if not events:
            events = [{
                "event_type": "administrative",
                "timestamp": "unknown",
                "preview": page_text[:200],
                "event_id": f"pdf_p{page_num:04d}_generic",
            }]

        return events

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM event extraction output for page {page_num}: {e}")
        # Fallback: create a generic page event
        return [{
            "event_type": "administrative",
            "timestamp": "unknown",
            "preview": page_text[:200],
            "event_id": f"pdf_p{page_num:04d}_fallback",
        }]
    except Exception as e:
        logger.error(f"Event extraction failed for page {page_num}: {e}")
        # Fallback: create a generic page event
        return [{
            "event_type": "administrative",
            "timestamp": "unknown",
            "preview": page_text[:200],
            "event_id": f"pdf_p{page_num:04d}_error",
        }]


async def populate_vision_from_extracted_pages(
    *,
    vision: PatientTimelineVision,
    extraction_pages: List[Tuple[int, str]],
    ingestion_client: AsyncOpenAI,
    ingestion_model: str,
    ingestion_context_tokens: Optional[int] = None,
    extraction_concurrency: int = 1,
) -> Dict[str, Any]:
    """
    Heuristic skeleton → batched per-page LLM extraction (with heuristic hints) →
    timestamp recovery → single temporal connascence pass → type reclassification →
    graph timestamp sanitize.

    Same algorithm as ``run_eohd_timeline_pdf.py`` / the PDF branch of
    ``summarize_timeline_from_pdf``. Mutates ``vision`` in place; does not write files.
    """
    import time as _time_mod
    from server.eoh.heuristic_page_extract import heuristic_extract_batch

    pid = vision.patient_id

    _base_url_full = str(getattr(ingestion_client, "_base_url", "") or "")
    _is_ollama = (
        "11434" in _base_url_full
        or "localhost" in _base_url_full
        or "127.0.0.1" in _base_url_full
        or "ollama" in _base_url_full.lower()
    )
    _force_json_format: bool = not _is_ollama
    _ollama_num_ctx: Optional[int] = None if _force_json_format else _ollama_num_ctx_default()
    _is_local_ollama = "localhost" in _base_url_full or "127.0.0.1" in _base_url_full
    _ollama_native_api: bool = _is_ollama and _is_local_ollama

    _heur_t0 = _time_mod.perf_counter()
    _heuristic_results = heuristic_extract_batch(extraction_pages)
    _heur_elapsed = _time_mod.perf_counter() - _heur_t0

    _heur_events = sum(len(r.events) for r in _heuristic_results.values())
    _heur_pages_with_date = sum(1 for r in _heuristic_results.values() if r.page_date)
    logger.info(
        "Heuristic pre-extraction [%s]: %d pages in %.0fms — %d events, %d/%d pages with encounter dates",
        pid,
        len(extraction_pages),
        _heur_elapsed * 1000,
        _heur_events,
        _heur_pages_with_date,
        len(extraction_pages),
    )

    _heur_added = 0
    for pn, heur_result in sorted(_heuristic_results.items()):
        if not heur_result.events:
            continue
        heur_event_dicts = []
        for he in heur_result.events:
            d = he.to_dict()
            d["annotations"] = {"heuristic_source": he.source}
            if he.drug_name:
                d["drug_name"] = he.drug_name
                d["annotations"]["drug_name"] = he.drug_name
            if he.drug_dosage:
                d["drug_dosage"] = he.drug_dosage
                d["annotations"]["drug_dosage"] = he.drug_dosage
            if he.drug_route:
                d["drug_route"] = he.drug_route
                d["annotations"]["drug_route"] = he.drug_route
            if he.icd_code:
                d["annotations"]["icd_code"] = he.icd_code
            heur_event_dicts.append(d)
        add_events_from_pdf_page(vision=vision, page_num=pn, events=heur_event_dicts)
        _heur_added += len(heur_event_dicts)

    logger.info("Heuristic events added to vision [%s]: %d (pre-LLM)", pid, _heur_added)

    _page_date_lookup: Dict[int, str] = {
        pn: r.page_date for pn, r in _heuristic_results.items() if r.page_date
    }

    _ctx_tokens = ingestion_context_tokens or _PDF_EXTRACTION_GPT41_MAX_CONTEXT_TOKENS

    _gpt41_ingest = bool(_force_json_format and _ingestion_is_full_gpt41(ingestion_model))

    if _gpt41_ingest and _ctx_tokens >= 500_000:
        # ~60% of context for input page text; system reserve sized for the long GPT-4.1 prompt.
        _sys_r = max(
            _PDF_EXTRACTION_SYSTEM_PROMPT_TOKENS_RESERVE,
            INGESTION_GPT41_SYSTEM_PROMPT_TOKEN_RESERVE,
        )
        _batch_max_chars = int(
            (_ctx_tokens * INGESTION_GPT41_INPUT_FILL_RATIO - _sys_r)
            * _PDF_EXTRACTION_CHARS_PER_TOKEN_ESTIMATE
        )
    elif _ctx_tokens >= 500_000:
        _batch_max_chars = int(
            (
                _ctx_tokens * _PDF_EXTRACTION_CONTEXT_FILL_RATIO
                - _PDF_EXTRACTION_SYSTEM_PROMPT_TOKENS_RESERVE
                - _PDF_EXTRACTION_OUTPUT_TOKENS_RESERVE
            )
            * _PDF_EXTRACTION_CHARS_PER_TOKEN_ESTIMATE
        )
    else:
        # Small-context local models (eoh-llama3.1:8b @ 32k): 60% of context for
        # page text, 30% output, ~10% prompt/margin — mirrors the GPT-4.1 split.
        from server.api.stream_config import (
            INGESTION_OLLAMA_INPUT_FILL_RATIO,
            INGESTION_OLLAMA_SYSTEM_PROMPT_TOKEN_RESERVE,
        )
        _small_input_tokens = max(
            1024,
            int(_ctx_tokens * INGESTION_OLLAMA_INPUT_FILL_RATIO)
            - INGESTION_OLLAMA_SYSTEM_PROMPT_TOKEN_RESERVE,
        )
        _batch_max_chars = _small_input_tokens * _PDF_EXTRACTION_CHARS_PER_TOKEN_ESTIMATE

    _batch_max_chars = max(_batch_max_chars, 8_000)

    _ollama_page_cap = _ollama_max_pages_per_batch()
    _ollama_tok_per_page = _ollama_output_tokens_per_page_estimate()
    if _ctx_tokens >= 500_000:
        if _gpt41_ingest:
            _output_token_cap = INGESTION_GPT41_MAX_OUTPUT_TOKENS
        else:
            _output_token_cap = _PDF_EXTRACTION_OUTPUT_TOKENS_RESERVE
    elif _is_ollama and _ollama_num_ctx is not None:
        # Match actual Ollama num_predict — avoids sizing batches from ctx//2 while
        # generation is capped by _ollama_max_predict_tokens (typically lower).
        _output_token_cap = _ollama_max_predict_tokens(_ollama_num_ctx)
    else:
        _output_token_cap = min(16384, max(4096, _ctx_tokens // 2))
    _max_pages_per_batch: Optional[int] = min(
        _ollama_page_cap,
        max(1, _output_token_cap // _ollama_tok_per_page),
    )
    if _ctx_tokens >= 500_000:
        _max_pages_per_batch = None

    # Chapter-aware batching: a PDF chapter = one Kaiser encounter (one clinical
    # day's visit/lab/message) or one administrative summary section (problem
    # list, current medications, immunizations). The packer keeps chapters
    # intact where possible and only splits an oversize chapter (rare) into
    # contiguous page runs that reference the same chapter_id.
    from server.timeline.pdf_sectionizer import (
        sectionize_pages,
        pack_chapters_into_batches,
        estimate_batch_seconds,
    )

    _chapters = sectionize_pages(extraction_pages)
    _chapter_batches = pack_chapters_into_batches(
        _chapters,
        max_chars=_batch_max_chars,
        max_pages_per_batch=_max_pages_per_batch,
        per_page_overhead_chars=_PDF_EXTRACTION_PER_PAGE_JSON_OVERHEAD_CHARS,
    )
    batches: List[List[Tuple[int, str]]] = [cb.pages for cb in _chapter_batches]
    _primary_chapter_ids: List[str] = [cb.primary_chapter_id for cb in _chapter_batches]
    _chapter_index: Dict[str, Dict[str, Any]] = {
        ch.chapter_id: ch.to_dict() for ch in _chapters
    }
    _ocr_pending_pages: List[int] = []
    for ch in _chapters:
        if ch.ocr_pending_pages:
            _ocr_pending_pages.extend(ch.ocr_pending_pages)

    oh = _PDF_EXTRACTION_PER_PAGE_JSON_OVERHEAD_CHARS
    _eta_total = sum(
        estimate_batch_seconds(len(cb.pages), cb.char_len, model=ingestion_model)
        for cb in _chapter_batches
    )
    logger.info(
        "PDF event extraction [%s]: %d pages → %d chapter(s) → %d batch(es); "
        "~%d input chars/batch cap (%dK-token ctx; model=%s); est total %.0fs; ocr_pending=%d",
        pid,
        len(extraction_pages),
        len(_chapters),
        len(batches),
        _batch_max_chars,
        _ctx_tokens // 1024,
        ingestion_model,
        _eta_total,
        len(_ocr_pending_pages),
    )

    _concurrency = max(1, extraction_concurrency)
    _sem = asyncio.Semaphore(_concurrency)
    enrichment_stats_list: List[Dict[str, Any]] = []

    async def _extract_one(
        b_idx: int, batch: List[Tuple[int, str]]
    ) -> Tuple[int, List[Tuple[int, str]], Dict[int, List[Dict[str, Any]]], int, Optional[str]]:
        batch_chars = sum(len(t) for _, t in batch) + len(batch) * oh
        primary_cid = _primary_chapter_ids[b_idx - 1] if b_idx - 1 < len(_primary_chapter_ids) else None
        logger.info(
            "PDF event extraction batch %d/%d [%s]: %d pages, ~%d chars, chapter=%s",
            b_idx,
            len(batches),
            pid,
            len(batch),
            batch_chars,
            primary_cid,
        )
        batch_heur = (
            {pn: _heuristic_results[pn] for pn, _ in batch if pn in _heuristic_results}
            if _heuristic_results
            else None
        )

        t0 = _time_mod.perf_counter()
        err: Optional[str] = None
        try:
            async with _sem:
                result = await _extract_events_from_pages_batch(
                    ingestion_client,
                    batch,
                    model=ingestion_model,
                    force_json_format=_force_json_format,
                    ollama_num_ctx=_ollama_num_ctx,
                    ollama_native_api=_ollama_native_api,
                    heuristic_results=batch_heur,
                )
        except Exception as _ex:
            logger.warning(
                "PDF extraction batch %d/%d [%s] failed: %s", b_idx, len(batches), pid, _ex
            )
            result = {}
            err = str(_ex)
        elapsed_ms = int((_time_mod.perf_counter() - t0) * 1000)
        return b_idx, batch, result, elapsed_ms, err

    extraction_tasks = [_extract_one(i + 1, batch) for i, batch in enumerate(batches)]
    all_results = await asyncio.gather(*extraction_tasks)

    from server.eoh.patient_timeline_vision import _infer_temporal_connascence

    _stat_total_events = 0
    _stat_extract_fail_events = 0  # LLM/JSON failed after retries (*_extract_fail)
    _stat_batch_empty_stubs = 0  # gather-level empty batch (*_batch_empty)
    _stat_generic_stub_events = 0  # *_generic — model omitted page
    _stat_ts_recovered = 0

    for b_idx, batch, page_to_events, elapsed_ms, batch_err in sorted(all_results, key=lambda x: x[0]):
        # Whole-batch failure used to return {} and silently skip pages — never add vision events.
        if not page_to_events:
            logger.warning(
                "PDF batch %d/%d [%s]: empty extraction result (%s) — per-page stubs",
                b_idx,
                len(batches),
                pid,
                batch_err or "no error detail",
            )
            page_to_events = {
                pn: [
                    {
                        "event_type": "administrative",
                        "timestamp": "unknown",
                        "preview": (txt[:200] if txt and txt.strip() else "(batch empty)"),
                        "event_id": f"pdf_p{pn:04d}_batch_empty",
                    }
                ]
                for pn, txt in batch
            }

        ts_scrubbed = _sanitize_timestamps_batch(page_to_events)
        batch_event_count = sum(len(evts) for evts in page_to_events.values())
        _stat_total_events += batch_event_count

        # Tag every event in this batch with its chapter_id so the graph,
        # the Postgres timeline rows, and the SSE stream can group events by
        # clinical encounter/summary section.
        _batch_primary_cid = (
            _primary_chapter_ids[b_idx - 1] if b_idx - 1 < len(_primary_chapter_ids) else None
        )
        _batch_chapter_meta = (
            _chapter_index.get(_batch_primary_cid) if _batch_primary_cid else None
        )

        for evts in page_to_events.values():
            for ev in evts:
                eid = str(ev.get("event_id", ""))
                if eid.endswith("_extract_fail"):
                    _stat_extract_fail_events += 1
                elif eid.endswith("_batch_empty"):
                    _stat_batch_empty_stubs += 1
                elif eid.endswith("_generic"):
                    _stat_generic_stub_events += 1
                elif eid.endswith("_batch_error"):
                    # legacy id from older runs / manual edits
                    _stat_extract_fail_events += 1
                if _batch_primary_cid:
                    ann = ev.setdefault("annotations", {})
                    ann.setdefault("chapter_id", _batch_primary_cid)
                    if _batch_chapter_meta:
                        if _batch_chapter_meta.get("encounter_date"):
                            ann.setdefault("encounter_date", _batch_chapter_meta["encounter_date"])
                        if _batch_chapter_meta.get("encounter_type"):
                            ann.setdefault("encounter_type", _batch_chapter_meta["encounter_type"])
                        if _batch_chapter_meta.get("section_header"):
                            ann.setdefault("section_header", _batch_chapter_meta["section_header"])
                        ann.setdefault("chapter_kind", _batch_chapter_meta.get("kind"))

        for page_num, evts in page_to_events.items():
            page_date = _page_date_lookup.get(page_num)
            if not page_date:
                continue
            for ev in evts:
                ts = ev.get("timestamp", "")
                if ts.lower() in ("unknown", "", "n/a", "none"):
                    from server.utils.parse_date import extract_date_from_text

                    preview_date = extract_date_from_text(ev.get("preview", ""))
                    if preview_date:
                        ev["timestamp"] = preview_date.strftime("%Y-%m-%d")
                        ev.setdefault("annotations", {})["timestamp_source"] = "preview_regex"
                    else:
                        ev["timestamp"] = page_date
                        ev.setdefault("annotations", {})["timestamp_source"] = "heuristic_page_date"
                    _stat_ts_recovered += 1

        pn_first = batch[0][0]
        pn_last = batch[-1][0]
        enrichment_stats_list.append(
            {
                "batch_index": b_idx - 1,
                "page_range": f"{pn_first}-{pn_last}",
                "input_chars": sum(len(t) for _, t in batch),
                "events_extracted": batch_event_count,
                "edges_extracted": 0,
                "elapsed_ms": elapsed_ms,
                "error": batch_err,
            }
        )

        ts_samples: list[str] = []
        for evts in page_to_events.values():
            for ev in evts:
                t = ev.get("timestamp", "")
                if t and t != "unknown" and len(ts_samples) < 6:
                    ts_samples.append(t)
        _stub_ev = sum(
            1
            for evs in page_to_events.values()
            for e in evs
            if str(e.get("event_id", "")).endswith(
                ("_extract_fail", "_batch_empty", "_generic")
            )
        )
        _all_stub = _stub_ev == batch_event_count and batch_event_count > 0
        log_msg = "Batch %d/%d [%s] extracted %d events across %d pages; samples: %s"
        if _all_stub:
            log_msg += " — stubs only (LLM/JSON did not produce events; dates often from heuristics)"
        if ts_scrubbed:
            log_msg += f"; scrubbed {ts_scrubbed} prompt-bleed timestamp(s)"
        logger.info(
            log_msg,
            b_idx,
            len(batches),
            pid,
            batch_event_count,
            len(page_to_events),
            ts_samples,
        )

        events_before_graph = len(vision.events)
        for page_num in sorted(page_to_events.keys()):
            add_events_from_pdf_page(
                vision=vision, page_num=page_num, events=page_to_events[page_num]
            )
        added_this_batch = len(vision.events) - events_before_graph

        logger.info(
            "PatientTimelineVision [%s]: after batch %d/%d — total events=%d (+%d this batch); "
            "edges=%d (unchanged until final connascence)",
            pid,
            b_idx,
            len(batches),
            len(vision.events),
            added_this_batch,
            vision.count_edges(),
        )

    _avg_batch_ms = sum(r[3] for r in all_results) / max(len(all_results), 1)
    if _avg_batch_ms < 120 and len(batches) > 200:
        logger.warning(
            "[%s] Mean batch time %.0fms with %d batches — if using Ollama, check "
            "OLLAMA_BASE_URL / model name; very fast batches often mean failed HTTP calls.",
            pid,
            _avg_batch_ms,
            len(batches),
        )

    logger.info(
        "═══ PDF extraction complete [%s]: %d batches, %d graph events added from LLM batches "
        "(%d extract_fail, %d batch_empty, %d generic), %d timestamps recovered (heuristic/preview)",
        pid,
        len(batches),
        _stat_total_events,
        _stat_extract_fail_events,
        _stat_batch_empty_stubs,
        _stat_generic_stub_events,
        _stat_ts_recovered,
    )
    if _stat_extract_fail_events + _stat_batch_empty_stubs >= max(1, _stat_total_events // 2):
        logger.warning(
            "[%s] Most LLM batch output was stubs — check Ollama is reachable (OLLAMA_BASE_URL), "
            "model exists (ollama list), and INGESTION_MODEL matches the tag.",
            pid,
        )

    _infer_temporal_connascence(vision, window_days=7)

    n_reclassified = _reclassify_event_types(vision)
    if n_reclassified:
        logger.info("[%s] PDF event type reclassification: %d events", pid, n_reclassified)

    n_ts_recovered_preview = _recover_timestamps_from_preview(vision)
    if n_ts_recovered_preview:
        logger.info(
            "[%s] PDF timestamp recovery (Noted on: regex): %d events",
            pid, n_ts_recovered_preview,
        )

    _page_to_chapter = _build_page_to_chapter_index(_chapters)
    n_ch_stamped = _backfill_chapter_annotations(vision, _chapter_index, _page_to_chapter)
    if n_ch_stamped:
        logger.info("[%s] PDF chapter back-stamp: %d events", pid, n_ch_stamped)

    reduced_stats = _infer_reduced_graph_connascence(vision)
    logger.info(
        "[%s] PDF reduced-graph connascence: chapter=%d encounter=%d drug=%d icd=%d day=%d",
        pid,
        reduced_stats["same_chapter"],
        reduced_stats["same_encounter"],
        reduced_stats["same_drug"],
        reduced_stats["same_icd"],
        reduced_stats["same_day"],
    )

    n_ts_scrubbed = _sanitize_timestamps_graph(vision)
    if n_ts_scrubbed:
        logger.info("[%s] PDF timestamp sanity: %d scrubbed", pid, n_ts_scrubbed)

    return {
        "heuristic_events_added": _heur_added,
        "batches": len(batches),
        "chapters": len(_chapters),
        "chapter_plan": [ch.to_dict() for ch in _chapters],
        "ocr_pending_pages": list(_ocr_pending_pages),
        "llm_events_total": _stat_total_events,
        "reduced_graph_connascence": reduced_stats,
        "timestamps_recovered_from_preview": n_ts_recovered_preview,
        "extract_fail_events": _stat_extract_fail_events,
        "batch_empty_stubs": _stat_batch_empty_stubs,
        "generic_stub_events": _stat_generic_stub_events,
        "timestamps_recovered": _stat_ts_recovered,
        "reclassified": n_reclassified,
        "graph_timestamps_scrubbed": n_ts_scrubbed,
        "enrichment_stats": enrichment_stats_list,
        "ingestion_model": ingestion_model,
    }


async def stream_populate_vision_from_extracted_pages(
    *,
    vision: PatientTimelineVision,
    extraction_pages: List[Tuple[int, str]],
    ingestion_client: AsyncOpenAI,
    ingestion_model: str,
    ingestion_context_tokens: Optional[int] = None,
) -> AsyncIterator[Dict[str, Any]]:
    """
    Streaming (async-generator) variant of ``populate_vision_from_extracted_pages``.

    Emits a sequence of ``dict`` frames suitable for SSE:
      * ``{"type": "plan", ...}``           — chapter plan + ETA + model meta
      * ``{"type": "heuristic", ...}``      — regex pre-scan stats
      * ``{"type": "chapter_start", ...}``  — before each LLM batch
      * ``{"type": "chapter_events", ...}`` — events added from one batch
      * ``{"type": "chapter_done", ...}``   — elapsed + accumulated totals
      * ``{"type": "done", ...}``           — final stats after graph finalize
      * ``{"type": "error", ...}``          — fatal failure (generator continues)

    Each frame contains plain, JSON-serializable fields. The caller is
    responsible for turning them into ``text/event-stream`` wire format.

    Unlike the non-streaming sibling, this function processes batches
    sequentially so the UI receives chapters in chronological order.
    """
    import time as _time_mod
    from server.eoh.heuristic_page_extract import heuristic_extract_batch
    from server.eoh.patient_timeline_vision import _infer_temporal_connascence
    from server.timeline.pdf_sectionizer import (
        sectionize_pages,
        pack_chapters_into_batches,
        estimate_batch_seconds,
    )

    pid = vision.patient_id

    _base_url_full = str(getattr(ingestion_client, "_base_url", "") or "")
    _is_ollama = (
        "11434" in _base_url_full
        or "localhost" in _base_url_full
        or "127.0.0.1" in _base_url_full
        or "ollama" in _base_url_full.lower()
    )
    _force_json_format: bool = not _is_ollama
    _ollama_num_ctx: Optional[int] = None if _force_json_format else _ollama_num_ctx_default()
    _is_local_ollama = "localhost" in _base_url_full or "127.0.0.1" in _base_url_full
    _ollama_native_api: bool = _is_ollama and _is_local_ollama

    # --- heuristic pre-scan (same skeleton as non-streaming sibling) ----------
    _heur_t0 = _time_mod.perf_counter()
    _heuristic_results = heuristic_extract_batch(extraction_pages)
    _heur_elapsed_ms = int((_time_mod.perf_counter() - _heur_t0) * 1000)
    _heur_added = 0
    for pn, heur_result in sorted(_heuristic_results.items()):
        if not heur_result.events:
            continue
        heur_event_dicts = []
        for he in heur_result.events:
            d = he.to_dict()
            d["annotations"] = {"heuristic_source": he.source}
            if he.drug_name:
                d["drug_name"] = he.drug_name
                d["annotations"]["drug_name"] = he.drug_name
            if he.drug_dosage:
                d["drug_dosage"] = he.drug_dosage
                d["annotations"]["drug_dosage"] = he.drug_dosage
            if he.drug_route:
                d["drug_route"] = he.drug_route
                d["annotations"]["drug_route"] = he.drug_route
            if he.icd_code:
                d["annotations"]["icd_code"] = he.icd_code
            heur_event_dicts.append(d)
        add_events_from_pdf_page(vision=vision, page_num=pn, events=heur_event_dicts)
        _heur_added += len(heur_event_dicts)

    _page_date_lookup: Dict[int, str] = {
        pn: r.page_date for pn, r in _heuristic_results.items() if r.page_date
    }

    # --- plan ------------------------------------------------------------------
    _gpt41_ingest = bool(_force_json_format and _ingestion_is_full_gpt41(ingestion_model))
    _ctx_tokens = ingestion_context_tokens or _PDF_EXTRACTION_GPT41_MAX_CONTEXT_TOKENS

    if _gpt41_ingest and _ctx_tokens >= 500_000:
        _sys_r = max(
            _PDF_EXTRACTION_SYSTEM_PROMPT_TOKENS_RESERVE,
            INGESTION_GPT41_SYSTEM_PROMPT_TOKEN_RESERVE,
        )
        _batch_max_chars = int(
            (_ctx_tokens * INGESTION_GPT41_INPUT_FILL_RATIO - _sys_r)
            * _PDF_EXTRACTION_CHARS_PER_TOKEN_ESTIMATE
        )
    elif _ctx_tokens >= 500_000:
        _batch_max_chars = int(
            (
                _ctx_tokens * _PDF_EXTRACTION_CONTEXT_FILL_RATIO
                - _PDF_EXTRACTION_SYSTEM_PROMPT_TOKENS_RESERVE
                - _PDF_EXTRACTION_OUTPUT_TOKENS_RESERVE
            )
            * _PDF_EXTRACTION_CHARS_PER_TOKEN_ESTIMATE
        )
    else:
        from server.api.stream_config import (
            INGESTION_OLLAMA_INPUT_FILL_RATIO,
            INGESTION_OLLAMA_SYSTEM_PROMPT_TOKEN_RESERVE,
        )
        _small_input_tokens = max(
            1024,
            int(_ctx_tokens * INGESTION_OLLAMA_INPUT_FILL_RATIO)
            - INGESTION_OLLAMA_SYSTEM_PROMPT_TOKEN_RESERVE,
        )
        _batch_max_chars = _small_input_tokens * _PDF_EXTRACTION_CHARS_PER_TOKEN_ESTIMATE
    _batch_max_chars = max(_batch_max_chars, 8_000)

    _max_pages_per_batch: Optional[int]
    if _ctx_tokens >= 500_000:
        _max_pages_per_batch = None
    else:
        _max_pages_per_batch = _ollama_max_pages_per_batch()

    chapters = sectionize_pages(extraction_pages)
    chapter_batches = pack_chapters_into_batches(
        chapters,
        max_chars=_batch_max_chars,
        max_pages_per_batch=_max_pages_per_batch,
        per_page_overhead_chars=_PDF_EXTRACTION_PER_PAGE_JSON_OVERHEAD_CHARS,
    )
    chapter_index: Dict[str, Dict[str, Any]] = {ch.chapter_id: ch.to_dict() for ch in chapters}
    ocr_pending: List[int] = []
    for ch in chapters:
        if ch.ocr_pending_pages:
            ocr_pending.extend(ch.ocr_pending_pages)

    per_batch_eta = [
        estimate_batch_seconds(len(b.pages), b.char_len, model=ingestion_model)
        for b in chapter_batches
    ]
    total_eta = sum(per_batch_eta)

    logger.info(
        "PDF streaming extraction [%s]: %d pages → %d chapters → %d batches "
        "(%dK-ctx; model=%s; total ETA ~%.0fs; ocr_pending=%d)",
        pid,
        len(extraction_pages),
        len(chapters),
        len(chapter_batches),
        _ctx_tokens // 1024,
        ingestion_model,
        total_eta,
        len(ocr_pending),
    )

    yield {
        "type": "plan",
        "patient_id": pid,
        "ingestion_model": ingestion_model,
        "is_gpt41": _gpt41_ingest,
        "context_tokens": _ctx_tokens,
        "total_pages": len(extraction_pages),
        "total_chapters": len(chapters),
        "total_batches": len(chapter_batches),
        "total_eta_seconds": round(total_eta, 1),
        "heuristic_events_added": _heur_added,
        "ocr_pending_pages": ocr_pending,
        "chapters": [ch.to_dict() for ch in chapters],
        "batches": [
            {
                "batch_index": i,
                "primary_chapter_id": b.primary_chapter_id,
                "chapter_ids": list(b.chapter_ids),
                "pages": [pn for pn, _ in b.pages],
                "char_len": b.char_len,
                "est_seconds": round(eta, 1),
                "split_note": b.split_note,
            }
            for i, (b, eta) in enumerate(zip(chapter_batches, per_batch_eta))
        ],
    }

    yield {
        "type": "heuristic",
        "patient_id": pid,
        "events_added": _heur_added,
        "elapsed_ms": _heur_elapsed_ms,
        "pages_with_date": len(_page_date_lookup),
    }

    # Build and emit an early "regex skeleton" graph before any LLM batch work.
    # This gives the UI a fast, clinically structured baseline (chapterized +
    # temporal connascence over regex/heuristic events) instead of appearing
    # frozen while waiting for chapter 1 extraction to complete.
    _skel_t0 = _time_mod.perf_counter()
    _infer_temporal_connascence(vision, window_days=7)
    _skel_elapsed_ms = int((_time_mod.perf_counter() - _skel_t0) * 1000)
    yield {
        "type": "skeleton_ready",
        "patient_id": pid,
        "total_pages": len(extraction_pages),
        "total_chapters": len(chapters),
        "regex_heuristic_events": len(vision.events),
        "temporal_edges": vision.count_edges(),
        "elapsed_ms": _skel_elapsed_ms,
        "message": "Regex skeleton ready (chapterized + temporal connascence). Continuing LLM enrichment...",
    }

    # --- iterate batches sequentially -----------------------------------------
    _stat_total_events = 0
    _stat_extract_fail_events = 0
    _stat_batch_empty_stubs = 0
    _stat_generic_stub_events = 0
    _stat_ts_recovered = 0
    enrichment_stats_list: List[Dict[str, Any]] = []

    for i, (batch, eta) in enumerate(zip(chapter_batches, per_batch_eta)):
        primary_cid = batch.primary_chapter_id
        chapter_meta = chapter_index.get(primary_cid, {})

        yield {
            "type": "chapter_start",
            "batch_index": i,
            "total_batches": len(chapter_batches),
            "primary_chapter_id": primary_cid,
            "chapter_ids": list(batch.chapter_ids),
            "chapter_label": chapter_meta.get("label"),
            "pages": [pn for pn, _ in batch.pages],
            "char_len": batch.char_len,
            "est_seconds": round(eta, 1),
            "split_note": batch.split_note,
        }

        batch_heur = {pn: _heuristic_results[pn] for pn, _ in batch.pages if pn in _heuristic_results}
        t0 = _time_mod.perf_counter()
        err: Optional[str] = None
        try:
            page_to_events = await _extract_events_from_pages_batch(
                ingestion_client,
                batch.pages,
                model=ingestion_model,
                force_json_format=_force_json_format,
                ollama_num_ctx=_ollama_num_ctx,
                ollama_native_api=_ollama_native_api,
                heuristic_results=batch_heur,
            )
        except Exception as _ex:
            logger.warning(
                "PDF streaming batch %d/%d [%s] failed: %s",
                i + 1, len(chapter_batches), pid, _ex,
            )
            page_to_events = {}
            err = str(_ex)

        elapsed_ms = int((_time_mod.perf_counter() - t0) * 1000)

        if not page_to_events:
            page_to_events = {
                pn: [
                    {
                        "event_type": "administrative",
                        "timestamp": "unknown",
                        "preview": (txt[:200] if txt and txt.strip() else "(batch empty)"),
                        "event_id": f"pdf_p{pn:04d}_batch_empty",
                    }
                ]
                for pn, txt in batch.pages
            }

        _sanitize_timestamps_batch(page_to_events)
        batch_event_count = sum(len(evts) for evts in page_to_events.values())
        _stat_total_events += batch_event_count

        for evts in page_to_events.values():
            for ev in evts:
                eid = str(ev.get("event_id", ""))
                if eid.endswith("_extract_fail"):
                    _stat_extract_fail_events += 1
                elif eid.endswith("_batch_empty"):
                    _stat_batch_empty_stubs += 1
                elif eid.endswith("_generic"):
                    _stat_generic_stub_events += 1
                # Tag with chapter context
                ann = ev.setdefault("annotations", {})
                ann.setdefault("chapter_id", primary_cid)
                if chapter_meta.get("encounter_date"):
                    ann.setdefault("encounter_date", chapter_meta["encounter_date"])
                if chapter_meta.get("encounter_type"):
                    ann.setdefault("encounter_type", chapter_meta["encounter_type"])
                if chapter_meta.get("section_header"):
                    ann.setdefault("section_header", chapter_meta["section_header"])
                ann.setdefault("chapter_kind", chapter_meta.get("kind"))

        for page_num, evts in page_to_events.items():
            page_date = _page_date_lookup.get(page_num)
            if not page_date:
                continue
            for ev in evts:
                ts = ev.get("timestamp", "")
                if ts.lower() in ("unknown", "", "n/a", "none"):
                    from server.utils.parse_date import extract_date_from_text

                    preview_date = extract_date_from_text(ev.get("preview", ""))
                    if preview_date:
                        ev["timestamp"] = preview_date.strftime("%Y-%m-%d")
                        ev.setdefault("annotations", {})["timestamp_source"] = "preview_regex"
                    else:
                        ev["timestamp"] = page_date
                        ev.setdefault("annotations", {})["timestamp_source"] = "heuristic_page_date"
                    _stat_ts_recovered += 1

        events_before_graph = len(vision.events)
        new_event_snapshots: List[Dict[str, Any]] = []
        for page_num in sorted(page_to_events.keys()):
            add_events_from_pdf_page(
                vision=vision, page_num=page_num, events=page_to_events[page_num]
            )
            for ev in page_to_events[page_num]:
                ev_view = {
                    "page": page_num,
                    "event_type": ev.get("event_type"),
                    "timestamp": ev.get("timestamp"),
                    "preview": (ev.get("preview") or "")[:280],
                    "drug_name": ev.get("drug_name"),
                    "event_id": ev.get("event_id"),
                }
                new_event_snapshots.append(ev_view)
        added_this_batch = len(vision.events) - events_before_graph

        enrichment_stats_list.append(
            {
                "batch_index": i,
                "primary_chapter_id": primary_cid,
                "pages": [pn for pn, _ in batch.pages],
                "events_extracted": batch_event_count,
                "events_added": added_this_batch,
                "elapsed_ms": elapsed_ms,
                "error": err,
            }
        )

        yield {
            "type": "chapter_events",
            "batch_index": i,
            "primary_chapter_id": primary_cid,
            "chapter_label": chapter_meta.get("label"),
            "events_extracted": batch_event_count,
            "events_added": added_this_batch,
            "events_preview": new_event_snapshots[:40],
            "elapsed_ms": elapsed_ms,
        }
        yield {
            "type": "chapter_done",
            "batch_index": i,
            "primary_chapter_id": primary_cid,
            "elapsed_ms": elapsed_ms,
            "error": err,
            "total_graph_events": len(vision.events),
            "total_graph_edges": vision.count_edges(),
        }

    _infer_temporal_connascence(vision, window_days=7)
    n_reclassified = _reclassify_event_types(vision)
    n_ts_recovered_preview = _recover_timestamps_from_preview(vision)
    page_to_chapter = _build_page_to_chapter_index(chapters)
    n_ch_stamped = _backfill_chapter_annotations(vision, chapter_index, page_to_chapter)
    reduced_stats = _infer_reduced_graph_connascence(vision)
    n_ts_scrubbed = _sanitize_timestamps_graph(vision)

    logger.info(
        "PDF streaming extraction [%s]: reduced-graph connascence "
        "chapter=%d encounter=%d drug=%d icd=%d day=%d; "
        "preview-ts recovered=%d; chapter back-stamped=%d",
        pid,
        reduced_stats["same_chapter"],
        reduced_stats["same_encounter"],
        reduced_stats["same_drug"],
        reduced_stats["same_icd"],
        reduced_stats["same_day"],
        n_ts_recovered_preview,
        n_ch_stamped,
    )

    yield {
        "type": "done",
        "patient_id": pid,
        "chapters": len(chapters),
        "batches": len(chapter_batches),
        "llm_events_total": _stat_total_events,
        "heuristic_events_added": _heur_added,
        "extract_fail_events": _stat_extract_fail_events,
        "batch_empty_stubs": _stat_batch_empty_stubs,
        "generic_stub_events": _stat_generic_stub_events,
        "timestamps_recovered": _stat_ts_recovered,
        "timestamps_recovered_from_preview": n_ts_recovered_preview,
        "reclassified": n_reclassified,
        "graph_timestamps_scrubbed": n_ts_scrubbed,
        "chapter_backstamped": n_ch_stamped,
        "reduced_graph_connascence": reduced_stats,
        "total_graph_events": len(vision.events),
        "total_graph_edges": vision.count_edges(),
        "ocr_pending_pages": ocr_pending,
        "enrichment_stats": enrichment_stats_list,
        "ingestion_model": ingestion_model,
    }


async def summarize_timeline_from_pdf(
    client: AsyncOpenAI,
    question: str,
    pdf_path: str,
    password: Optional[str] = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    pool: Any | None = None,
    patient_id: str = "session_patient",
    graph_out_path: Optional[str] = None,
    artifact_dir: Optional[str] = None,
    extraction_mode: str = PDF_EXTRACTION_MODE_LITE,
    ingestion_client: Optional[AsyncOpenAI] = None,
    ingestion_model: str = INGESTION_MODEL,
    ingestion_context_tokens: Optional[int] = None,
    extraction_concurrency: int = 1,
    use_claude: bool = False,
    summarizer_model: str | None = None,
    claude_scope: Optional[str] = None,
    skip_summarization: bool = False,
) -> TimelineSummaries:
    """
    Import and summarize a timeline PDF for session-only use.

    Extraction modes
    ----------------
    ``"lite"`` (default)
        Graph event extraction covers the first 200 pages, last 200 pages, and
        400 randomly sampled pages from the middle (~800 pages total, ~4-5 LLM
        calls).  Fast and cheap; the full timeline text still flows through the
        narrative summarizer unchanged.  More graph events can be added
        incrementally when the timeline is queried in EoHD.

    ``"full"``
        All pages are sent through the per-page LLM event extractor (~23 calls
        for a 4,000-page record).  Produces a much denser graph but costs
        significantly more tokens and time.

    All data is session-only:
    - No writes to rag_corpus or ehr.patient_timeline
    - Password deleted immediately after decryption
    - Timeline text stays in memory only

    Args:
        client: OpenAI async client
        question: Question for EoHD investigation
        pdf_path: Path to timeline PDF
        password: Optional decryption password (will prompt if needed)
        max_tokens: Max tokens for summarization
        pool: Optional DB pool (for PatientTimelineVision session graph)
        patient_id: Patient ID for session (default: "session_patient")
        graph_out_path: If set, write the final PatientTimelineVision graph (JSON)
            to this path after summarization and optional enrichment.
        artifact_dir: If set, write the session vision snapshot and gap/synthesis
            sidecar JSON files under this directory instead of ``/tmp``.
        extraction_mode: ``"lite"`` (default) or ``"full"``.
        ingestion_client: Optional separate AsyncOpenAI client for PDF event
            extraction and connascence LLM passes.  Pass an Ollama client here
            to run ingestion locally at zero API cost while keeping ``client``
            pointed at OpenAI for the narrative summarization.  Defaults to
            ``client`` when not provided.
        ingestion_model: Model name used for ingestion calls (extraction +
            connascence).  Ignored when ``ingestion_client`` is ``None``.
            Default: ``INGESTION_MODEL`` env var (falls back to
            ``EOH_TIMELINE_SUMMARIZER_MODEL``).
        ingestion_context_tokens: Override the context window size (in tokens)
            used to compute batch sizes for PDF event extraction.  Defaults to
            ``_PDF_EXTRACTION_GPT41_MAX_CONTEXT_TOKENS`` (1M).  Set to e.g.
            32_768 for local 8B models that have a 128K context but cannot
            sustain a full-context KV cache without timing out.
        skip_summarization: If True, stop after extraction + graph enrichment
            (no narrative summarization). Returns TimelineSummaries with only
            vision_path and graph_out_path populated.

    Returns:
        TimelineSummaries object ready for EoHD execution
    """
    # Resolve ingestion client — fall back to the main client when not supplied.
    _ingestion_client: AsyncOpenAI = ingestion_client if ingestion_client is not None else client
    _ingestion_model: str = ingestion_model

    # Grammar-constrained JSON sampling (response_format=json_object) is 5-10x
    # slower on llama.cpp / Ollama than unconstrained generation.  Detect Ollama
    # by inspecting the client's base URL and disable the constraint — the
    # prompts explicitly request JSON so output quality is maintained.
    _base_url_full = str(getattr(_ingestion_client, "_base_url", "") or "")
    _is_ollama = (
        "11434" in _base_url_full
        or "localhost" in _base_url_full
        or "127.0.0.1" in _base_url_full
        or "ollama" in _base_url_full.lower()
    )
    _force_json_format: bool = not _is_ollama
    # For Ollama, num_ctx defaults lower (OLLAMA_NUM_CTX, default 16384) — smaller
    # KV often yields cleaner extraction JSON from 8B models; tune per GPU.
    _ollama_num_ctx: Optional[int] = None if _force_json_format else _ollama_num_ctx_default()
    # Native /api/chat is only used for localhost Ollama (validated on M2 Ultra).
    # Remote Ollama (e.g. RTX 4090 at 192.168.x.x) uses the OpenAI-compat
    # /v1/chat/completions path with num_ctx/num_predict passed via extra_body
    # options.  The native path caused silent httpx.ReadError failures on remote
    # setups, while the compat path is stable across network boundaries.
    _is_local_ollama = (
        "localhost" in _base_url_full or "127.0.0.1" in _base_url_full
    )
    _ollama_native_api: bool = _is_ollama and _is_local_ollama
    from pathlib import Path
    from pypdf import PdfReader
    import getpass
    
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    logger.info("Timeline PDF import (session-only): %s", pdf_file.name)

    # Step 1: Read bytes and decrypt if needed
    pdf_bytes = pdf_file.read_bytes()
    from io import BytesIO
    reader = PdfReader(BytesIO(pdf_bytes))
    was_encrypted = reader.is_encrypted

    if was_encrypted:
        if password is None:
            logger.info("PDF is encrypted; prompting for password")
            password = getpass.getpass("Enter PDF decryption password: ")

        try:
            if reader.decrypt(password) == 0:
                raise ValueError("Incorrect password")
            logger.info("PDF decrypted successfully")
        except Exception as e:
            raise ValueError(f"Failed to decrypt PDF: {e}")
        finally:
            if password:
                del password

    # Step 2: Resilient text extraction — pypdf first, pypdfium2 fallback.
    #
    # Some PDFs have broken xref/page-tree structures that crash pypdf at
    # len(reader.pages) or page.extract_text() while still rendering fine
    # in browsers.  We handle this in two tiers:
    #   - Tier A (pypdf OK): per-page pypdf, pypdfium2 fallback on empty/error.
    #   - Tier B (pypdf broken): full pypdfium2 extraction from one open doc.
    # In both tiers the pypdfium2 document is opened ONCE to avoid O(n²) cost.

    page_entries: List[Tuple[int, str]] = []  # (1-based page num, text)

    # Try to walk pypdf's page tree — this is where TypeError surfaces.
    pypdf_tree_ok = False
    total_pdf_pages = 0
    try:
        total_pdf_pages = len(reader.pages)
        pypdf_tree_ok = True
        logger.info("Extracting text from %d pages (pypdf)", total_pdf_pages)
    except Exception as tree_err:
        logger.warning(
            "pypdf page tree broken for %s (%s: %s) — switching to pypdfium2",
            pdf_file.name, type(tree_err).__name__, tree_err,
        )

    # Open pypdfium2 once for the entire document.
    _pdfium_doc = None
    try:
        import pypdfium2 as pdfium
        _pdfium_doc = pdfium.PdfDocument(pdf_bytes)
        if not pypdf_tree_ok:
            total_pdf_pages = len(_pdfium_doc)
            logger.info("Extracting text from %d pages (pypdfium2 full)", total_pdf_pages)
    except ImportError:
        _pdfium_doc = None
        if not pypdf_tree_ok:
            raise RuntimeError(
                "pypdf page tree is broken and pypdfium2 is not installed. "
                "Install it: pip install 'pypdfium2>=4.30'"
            )
    except Exception as pdfium_open_err:
        logger.warning("pypdfium2 failed to open %s: %s", pdf_file.name, pdfium_open_err)
        _pdfium_doc = None
        if not pypdf_tree_ok:
            raise

    def _pdfium_text(idx: int) -> str:
        if _pdfium_doc is None:
            return ""
        try:
            p = _pdfium_doc[idx]
            tp = p.get_textpage()
            t = (tp.get_text_bounded() or "").strip().replace("\x00", "")
            tp.close(); p.close()
            return t
        except Exception as e:
            logger.warning("pypdfium2 failed on page %d: %s", idx + 1, e)
            return ""

    try:
        if pypdf_tree_ok:
            for idx, page in enumerate(reader.pages):
                try:
                    text = (page.extract_text() or "").strip().replace("\x00", "")
                except Exception:
                    text = ""
                if not text:
                    text = _pdfium_text(idx)
                if text:
                    pdf_page = idx + 1
                    page_entries.append((pdf_page, text))
        else:
            for idx in range(total_pdf_pages):
                text = _pdfium_text(idx)
                if text:
                    page_entries.append((idx + 1, text))
    finally:
        if _pdfium_doc is not None:
            _pdfium_doc.close()

    chunks = [f"=== Page {pg} ===\n{txt}" for pg, txt in page_entries]
    timeline_text = "\n\n".join(chunks)
    logger.info(
        "Timeline PDF extracted: %d non-empty pages, %d chars",
        len(page_entries),
        len(timeline_text),
    )

    # Step 2a: Build PatientTimelineVision for provenance tracking
    logger.info("Building PatientTimelineVision for %s", patient_id)

    vision = seed_from_structured_probe_snapshot(
        patient_id=patient_id,
        snapshot_counts={
            "total_pages": len(page_entries),
            "total_chars": len(timeline_text),
        },
        dx_examples=[],
        lab_examples=[],
        note_examples=[],
        session_only=True,
    )

    # Page selection for graph event extraction.
    # Note: timeline_text always covers ALL pages for the narrative summarizer;
    # only the graph extraction is tiered.
    if extraction_mode == PDF_EXTRACTION_MODE_FULL:
        extraction_pages = page_entries
        mode_label = "full"
    else:
        extraction_pages = _select_pages_lite(page_entries)
        mode_label = (
            f"lite (head={_LITE_HEAD_PAGES}, tail={_LITE_TAIL_PAGES}, "
            f"mc_middle={_LITE_MC_MIDDLE_PAGES})"
        )

    logger.info(
        "PDF graph extraction mode: %s — %d/%d pages selected for event extraction",
        mode_label,
        len(extraction_pages),
        len(page_entries),
    )

    await populate_vision_from_extracted_pages(
        vision=vision,
        extraction_pages=extraction_pages,
        ingestion_client=_ingestion_client,
        ingestion_model=_ingestion_model,
        ingestion_context_tokens=ingestion_context_tokens,
        extraction_concurrency=extraction_concurrency,
    )

    # Save vision snapshot (session_only still true; path is for sharing / gap artifacts)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if artifact_dir:
        ad = Path(artifact_dir).expanduser().resolve()
        ad.mkdir(parents=True, exist_ok=True)
        vision_path = str(ad / f"patient_timeline_vision_{patient_id}_{ts}.json")
    else:
        vision_path = f"/tmp/patient_timeline_vision_{patient_id}_{ts}.json"
    vision.save(vision_path, force=True)
    logger.info(
        "PatientTimelineVision saved: %s (events=%d, edges=%d)",
        vision_path,
        len(vision.events),
        vision.count_edges()
    )

    # PatientTimelineSnapshot — the "git ls-files" of the graph.
    # Lightweight shape-only JSON that agents read first.
    snapshot_path = vision_path.replace("_vision_", "_snapshot_").replace(".json", ".json")
    try:
        snap = vision.snapshot()
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(snap, f, indent=2, ensure_ascii=False)
        type_line = ", ".join(f"{k}={v['count']}" for k, v in snap["types"].items())
        logger.info(
            "PatientTimelineSnapshot saved: %s (%d nodes, %d edges — %s)",
            snapshot_path, snap["total_events"], snap["total_edges"], type_line,
        )
        print(f"\nTimeline snapshot: {snapshot_path}", flush=True)
    except Exception:
        logger.exception("Failed to write PatientTimelineSnapshot")

    pdf_graph_enrichment: Optional[Dict[str, Any]] = None
    if vision.events:
        logger.info(
            "PDF pipeline: gap/synthesis/connascence on loaded graph (before narrative summary)"
        )
        try:
            pdf_graph_enrichment = await _run_timeline_enrichment_gap_synthesis_connascence(
                client=client,
                vision=vision,
                patient_id=patient_id,
                pool=pool,
                question=question,
                existing_context=_existing_context_rows_from_vision(vision),
                artifact_base_path=vision_path,
                phase_label="pdf_pre_summary",
                ingestion_client=_ingestion_client,
                ingestion_model=_ingestion_model,
                force_json_format=_force_json_format,
            )
            gap_p = pdf_graph_enrichment.get("gap_analysis_path")
            if gap_p:
                print(f"\nGap analysis saved: {gap_p}", flush=True)
            syn_p = pdf_graph_enrichment.get("synthesis_path")
            if syn_p:
                print(f"\nEnrichment synthesis saved: {syn_p}", flush=True)
        except Exception:
            logger.exception(
                "PDF pre-summary gap/synthesis/connascence failed; continuing with base graph"
            )
        vision.save(vision_path, force=True)
        logger.info(
            "PatientTimelineVision after pre-summary enrichment: events=%d edges=%d",
            len(vision.events),
            vision.count_edges(),
        )

    # Early exit: extraction-only mode (no narrative summarization).
    if skip_summarization:
        logger.info(
            "PDF pipeline: skip_summarization=True — returning extraction-only results "
            "(events=%d, edges=%d)",
            len(vision.events),
            vision.count_edges(),
        )
        extract_only = TimelineSummaries(
            timeline_summary="",
            meds_and_labs_snapshot="",
        )
        extract_only.vision_path = vision_path
        if pdf_graph_enrichment:
            extract_only.timeline_enrichment = {"pdf_pre_summary_enrichment": pdf_graph_enrichment}
        if graph_out_path:
            out_p = Path(graph_out_path).expanduser().resolve()
            out_p.parent.mkdir(parents=True, exist_ok=True)
            vision.save(str(out_p), force=True)
            extract_only.graph_out_path = str(out_p)
            logger.info(
                "PatientTimelineVision graph export: %s (events=%d, edges=%d)",
                str(out_p), len(vision.events), vision.count_edges(),
            )
        return extract_only

    # Step 3: Pass to standard timeline summarizer
    # This handles single-pass vs. hierarchical vs. RAG automatically
    logger.info(
        "PDF pipeline Step 3: summarize_timeline_for_eoh (timeline_chars=%d, pages=%d, rag=%s)",
        len(timeline_text),
        len(page_entries),
        bool(pool),
    )
    summaries = await summarize_timeline_for_eoh(
        client=client,
        question=question,
        timeline_text=timeline_text,
        max_tokens=max_tokens,
        pool=pool,
        patient_id=patient_id,
        use_timeline_rag=True if pool else False,
        timeline_vision=vision,
        use_claude=use_claude,
        summarizer_model=summarizer_model,
        claude_scope=claude_scope,
    )

    summaries.vision_path = vision_path
    enrichment_out: Dict[str, Any] = {}
    if pdf_graph_enrichment:
        enrichment_out["pdf_pre_summary_enrichment"] = pdf_graph_enrichment
    if summaries.timeline_enrichment:
        enrichment_out["probe_rag_enrichment"] = summaries.timeline_enrichment
    summaries.timeline_enrichment = enrichment_out if enrichment_out else None

    logger.info("Timeline PDF import complete with PatientTimelineVision: %s", vision_path)

    if graph_out_path:
        out_p = Path(graph_out_path).expanduser().resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        vision.save(str(out_p), force=True)
        summaries.graph_out_path = str(out_p)
        logger.info(
            "PatientTimelineVision graph export: %s (events=%d, edges=%d)",
            summaries.graph_out_path,
            len(vision.events),
            vision.count_edges(),
        )
        print(f"\nTimeline graph written: {summaries.graph_out_path}", flush=True)

    return summaries


_PROMPT_BLEED_DATES = frozenset({
    "2019-03-01",
    "YYYY-MM-DD",
})


def _sanitize_timestamps_batch(page_to_events: Dict[int, List[Dict[str, Any]]]) -> int:
    """
    Scrub prompt-bleed and placeholder timestamps from extraction output
    before events are added to the graph.  Returns the number of timestamps
    replaced with "unknown".
    """
    fixed = 0
    for evts in page_to_events.values():
        for ev in evts:
            ts = ev.get("timestamp", "")
            if ts in _PROMPT_BLEED_DATES:
                ev["timestamp"] = "unknown"
                fixed += 1
    return fixed


def _sanitize_timestamps_graph(vision: "PatientTimelineVision") -> int:
    """
    Post-hoc sweep over the full graph to scrub prompt-bleed dates that
    were missed during batch processing (e.g., from prior runs).
    """
    fixed = 0
    for event in vision.events.values():
        if event.timestamp in _PROMPT_BLEED_DATES:
            event.timestamp = "unknown"
            fixed += 1
    return fixed


def _reclassify_event_types(vision: "PatientTimelineVision") -> int:
    """
    Keyword-based post-processing pass: upgrade events whose event_type is
    ambiguous ("page", "note", "unknown", "administrative") to a more specific
    clinical type based on preview text.

    Also normalizes the legacy bucket names — any remaining "page" or bare
    "note" becomes either a specific clinical type (preferred) or
    "administrative" / "clinical_note" so the exported graph never ships with
    an event_type that isn't medically meaningful.

    Returns the number of events reclassified.
    """
    # Ordered by specificity — first match wins.
    _PATTERNS: List[tuple] = [
        ("lab", re.compile(
            r"\b(?:level|result|count|value|mg/dl|mmol|ng/ml|iu/l|meq/l|"
            r"hemoglobin|hgb|wbc|creatinine|sodium|potassium|glucose|"
            r"albumin|bilirubin|alt|ast|ldh|ck|troponin|ferritin|"
            r"a1c|psa|tsh|t4|inr|pt|ptt|esr|crp|ana|anca|"
            r"urinalysis|culture|sensitivity|pcr|titer|panel)\b",
            re.I,
        )),
        ("diagnosis", re.compile(
            r"\b(?:diagnos(?:is|ed)|assessment|impression|icd[-\s]?\d|"
            r"disease|disorder|syndrome|cancer|carcinoma|tumor|lymphoma|"
            r"failure|insufficiency|stenosis|fibrosis|hepatitis|cirrhosis|"
            r"myasthenia|lupus|scleroderma|sarcoidosis|vasculitis|"
            r"infection|sepsis|pneumonia|covid|influenza)\b",
            re.I,
        )),
        ("medication", re.compile(
            r"\b(?:prescribed|started|initiated|dose|dosage|mg|tablet|"
            r"capsule|injection|infusion|iv |oral|topical|inhaler|"
            r"prednisone|methotrexate|azathioprine|cyclosporine|"
            r"rituximab|mycophenolate|hydroxychloroquine|tacrolimus|"
            r"antibiotic|steroid|medication|drug|therapy|treatment)\b",
            re.I,
        )),
        ("procedure", re.compile(
            r"\b(?:surgery|operation|procedure|resection|biopsy|"
            r"catheterization|dialysis|transplant|intubation|bronchoscopy|"
            r"endoscopy|colonoscopy|cystoscopy|thoracentesis|"
            r"paracentesis|lumbar puncture|bone marrow|pacemaker|"
            r"tracheostomy|debridement|repair|revision)\b",
            re.I,
        )),
        ("symptom", re.compile(
            r"\b(?:pain|fever|fatigue|dyspnea|shortness of breath|"
            r"nausea|vomiting|diarrhea|constipation|cough|edema|"
            r"weakness|swelling|rash|pruritus|headache|dizziness|"
            r"syncope|palpitations|chest (?:pain|tightness)|"
            r"complaint|symptom|presenting)\b",
            re.I,
        )),
        ("visit", re.compile(
            r"\b(?:visit|appointment|admitted|admission|discharged|"
            r"discharge|clinic|outpatient|inpatient|emergency|"
            r"follow[- ]up|consultation|referral|transfer|"
            r"hospitalization|icu|icu stay)\b",
            re.I,
        )),
        ("imaging", re.compile(
            r"\b(?:x[-\s]?ray|ct scan|mri|ultrasound|echo|"
            r"echocardiogram|pet scan|nuclear|scintigraphy|"
            r"radiograph|imaging|scan|sonogram)\b",
            re.I,
        )),
    ]

    RECLASSIFY_FROM = {"page", "unknown", "note", "administrative"}
    reclassified = 0

    _ADMIN_RE = re.compile(
        r"\b(?:release of medical information|authorization to release|"
        r"consent for|advance (?:care )?directive|living will|hipaa|"
        r"power of attorney|demographic|registration|billing|insurance|"
        r"page \d+ of \d+|continued\b)",
        re.I,
    )

    for event in vision.events.values():
        if event.event_type not in RECLASSIFY_FROM:
            continue
        text = (event.preview or "").lower()
        if not text:
            # No text to classify. Demote legacy "page"/"unknown" to
            # "administrative" so downstream analytics never sees "page".
            if event.event_type in ("page", "unknown", "note"):
                event.event_type = "administrative"
                reclassified += 1
            continue
        matched = False
        for new_type, pattern in _PATTERNS:
            if pattern.search(text):
                event.event_type = new_type
                matched = True
                reclassified += 1
                break
        if matched:
            continue
        if _ADMIN_RE.search(text):
            if event.event_type != "administrative":
                event.event_type = "administrative"
                reclassified += 1
            continue
        # Still ambiguous: if the preview looks like prose (≥40 chars and has
        # some letters), treat it as a clinical_note rather than leaving it
        # as "page"/"unknown"/bare "note".
        if len(text) >= 40 and re.search(r"[a-z]{4,}", text):
            if event.event_type != "clinical_note":
                event.event_type = "clinical_note"
                reclassified += 1
        elif event.event_type in ("page", "unknown", "note"):
            event.event_type = "administrative"
            reclassified += 1

    _VACCINE_RE = re.compile(
        r"\b(?:vaccin|immuniz|inoculat|covid.{0,8}(?:dose|shot|booster)|"
        r"influenza.{0,8}(?:shot|vaccine)|tdap|shingrix|prevnar|pneumovax|"
        r"moderna|pfizer|biontech|janssen|flu shot|hepatitis [ab].{0,8}vaccine|"
        r"mmr|varicella vaccine|hpv vaccine|zostavax)\b",
        re.I,
    )
    for event in vision.events.values():
        if event.event_type != "lab":
            continue
        text = (event.preview or "").lower()
        if text and _VACCINE_RE.search(text):
            event.event_type = "immunization"
            reclassified += 1

    return reclassified


def _parse_ts(ts_str: str) -> Optional["datetime"]:
    """Thin wrapper → canonical ``parse_clinical_date``."""
    from server.utils.parse_date import parse_clinical_date
    return parse_clinical_date(ts_str)


# ---------------------------------------------------------------------------
# Reduced-graph connascence passes
# ---------------------------------------------------------------------------
#
# Strategy, not cleverness: each pass groups events by a clinically meaningful
# key (chapter, encounter, same-drug, same-ICD, same-day) and emits pairwise
# edges within each group. The algorithm is dumb pairwise-within-bucket; the
# intelligence is in the choice of key. Large buckets collapse to a star
# topology (one hub → N members) to avoid O(n²) edge bloat.
#
# Returns a dict of {pass_name: edges_added} for logging / SSE.
# ---------------------------------------------------------------------------

_ICD_CODE_RX = re.compile(r"\[([A-Z]\d{2}(?:\.[0-9A-Za-z]+)?)\]")
_NOTED_ON_RX = re.compile(r"\bNoted\s+on[:\s]+(\d{1,2}/\d{1,2}/\d{2,4})", re.I)
_STAR_THRESHOLD = 8  # Buckets with > N events emit star edges instead of full clique.


def _emit_bucket_edges(
    vision: "PatientTimelineVision",
    bucket_key: str,
    members: List[str],
    kind: str,
) -> int:
    """Emit connascence edges for a bucket of ≥2 event IDs.

    Small buckets get a full clique. Large buckets collapse to a star around
    the earliest-timestamped member (or the first member if no timestamps) to
    keep edge counts bounded.
    """
    if len(members) < 2:
        return 0

    if len(members) > _STAR_THRESHOLD:
        # Star topology — pick a hub (earliest real timestamp, then first).
        def _sort_key(eid: str) -> Tuple[int, str]:
            ev = vision.events.get(eid)
            ts = (ev.timestamp if ev else "") or ""
            if ts and ts.lower() not in ("unknown", "n/a", ""):
                return (0, ts)
            return (1, eid)

        ordered = sorted(members, key=_sort_key)
        hub, spokes = ordered[0], ordered[1:]
        edges = 0
        for spoke in spokes:
            vision.add_edge(
                source_event_id=hub,
                target_event_id=spoke,
                connascence_type=kind,
                discovered_by=f"{kind}:star",
                metadata={"group": bucket_key, "topology": "star"},
            )
            edges += 1
        return edges

    # Full clique for small buckets.
    edges = 0
    for a, b in itertools.combinations(sorted(members), 2):
        vision.add_edge(
            source_event_id=a,
            target_event_id=b,
            connascence_type=kind,
            discovered_by=f"{kind}:clique",
            metadata={"group": bucket_key},
        )
        edges += 1
    return edges


def _infer_reduced_graph_connascence(
    vision: "PatientTimelineVision",
) -> Dict[str, int]:
    """Run all reduced-graph connascence passes. Strategic, not clever.

    Each pass groups events by a clinically meaningful key and emits edges
    within each group. Edges are distinct connascence kinds so the graph UI
    can filter/weight them independently.

    Passes:
      - same_chapter       : annotations.chapter_id
      - same_encounter     : annotations.encounter_date (fallback to chapter_id's encounter_date)
      - same_drug          : annotations.drug_name.lower() — medication continuity
      - same_icd           : [Ann.nn] ICD-10 code in preview — condition threads
      - same_day           : timestamp[:10] — procedural bundles
      - temporal_7d        : already emitted by ``_infer_temporal_connascence``
                             earlier in the pipeline; not repeated here.
    """
    from collections import defaultdict

    by_chapter: Dict[str, List[str]] = defaultdict(list)
    by_encounter: Dict[str, List[str]] = defaultdict(list)
    by_drug: Dict[str, List[str]] = defaultdict(list)
    by_icd: Dict[str, List[str]] = defaultdict(list)
    by_day: Dict[str, List[str]] = defaultdict(list)

    for eid, ev in vision.events.items():
        ann = ev.annotations or {}
        ch = ann.get("chapter_id")
        if ch:
            by_chapter[str(ch)].append(eid)
        enc = ann.get("encounter_date")
        if enc:
            by_encounter[str(enc)].append(eid)
        if ev.event_type == "medication":
            dn = ann.get("drug_name")
            if dn and isinstance(dn, str):
                by_drug[dn.strip().lower()].append(eid)
        code = ann.get("icd_code")
        if not code:
            m = _ICD_CODE_RX.search(ev.preview or "")
            if m:
                code = m.group(1)
        if code:
            by_icd[str(code).upper()].append(eid)
        ts = (ev.timestamp or "").strip()
        if ts and ts.lower() not in ("unknown", "n/a"):
            day = ts[:10]
            if re.match(r"\d{4}-\d{2}-\d{2}$", day):
                by_day[day].append(eid)

    stats: Dict[str, int] = {
        "same_chapter": 0,
        "same_encounter": 0,
        "same_drug": 0,
        "same_icd": 0,
        "same_day": 0,
    }
    for key, members in by_chapter.items():
        stats["same_chapter"] += _emit_bucket_edges(vision, key, members, "same_chapter")
    for key, members in by_encounter.items():
        stats["same_encounter"] += _emit_bucket_edges(vision, key, members, "same_encounter")
    for key, members in by_drug.items():
        stats["same_drug"] += _emit_bucket_edges(vision, key, members, "same_drug")
    for key, members in by_icd.items():
        stats["same_icd"] += _emit_bucket_edges(vision, key, members, "same_icd")
    for key, members in by_day.items():
        stats["same_day"] += _emit_bucket_edges(vision, key, members, "same_day")

    return stats


def _backfill_chapter_annotations(
    vision: "PatientTimelineVision",
    chapter_index: Dict[str, Dict[str, Any]],
    page_to_chapter: Dict[int, str],
) -> int:
    """Stamp chapter_id / encounter_* / chapter_kind / section_header on any
    event that lacks them, using its ``annotations.pdf_page`` → chapter map.

    Heuristic-only events (added during the regex skeleton phase) don't know
    their chapter at insertion time; this pass closes the loop so reduced-graph
    ``same_chapter`` / ``same_encounter`` connascence can find them.
    """
    stamped = 0
    for ev in vision.events.values():
        ann = ev.annotations
        if ann.get("chapter_id"):
            continue
        pn = ann.get("pdf_page")
        if not isinstance(pn, int):
            continue
        cid = page_to_chapter.get(pn)
        if not cid:
            continue
        meta = chapter_index.get(cid) or {}
        ann["chapter_id"] = cid
        if meta.get("encounter_date"):
            ann.setdefault("encounter_date", meta["encounter_date"])
        if meta.get("encounter_type"):
            ann.setdefault("encounter_type", meta["encounter_type"])
        if meta.get("section_header"):
            ann.setdefault("section_header", meta["section_header"])
        if meta.get("kind"):
            ann.setdefault("chapter_kind", meta["kind"])
        stamped += 1
    return stamped


def _build_page_to_chapter_index(chapters: List[Any]) -> Dict[int, str]:
    """Build a page_num → chapter_id lookup from a list of ``PdfChapter``."""
    idx: Dict[int, str] = {}
    for ch in chapters:
        for pn in getattr(ch, "pages", None) or []:
            if isinstance(pn, int):
                idx[pn] = ch.chapter_id
    return idx


def _recover_timestamps_from_preview(vision: "PatientTimelineVision") -> int:
    """Dumb post-pass regex: lift 'Noted on: MM/DD/YYYY' dates from preview text
    into ``timestamp`` when the current timestamp is missing.

    The Problem-List page of an EHR dump stamps onset dates inline (e.g.
    ``"ANEMIA [D64.9] ... Noted on: 04/06/2017"``) but the LLM leaves the
    event with ``timestamp: "unknown"`` because there is no top-level date on
    the page. This post-pass reclaims those dates.
    """
    from server.utils.parse_date import parse_clinical_date

    recovered = 0
    for ev in vision.events.values():
        ts = (ev.timestamp or "").strip().lower()
        if ts and ts not in ("unknown", "n/a", ""):
            continue
        m = _NOTED_ON_RX.search(ev.preview or "")
        if not m:
            continue
        dt = parse_clinical_date(m.group(1))
        if not dt:
            continue
        ev.timestamp = dt.strftime("%Y-%m-%d")
        ev.annotations.setdefault("timestamp_source", "noted_on_regex")
        recovered += 1
    return recovered


async def _enrich_timeline_vision_connascence(
    vision: PatientTimelineVision,
    client: Any,
    question: str,
    model: str = INGESTION_MODEL,
    force_json_format: bool = True,
) -> PatientTimelineVision:
    """
    Connascence enrichment — RUBRIC v0.2.

    Mechanical rules (no LLM):
      Rule 1: Temporal (≤7 days all-type, 7-14 days cross-type only, max 10 neighbors/event)
      Rule 4: Treatment (med → lab/symptom/note 0-60 days)

    LLM rules (batched per type):
      Rule 2: Diagnostic — GPT-4.1 links diagnosis/procedure/symptom events
               describing the same condition.
      Rule 3: Lab trend — GPT-4.1 links repeated measurements of the same test.
    """
    from server.eoh.patient_timeline_vision import (
        CONNASCENCE_TEMPORAL,
        CONNASCENCE_DIAGNOSTIC,
        CONNASCENCE_TREATMENT,
        CONNASCENCE_LAB_TREND,
    )

    if not vision.events:
        return vision

    events_list = list(vision.events.values())

    # -----------------------------------------------------------------------
    # RULE 1: Temporal connascence — two windows, neighbor-capped
    # -----------------------------------------------------------------------
    # Narrow windows: the incremental 7-day pass during extraction already
    # produces dense same-episode linkage.  This post-extraction pass adds
    # cross-type bridges up to 14 days and keeps the per-event degree bounded
    # so the graph does not degenerate into a near-complete graph for dense
    # hospitalisation periods.
    TEMPORAL_SHORT_DAYS = 7     # same-episode tight linkage (same as extraction pass)
    TEMPORAL_CROSS_DAYS = 14    # cross-type bridge (replaces the former 30/90-day episode window)
    MAX_TEMPORAL_NEIGHBORS = 10 # hard cap per event — prevents O(n²) explosion

    dated: List[tuple] = []
    for e in events_list:
        dt = _parse_ts(e.timestamp)
        if dt is not None:
            dated.append((dt, e))
    dated.sort(key=lambda x: x[0])

    for i, (dt_a, ev_a) in enumerate(dated):
        for dt_b, ev_b in dated[i + 1:]:
            delta = (dt_b - dt_a).days
            if delta > TEMPORAL_CROSS_DAYS:
                break  # sorted — nothing further will qualify
            already_a = len(ev_a.connascence.get(CONNASCENCE_TEMPORAL, []))
            already_b = len(ev_b.connascence.get(CONNASCENCE_TEMPORAL, []))
            if already_a >= MAX_TEMPORAL_NEIGHBORS and already_b >= MAX_TEMPORAL_NEIGHBORS:
                continue  # both events already saturated
            if delta <= TEMPORAL_SHORT_DAYS:
                ev_a.add_connascence(CONNASCENCE_TEMPORAL, ev_b.event_id)
                ev_b.add_connascence(CONNASCENCE_TEMPORAL, ev_a.event_id)
            elif ev_a.event_type != ev_b.event_type:
                # 7-14 day cross-type bridge (diagnosis↔lab, medication↔symptom, etc.)
                ev_a.add_connascence(CONNASCENCE_TEMPORAL, ev_b.event_id)
                ev_b.add_connascence(CONNASCENCE_TEMPORAL, ev_a.event_id)

    logger.info("Connascence RULE 1 complete: %d temporal edges", vision.count_edges())

    # -----------------------------------------------------------------------
    # RULE 4: Treatment connascence (mechanical)
    # -----------------------------------------------------------------------
    MED_TYPES = {"medication", "med", "rx", "drug", "prescription"}
    RESPONSE_TYPES = {"lab", "symptom", "note", "imaging"}
    TREATMENT_WINDOW_DAYS = 60  # extended from 30 to catch slower drug responses

    med_dated = [(dt, e) for dt, e in dated if e.event_type in MED_TYPES]
    resp_dated = [(dt, e) for dt, e in dated if e.event_type in RESPONSE_TYPES]

    for med_dt, med_ev in med_dated:
        for resp_dt, resp_ev in resp_dated:
            delta_days = (resp_dt - med_dt).days
            if delta_days < 0:
                continue
            if delta_days > TREATMENT_WINDOW_DAYS:
                break
            med_ev.add_connascence(CONNASCENCE_TREATMENT, resp_ev.event_id)
            resp_ev.add_connascence(CONNASCENCE_TREATMENT, med_ev.event_id)

    logger.info(
        "Connascence RULE 4 complete: %d total edges after treatment pass",
        vision.count_edges(),
    )

    # -----------------------------------------------------------------------
    # RULES 2 & 3: LLM-based diagnostic + lab_trend (batched)
    # -----------------------------------------------------------------------
    try:
        vision = await _infer_llm_connascence_batched(
            vision=vision,
            client=client,
            question=question,
            model=model,
            force_json_format=force_json_format,
        )
    except Exception:
        logger.exception("LLM connascence inference failed; continuing with mechanical edges only")

    logger.info(
        "Connascence enrichment complete (RUBRIC v0.2): %d total edges across %d events",
        vision.count_edges(),
        len(vision.events),
    )
    return vision


async def _infer_llm_connascence_batched(
    vision: PatientTimelineVision,
    client: Any,
    question: str,
    batch_size: int = 300,
    model: str = INGESTION_MODEL,
    force_json_format: bool = True,
) -> PatientTimelineVision:  # also mutates vision.metadata["degradation"]
    """
    Batched LLM connascence inference for diagnostic and lab_trend edges.

    Runs one set of batched calls per type:
      - diagnostic: diagnosis + procedure + symptom events
      - lab_trend:  lab events

    Each batch is capped at batch_size events. Multiple batches are run
    sequentially per type if the event count exceeds batch_size.
    """
    from pathlib import Path
    from server.eoh.patient_timeline_vision import (
        CONNASCENCE_DIAGNOSTIC,
        CONNASCENCE_LAB_TREND,
    )

    rubric_path = Path(__file__).parent / "PATIENT_TIMELINE_CONNASCENCE_RUBRIC.md"
    try:
        rubric_text = rubric_path.read_text(encoding="utf-8")
    except Exception:
        logger.warning("Could not load connascence rubric; skipping LLM inference")
        return vision

    # Degradation receipt — written into vision.metadata so it survives serialization.
    degradation: Dict[str, Any] = vision.metadata.setdefault("degradation", {})
    degradation.setdefault("connascence_batches_failed", 0)
    degradation.setdefault("connascence_batches_failed_detail", [])

    type_buckets = {
        CONNASCENCE_DIAGNOSTIC: [
            e for e in vision.events.values()
            if e.event_type in ("diagnosis", "procedure", "symptom", "flare")
        ],
        CONNASCENCE_LAB_TREND: [
            e for e in vision.events.values()
            if e.event_type == "lab"
        ],
    }

    total_llm_edges = 0

    for conn_type, bucket in type_buckets.items():
        if not bucket:
            continue

        # Sort chronologically where possible
        _DT_MIN_UTC = datetime.min.replace(tzinfo=timezone.utc)
        bucket.sort(key=lambda e: (_parse_ts(e.timestamp) or _DT_MIN_UTC))

        # Split into batches
        batches = [bucket[i: i + batch_size] for i in range(0, len(bucket), batch_size)]
        logger.info(
            "LLM connascence %s: %d events → %d batch(es)", conn_type, len(bucket), len(batches)
        )

        for batch_idx, batch in enumerate(batches):
            events_payload = [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type,
                    "timestamp": e.timestamp,
                    "preview": (e.preview or "")[:250],
                }
                for e in batch
            ]

            system_prompt = (
                f"You are a medical timeline connascence analyst (RUBRIC v0.2).\n\n"
                f"{rubric_text}\n\n"
                f"TASK: Identify '{conn_type}' edges between the events provided.\n"
                f"Patient context: {question[:300]}\n\n"
                f"OUTPUT FORMAT — return a JSON object:\n"
                f'{{"edges": [{{"event_a_id": "...", "event_b_id": "...", '
                f'"type": "{conn_type}", "reasoning": "..."}}]}}\n\n'
                f"RULES:\n"
                f"1. Only return type='{conn_type}' edges.\n"
                f"2. Only link events if they CLEARLY meet the rubric criteria.\n"
                f"3. Precision over recall — no hallucinations.\n"
                f"4. If no clear edges exist, return: {{\"edges\": []}}\n"
            )

            user_content = json.dumps(
                {
                    "task": f"infer_{conn_type}_edges",
                    "batch": f"{batch_idx + 1}/{len(batches)}",
                    "event_count": len(events_payload),
                    "events": events_payload,
                },
                cls=DateTimeJSONEncoder,
            )

            try:
                conn_call_kwargs: Dict[str, Any] = dict(
                    max_tokens=16_384,
                    temperature=0.0,
                )
                if force_json_format:
                    conn_call_kwargs["response_format"] = {"type": "json_object"}

                resp = await chat_completion_async(
                    client=client,
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    **conn_call_kwargs,
                )
                if iscoroutine(resp):
                    resp = await resp

                raw = _safe_get_choice_content(resp)
                # Gracefully handle truncated JSON: extract any complete edge
                # objects that were emitted before the token limit was hit.
                data: Dict[str, Any] = {}
                if raw:
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        # Attempt partial recovery — collect complete {...} objects
                        # from the "edges" array before the truncation point.
                        import re as _re
                        partial_edges = _re.findall(
                            r'\{[^{}]*"event_a_id"[^{}]*"event_b_id"[^{}]*\}', raw
                        )
                        if partial_edges:
                            recovered = []
                            for pe in partial_edges:
                                try:
                                    recovered.append(json.loads(pe))
                                except json.JSONDecodeError:
                                    pass
                            if recovered:
                                logger.warning(
                                    "LLM connascence %s batch %d: JSON truncated; "
                                    "recovered %d/%d+ edges via partial parse",
                                    conn_type, batch_idx + 1, len(recovered), len(partial_edges),
                                )
                                data = {"edges": recovered}
                            else:
                                logger.warning(
                                    "LLM connascence %s batch %d: JSON truncated and "
                                    "partial recovery found no complete edge objects; skipping",
                                    conn_type, batch_idx + 1,
                                )
                        else:
                            logger.warning(
                                "LLM connascence %s batch %d: JSON parse failed; skipping",
                                conn_type, batch_idx + 1,
                            )
                edges = data.get("edges") or []

                if not isinstance(edges, list):
                    logger.warning(
                        "LLM connascence %s batch %d: unexpected response shape; skipping",
                        conn_type, batch_idx + 1,
                    )
                    continue

                batch_edges_added = 0
                for edge in edges:
                    a_id = edge.get("event_a_id")
                    b_id = edge.get("event_b_id")
                    etype = edge.get("type")
                    if not a_id or not b_id or etype != conn_type:
                        continue
                    if a_id not in vision.events or b_id not in vision.events:
                        continue
                    vision.events[a_id].add_connascence(conn_type, b_id)
                    vision.events[b_id].add_connascence(conn_type, a_id)
                    batch_edges_added += 1

                total_llm_edges += batch_edges_added
                logger.info(
                    "LLM connascence %s batch %d/%d: +%d edges",
                    conn_type, batch_idx + 1, len(batches), batch_edges_added,
                )

            except Exception:
                logger.exception(
                    "LLM connascence %s batch %d/%d failed; skipping batch",
                    conn_type, batch_idx + 1, len(batches),
                )
                degradation["connascence_batches_failed"] += 1
                degradation["connascence_batches_failed_detail"].append({
                    "conn_type": conn_type,
                    "batch": batch_idx + 1,
                    "of": len(batches),
                    "events_in_batch": len(batch),
                })

    if degradation["connascence_batches_failed"] > 0:
        logger.warning(
            "LLM connascence degraded: %d batch(es) failed — graph is incomplete. "
            "See vision.metadata['degradation'] for details.",
            degradation["connascence_batches_failed"],
        )

    logger.info("LLM connascence complete: +%d edges total", total_llm_edges)
    return vision


def _split_uniform_timeline_chunks(text: str, *, target_chars: int, max_chunks: int) -> List[str]:
    """Split plain text into up to max_chunks segments, each ~target_chars (last may be short)."""
    n = len(text)
    if n == 0:
        return []
    if n <= target_chars:
        return [text]
    chunks_needed = (n + target_chars - 1) // target_chars
    if chunks_needed <= max_chunks:
        return [text[i : i + target_chars] for i in range(0, n, target_chars)]
    base = n // max_chunks
    rem = n % max_chunks
    out: List[str] = []
    pos = 0
    for k in range(max_chunks):
        sz = base + (1 if k < rem else 0)
        out.append(text[pos : pos + sz])
        pos += sz
    return out


def _split_timeline_into_chunks(
    timeline_text: str,
    *,
    target_chars: int,
    max_chunks_floor: int,
) -> List[str]:
    """
    Map/reduce segments for huge timelines when DB RAG is unavailable (e.g. PDF-only import).

    Splits on ``=== Page N ===`` when present; otherwise fixed-size slices. Segment count
    scales with timeline length up to HIERARCHICAL_MAX_CHUNKS_CAP.
    """
    text = (timeline_text or "").strip()
    if not text:
        return []

    total = len(text)
    min_segments = max(1, (total + target_chars - 1) // target_chars)
    max_chunks = min(HIERARCHICAL_MAX_CHUNKS_CAP, max(max_chunks_floor, min_segments))

    page_blocks = re.split(r"(?m)(?=^=== Page \d+ ===\s*$)", text)
    page_blocks = [b.strip() for b in page_blocks if b.strip()]

    if len(page_blocks) <= 1:
        return _split_uniform_timeline_chunks(text, target_chars=target_chars, max_chunks=max_chunks)

    chunks: List[str] = []
    cur: List[str] = []
    cur_len = 0

    for b in page_blocks:
        extra = len(b) + (2 if cur else 0)
        if cur and cur_len + extra > target_chars and len(chunks) < max_chunks - 1:
            chunks.append("\n\n".join(cur))
            cur = [b]
            cur_len = len(b)
        else:
            cur.append(b)
            cur_len += extra

    if cur:
        chunks.append("\n\n".join(cur))

    while len(chunks) > max_chunks:
        chunks[-2] = chunks[-2] + "\n\n" + chunks[-1]
        chunks.pop()

    return chunks


# ---------------------------------------------------------------------------
# Graph context helper for reduce step
# ---------------------------------------------------------------------------

def _compact_graph_for_reduce(
    vision: "PatientTimelineVision",
    max_chars: int = 60_000,
) -> Dict[str, Any]:
    """
    Serialize the enriched PatientTimelineVision into a compact, LLM-readable
    dict grouped by event_type.

    Structure returned:
      {
        "event_counts": {"diagnosis": N, "lab": N, ...},
        "events_by_type": {
          "diagnosis": [{"ts": ..., "preview": ..., "connascence": {...}}, ...],
          ...
        },
        "edges": [{"from": id, "to": id, "type": kind}, ...]
      }

    Fits within max_chars (approximate) by truncating previews and capping
    the number of events per type proportionally.
    """
    from collections import defaultdict

    events_by_type: Dict[str, list] = defaultdict(list)
    for e in vision.events.values():
        events_by_type[e.event_type].append(e)

    # Sort each bucket chronologically
    for bucket in events_by_type.values():
        bucket.sort(key=lambda e: e.timestamp or "")

    event_counts = {k: len(v) for k, v in events_by_type.items()}

    # Budget chars per type proportionally
    total_events = max(sum(event_counts.values()), 1)
    chars_for_events = int(max_chars * 0.75)

    compact_events: Dict[str, list] = {}
    used = 0
    for etype, bucket in sorted(events_by_type.items()):
        type_budget = int(chars_for_events * len(bucket) / total_events)
        rows = []
        for e in bucket:
            row = {
                "ts": e.timestamp,
                "preview": (e.preview or "")[:120],
            }
            if e.connascence:
                row["connascence"] = {k: v for k, v in e.connascence.items()}
            row_str = json.dumps(row)
            if used + len(row_str) > type_budget + 200:
                break
            rows.append(row)
            used += len(row_str)
        compact_events[etype] = rows

    # Edges (flat list)
    edges: list = []
    chars_for_edges = max_chars - used
    edge_used = 0
    for event in vision.events.values():
        for conn_type, targets in event.connascence.items():
            for target_id in targets:
                edge = {"from": event.event_id, "to": target_id, "type": conn_type}
                s = json.dumps(edge)
                if edge_used + len(s) > chars_for_edges:
                    break
                edges.append(edge)
                edge_used += len(s)

    return {
        "event_counts": event_counts,
        "events_by_type": compact_events,
        "edges": edges,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


# Claude hierarchical chunks default large to limit segment count; each map call
# bills input tokens on the full segment. Opus × many × ~400k chars can exhaust
# prepaid credits in one run. Override: EOH_TIMELINE_CLAUDE_CHUNK_CHARS (e.g. 200000).
CLAUDE_CHUNK_TARGET_CHAR_LEN = int(os.getenv("EOH_TIMELINE_CLAUDE_CHUNK_CHARS", "400000"))
CLAUDE_CHUNK_TARGET_CHAR_LEN = max(80_000, min(CLAUDE_CHUNK_TARGET_CHAR_LEN, 900_000))


def _anthropic_credit_or_billing_block(exc: BaseException) -> bool:
    """Detect Anthropic 400s that mean credits/plan, not bad prompts."""
    s = str(exc).lower()
    if "credit balance" in s and "too low" in s:
        return True
    if "purchase credits" in s or "plans & billing" in s:
        return True
    return False


def _normalize_claude_scope(explicit: Optional[str]) -> str:
    """
    Where to spend Anthropic when use_claude=True (timeline summarizer).

    - reduce_only (default): no Anthropic in the timeline summarizer — hierarchical map+reduce
      and single-pass use OpenAI (e.g. GPT-4.1). Reserve Opus for real decision routes elsewhere.
    - all: Claude on hierarchical map+reduce and single-pass (legacy, very expensive).

    Env: EOH_TIMELINE_CLAUDE_SCOPE. Parameter ``explicit`` overrides env when set.
    """
    raw = (explicit if explicit is not None else os.getenv("EOH_TIMELINE_CLAUDE_SCOPE", "reduce_only"))
    v = (raw or "reduce_only").strip().lower()
    return v if v in ("all", "reduce_only") else "reduce_only"


async def summarize_timeline_for_eoh(
    client: AsyncOpenAI,
    question: str,
    timeline_text: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    pool: Any | None = None,
    patient_id: str | None = None,
    use_timeline_rag: bool | None = None,
    timeline_vision: Optional[PatientTimelineVision] = None,
    use_claude: bool = False,
    summarizer_model: str | None = None,
    claude_scope: Optional[str] = None,
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

    After producing summaries (when `patient_id` is set), loads or creates
    `PatientTimelineVision` and runs opportunistic graph enrichment from the
    composed summary fields. Pass `timeline_vision` to enrich an in-memory
    graph (e.g. PDF session import) instead of loading from disk.

    Claude spend control (when ``use_claude=True``):
    - ``claude_scope`` / ``EOH_TIMELINE_CLAUDE_SCOPE``: ``reduce_only`` (default) uses OpenAI
      for hierarchical and single-pass. ``all`` uses Claude for those steps too (expensive).
    """

    async def _finalize(summaries: TimelineSummaries, step_id: str) -> TimelineSummaries:
        await _enrich_patient_timeline_vision_from_summarizer(
            patient_id,
            question,
            summaries,
            step_id,
            timeline_vision=timeline_vision,
        )
        return summaries

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
        scope = _normalize_claude_scope(claude_scope)
        # Hierarchical: Anthropic only when scope=all (legacy). Otherwise map+reduce = OpenAI.
        claude_map = bool(use_claude and scope == "all")
        claude_single_pass = bool(use_claude and scope == "all")
        logger.info(
            "Timeline summarizer: received timeline of %d characters for question=%r",
            total_chars,
            question[:120],
        )
        if use_claude:
            logger.info(
                "Timeline summarizer: Claude scope=%r (hierarchical_claude=%s single_pass_claude=%s)",
                scope,
                claude_map,
                claude_single_pass,
            )

        # -------------------------------------------------------------------
        # 1) Simple-path summary for modest timelines (one pivotal LLM call)
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
            try:
                single = await _call_timeline_summarizer_model(
                    client,
                    question=question,
                    payload=payload,
                    max_tokens=max_tokens,
                    extra_system_hint=(
                        "You are seeing the patient's full timeline in one block. "
                        "Produce concise but information-dense JSON fields as specified."
                    ),
                    use_claude=claude_single_pass,
                    summarizer_model=summarizer_model,
                )
            except Exception as e:
                if claude_single_pass and _anthropic_credit_or_billing_block(e):
                    logger.error(
                        "Timeline summarizer: single-pass Claude blocked (credits/billing); "
                        "retrying with OpenAI (%s).",
                        EOH_TIMELINE_SUMMARIZER_MODEL,
                    )
                    single = await _call_timeline_summarizer_model(
                        client,
                        question=question,
                        payload=payload,
                        max_tokens=max_tokens,
                        extra_system_hint=(
                            "You are seeing the patient's full timeline in one block. "
                            "Produce concise but information-dense JSON fields as specified."
                        ),
                        use_claude=False,
                        summarizer_model=summarizer_model,
                    )
                else:
                    raise
            return await _finalize(single, "single_pass")

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
                    timeline_vision=timeline_vision,
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

                probe_te = probe_debug.get("timeline_enrichment")
                return await _finalize(
                    TimelineSummaries(
                        timeline_summary=canonical,
                        meds_and_labs_snapshot=meds_labs,
                        timeline_enrichment=probe_te if isinstance(probe_te, dict) else None,
                    ),
                    "probe_rag",
                )

            except Exception:
                logger.exception(
                    "Timeline summarizer: PROBE+RAG mode failed; using truncated raw timeline as canonical summary (no hierarchical map/reduce)."
                )
                canonical = (timeline_text or "")[:SUMMARY_MAX_CHARS].strip()
                return await _finalize(
                    TimelineSummaries(
                        timeline_summary=canonical,
                        meds_and_labs_snapshot="",
                    ),
                    "probe_rag_fallback",
                )

        # -------------------------------------------------------------------
        # 2) Hierarchical path: map-reduce over large timelines (fallback)
        # -------------------------------------------------------------------
        logger.info(
            "Timeline summarizer: using HIERARCHICAL mode (chars=%d > %d).",
            total_chars,
            SINGLE_PASS_CHAR_THRESHOLD,
        )
        effective_chunk_target = (
            CLAUDE_CHUNK_TARGET_CHAR_LEN if claude_map else CHUNK_TARGET_CHAR_LEN
        )
        chunks = _split_timeline_into_chunks(
            timeline_text,
            target_chars=effective_chunk_target,
            max_chunks_floor=MAX_CHUNKS,
        )
        n_chunks = len(chunks)
        hier_label = (
            " [map+reduce Claude]"
            if claude_map
            else f" [map+reduce {EOH_TIMELINE_SUMMARIZER_MODEL}]"
        )
        logger.info(
            "Timeline summarizer: split into %d chunk(s) (target=%d chars/floor, cap=%d)%s; "
            "sizes=%s",
            n_chunks,
            effective_chunk_target,
            HIERARCHICAL_MAX_CHUNKS_CAP,
            hier_label,
            str([len(c) for c in chunks[:8]]) + ("…" if n_chunks > 8 else ""),
        )
        if claude_map:
            logger.warning(
                "Timeline summarizer: Claude on every map + reduce — up to %d Opus-class map "
                "calls plus reduce; huge input tokens per map. If credits run out, steps fall "
                "back to OpenAI (%s). Default scope reduce_only keeps hierarchical on OpenAI.",
                n_chunks,
                EOH_TIMELINE_SUMMARIZER_MODEL,
            )
        else:
            logger.info(
                "Timeline summarizer: hierarchical map+reduce on %s (%d chunks); "
                "no Anthropic in this path unless EOH_TIMELINE_CLAUDE_SCOPE=all.",
                EOH_TIMELINE_SUMMARIZER_MODEL,
                n_chunks,
            )

        map_use_claude = claude_map
        reduce_use_claude = claude_map

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
                    use_claude=map_use_claude,
                    summarizer_model=summarizer_model,
                )
                chunk_summaries.append(seg_summary)
            except Exception as e:
                if map_use_claude and _anthropic_credit_or_billing_block(e):
                    logger.error(
                        "Timeline summarizer: Anthropic blocked chunk %d/%d (credits/billing). "
                        "Switching to OpenAI for this and remaining map/reduce steps.",
                        idx + 1,
                        n_chunks,
                    )
                    map_use_claude = False
                    reduce_use_claude = False
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
                            use_claude=False,
                            summarizer_model=summarizer_model,
                        )
                        chunk_summaries.append(seg_summary)
                    except Exception:
                        logger.exception(
                            "Timeline summarizer: map-step failed for chunk %d/%d after OpenAI fallback; continuing.",
                            idx + 1,
                            n_chunks,
                        )
                    continue
                logger.exception(
                    "Timeline summarizer: map-step failed for chunk %d/%d; continuing.",
                    idx + 1,
                    n_chunks,
                )
                continue

        if not chunk_summaries:
            logger.error(
                "Timeline summarizer: all map-step calls failed; falling back to raw timeline."
            )
            raise RuntimeError("no_chunk_summaries")

        # Reduce step: aggregate chunk-level summaries into a global view.
        reduce_payload: Dict[str, Any] = {
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

        # Inject enriched graph if available — gives the reducer structured,
        # cross-timeline knowledge (typed events + connascence edges) that the
        # raw text chunks cannot provide in aggregate.
        if timeline_vision is not None and timeline_vision.events:
            try:
                reduce_payload["enriched_graph"] = _compact_graph_for_reduce(
                    timeline_vision, max_chars=60_000
                )
                logger.info(
                    "Timeline summarizer reduce: injecting enriched graph "
                    "(%d events, %d edges) into reduce payload.",
                    len(timeline_vision.events),
                    timeline_vision.count_edges(),
                )
            except Exception:
                logger.warning("Timeline summarizer: graph compaction failed; skipping.", exc_info=True)

        graph_hint = ""
        if "enriched_graph" in reduce_payload:
            graph_hint = textwrap.dedent(
                """
                The payload also contains an `enriched_graph` field. This is a
                structured, typed view of the patient's clinical graph — events
                grouped by type (diagnosis, lab, med, procedure, note, visit) with
                connascence edges linking related events. Use it to:
                - Cross-check diagnoses and their linked lab/treatment events.
                - Identify temporal and causal chains not obvious from raw text.
                - Surface diagnostic arcs that span multiple timeline segments.
                Treat the graph as ground-truth provenance; prefer it over raw text
                when there is a conflict.
                """
            ).strip()

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

        if graph_hint:
            reduce_hint = f"{reduce_hint}\n\n{graph_hint}"

        try:
            final_summaries = await _call_timeline_summarizer_model(
                client,
                question=question,
                payload=reduce_payload,
                max_tokens=max_tokens,
                extra_system_hint=reduce_hint,
                use_claude=reduce_use_claude,
                summarizer_model=summarizer_model,
            )
        except Exception as e:
            if reduce_use_claude and _anthropic_credit_or_billing_block(e):
                logger.error(
                    "Timeline summarizer: reduce step blocked by Anthropic credits/billing; "
                    "retrying reduce with OpenAI (%s).",
                    EOH_TIMELINE_SUMMARIZER_MODEL,
                )
                final_summaries = await _call_timeline_summarizer_model(
                    client,
                    question=question,
                    payload=reduce_payload,
                    max_tokens=max_tokens,
                    extra_system_hint=reduce_hint,
                    use_claude=False,
                    summarizer_model=summarizer_model,
                )
            else:
                raise

        return await _finalize(final_summaries, "hierarchical_reduce")

    except Exception as e:
        logger.error("Timeline summarizer call failed; falling back to truncated timeline: %s", e)

        canonical = (timeline_text or "")[:SUMMARY_MAX_CHARS].strip()

        return await _finalize(
            TimelineSummaries(
                timeline_summary=canonical,
                meds_and_labs_snapshot="",
            ),
            "truncated_fallback",
        )