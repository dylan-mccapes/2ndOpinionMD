# server/api/stream_config.py

import os
import re
from typing import Any, Dict, List, Set

# ---------------------------------------------------------------------------
# Core knobs
# ---------------------------------------------------------------------------

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4.1-mini"  # adjust as needed

# How many total internal context chunks to give the LLM
BASE_RRF_K = 24

# Hard cap on context size passed to LLM (chars; rough guard vs token overflows)
MAX_CONTEXT_CHARS = 64_000

# Valyu-related env (used by valyu_client, kept here for centralization)
VALYU_BASE_URL = os.getenv("VALYU_BASE_URL", "").strip()
VALYU_API_KEY = os.getenv("VALYU_API_KEY", "").strip()
VALYU_TIMEOUT = float(os.getenv("VALYU_TIMEOUT", "20.0"))

# Ethos model source name (rag_corpus.source)
ETHOS_SOURCE_NAME = "ethos_model"

# Heuristic source-gating config
SOURCE_GATING_ENABLED = bool(int(os.getenv("RAG_SOURCE_GATING_ENABLED", "1")))
MIN_DOCS_PER_SOURCE = int(os.getenv("RAG_MIN_DOCS_PER_SOURCE", "1"))
REL_SCORE_CUTOFF = float(os.getenv("RAG_REL_SCORE_CUTOFF", "0.35"))
ABS_SCORE_CUTOFF = float(os.getenv("RAG_ABS_SCORE_CUTOFF", "0.0"))
ALWAYS_KEEP_SOURCES: Set[str] = {
    s.strip()
    for s in os.getenv("RAG_ALWAYS_KEEP_SOURCES", "").split(",")
    if s.strip()
}

# How many TS-based rows to "pin" per source during light fusion
# (these get guaranteed priority in the final fused context).
TS_PIN_K_PER_SOURCE_CODING = int(os.getenv("RAG_TS_PIN_K_PER_SOURCE_CODING", "10"))
TS_PIN_K_PER_SOURCE_DEFAULT = int(os.getenv("RAG_TS_PIN_K_PER_SOURCE_DEFAULT", "3"))

# Max fraction of ctx_k that pinned rows are allowed to occupy globally.
# Example: 0.5 → at most 50% of final context slots are reserved for pinned rows.
TS_PIN_MAX_FRAC_CTX = float(os.getenv("RAG_TS_PIN_MAX_FRAC_CTX", "0.5"))


# ---------------------------------------------------------------------------
# rag_corpus source registry
# ---------------------------------------------------------------------------

SOURCE_CONFIG: Dict[str, Dict[str, Any]] = {
    "acr_eular": {
        "kind": "guideline",
        "n_rows": 1,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": False,
    },
    "acr_ild_2023": {
        "kind": "guideline",
        "n_rows": 13,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": False,
    },
    "acr_ra_2021": {
        "kind": "guideline",
        "n_rows": 16,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": False,
    },
    "cdc_opioid": {
        "kind": "guideline",
        "n_rows": 409,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": False,
    },
    "chv": {
        "kind": "terminology",
        "n_rows": 152206,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": False,
    },
    "disgenet": {
        "kind": "molecular",
        "n_rows": 1,
        "allow_in_ask": True,
        "allow_in_coding": False,
        "codes_authoritative": False,
    },
    "esc_ers_ph_2022": {
        "kind": "guideline",
        "n_rows": 114,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": False,
    },
    "ethos_model": {
        "kind": "model",
        "n_rows": 4,
        "allow_in_ask": True,
        "allow_in_coding": False,
        "codes_authoritative": False,
    },
    "eular_acr_sle_2019": {
        "kind": "guideline",
        "n_rows": 30,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": False,
    },
    "eular_ra_2022": {
        "kind": "guideline",
        "n_rows": 10,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": False,
    },
    "gwas": {
        "kind": "molecular",
        "n_rows": 1,
        "allow_in_ask": True,
        "allow_in_coding": False,
        "codes_authoritative": False,
    },
    "hpo": {
        "kind": "terminology",
        "n_rows": 39441,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": True,
    },
    "icd10cm": {
        "kind": "terminology",
        "n_rows": 29178,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": True,
        "exclude_meta_from": ["snomed_map"],
    },
    "icd11": {
        "kind": "terminology",
        "n_rows": 34663,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": True,
    },
    "kdigo_gn_ln_2021": {
        "kind": "guideline",
        "n_rows": 281,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": False,
    },
    "loinc": {
        "kind": "terminology",
        "n_rows": 104672,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": True,
    },
    "medical_knowledge": {
        "kind": "misc",
        "n_rows": 1,
        "allow_in_ask": True,
        "allow_in_coding": False,
        "codes_authoritative": False,
    },
    "mimic3_dx": {
        "kind": "ehr_dx",
        "n_rows": 651000,
        "allow_in_ask": True,
        "allow_in_coding": False,
        "codes_authoritative": False,
    },
    "mimic3_labitems": {
        "kind": "ehr_labitems",
        "n_rows": 753,
        "allow_in_ask": True,
        "allow_in_coding": False,
        "codes_authoritative": False,
    },
    "mimic3_proc": {
        "kind": "ehr_proc",
        "n_rows": 240095,
        "allow_in_ask": True,
        "allow_in_coding": False,
        "codes_authoritative": False,
    },
    "mimic4_dx": {
        "kind": "ehr_dx",
        "n_rows": 4866101,
        "allow_in_ask": True,
        "allow_in_coding": False,
        "codes_authoritative": False,
    },
    "mimic4_labitems": {
        "kind": "ehr_labitems",
        "n_rows": 1622,
        "allow_in_ask": True,
        "allow_in_coding": False,
        "codes_authoritative": False,
    },
    "mimic4_note": {
        "kind": "ehr_note",
        "n_rows": 2646758,
        "allow_in_ask": True,
        "allow_in_coding": False,
        "codes_authoritative": False,
    },
    "n2c2_t3_ap": {
        "kind": "note_dataset",
        "n_rows": 538,
        "allow_in_ask": True,
        "allow_in_coding": False,
        "codes_authoritative": False,
    },
    "neurolex": {
        "kind": "terminology",
        "n_rows": 1,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": False,
    },
    "nice": {
        "kind": "guideline",
        "n_rows": 97,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": False,
    },
    "nice_ta397_belimumab": {
        "kind": "guideline",
        "n_rows": 17,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": False,
    },
    "orphanet": {
        "kind": "terminology",
        "n_rows": 11240,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": False,
    },
    "panelapp": {
        "kind": "gene_panel",
        "n_rows": 1,
        "allow_in_ask": True,
        "allow_in_coding": False,
        "codes_authoritative": False,
    },
    "pubmd": {
        "kind": "pubmed",
        "n_rows": 2,
        "allow_in_ask": True,
        "allow_in_coding": False,
        "codes_authoritative": False,
    },
    "rxnorm": {
        "kind": "terminology",
        "n_rows": 405026,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": True,
    },
    "snomed": {
        "kind": "terminology",
        "n_rows": 199420,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": True,
    },
    "va_guidelines": {
        "kind": "guideline",
        "n_rows": 6546,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": False,
    },
    "who_committee": {
        "kind": "guideline",
        "n_rows": 1,
        "allow_in_ask": True,
        "allow_in_coding": True,
        "codes_authoritative": False,
    },
}


def _is_code_source(src: str) -> bool:
    cfg = SOURCE_CONFIG.get((src or "").lower())
    return bool(cfg and cfg.get("codes_authoritative"))


def _allow_in_coding(src: str) -> bool:
    cfg = SOURCE_CONFIG.get((src or "").lower())
    return bool(cfg and cfg.get("allow_in_coding"))


ALL_SOURCES: Set[str] = set(SOURCE_CONFIG.keys())

CODING_DEFAULT_SOURCES: List[str] = [
    s for s in SOURCE_CONFIG.keys() if _allow_in_coding(s)
]

CODE_SOURCES: Set[str] = {s for s in SOURCE_CONFIG.keys() if _is_code_source(s)}

RA_GUIDELINE_SOURCES: Set[str] = {
    "acr_ra_2021",
    "eular_ra_2022",
}

GUIDELINE_SOURCES: Set[str] = {
    # Core disease-specific guidelines
    "acr_ra_2021",
    "eular_ra_2022",
    "acr_ild_2023",
    "esc_ers_ph_2022",
    "kdigo_gn_ln_2021",
    "nice",
    "nice_ta397_belimumab",
    "va_guidelines",
    "who_committee",
}

CODING_DEFAULT_SOURCES = [
    "acr_ra_2021",
    "eular_ra_2022",
    "acr_ild_2023",
    "icd11",
    "icd10cm",
    "loinc",
    "rxnorm",
    "snomed",
    "va_guidelines",
    "who",
    "panelapp",
    "disgenet",
    "chv",
    "hpo",
    "valyu",
]

# Sources that should be used for structured coding/abstraction
CODING_SOURCES = [
    "icd10cm",
    "icd11",
    "snomed",
    "loinc",
    "rxnorm",
    "hpo",
    "chv",
]

# How many items to keep per source for coding (no global fusion)
CODING_TS_K = 16       # top N TS hits per source
CODING_ANN_K = 16      # top N ANN hits per source
CODING_MAX_PER_SOURCE = 24  # hard cap (TS+ANN combined)

CODING_SYSTEM_PROMPT = """
TASK: Clinical coding abstraction.

PATIENT SCENARIO:
- Adult with biopsy-proven class IV lupus nephritis.
- Nephrotic-range proteinuria.
- Current treatment: mycophenolate mofetil + oral prednisone.

OBJECTIVES (PLEASE RETURN CODES FOR ALL):

1) DIAGNOSES
   - Systemic lupus erythematosus (SLE).
   - Lupus nephritis (renal involvement of SLE).

2) PROCEDURES
   - Kidney biopsy (renal biopsy).

3) LABS / MONITORING
   - Urine protein/creatinine ratio.
   - Serum creatinine.
   - Complement levels (C3, C4, CH50 acceptable).
   - Anti–double stranded DNA (anti-dsDNA) antibodies.

4) MEDICATIONS
   - Mycophenolate mofetil (systemic, oral formulation acceptable).
   - Oral prednisone.

VOCABULARIES (REQUIRED):
- ICD-10-CM and ICD-11 for diagnoses.
- SNOMED CT for diagnoses and procedures.
- LOINC for laboratory tests.
- RxNorm for medications.

OUTPUT FORMAT:
For each requested concept, list all of:
- ICD-10-CM code(s) + preferred term.
- ICD-11 code(s) + preferred term.
- SNOMED CT code(s) + preferred term.
- LOINC code(s) + name.
- RxNorm code(s) + name.

- Only use codes that appear in the provided context.
- If a requested concept has no code in context, write:
  “NOT FOUND IN CONTEXT — DO NOT HALLUCINATE.”
- Do NOT invent or guess codes.

Very important:

- You are given explicit context snippets which include codes and their vocabularies.
- If you saw ANY codes from a vocabulary in the context, you MUST list those codes under that vocabulary in the FINAL CODING OUTPUT.
- Only output "none_found" for a vocabulary if there were truly ZERO codes from that vocabulary ANYWHERE in the context.
- Never "forget" codes you already listed earlier in the answer.
""".strip()

def is_ra_query(q: str, valyu_labels: Dict[str, float] | None = None) -> bool:
    """
    Conservative RA intent detection, with protection for HF queries.

    - Requires explicit RA-ish tokens or Valyu RA confidence.
    - Suppresses RA mode if the query clearly looks like heart failure.
    """
    q_lower = (q or "").lower()

    has_explicit_ra = (
        "rheumatoid arthritis" in q_lower
        or re.search(r"\bra\b", q_lower)
        or "dmard" in q_lower
        or "methotrexate" in q_lower
        or "etanercept" in q_lower
    )

    # protect against HF questions being misclassified as RA
    hf_terms = ["heart failure", "hfref", "hfpef", "hfmref"]
    has_hf = any(term in q_lower for term in hf_terms)

    valyu_ra_conf = float((valyu_labels or {}).get("rheumatoid_arthritis", 0.0))

    return (has_explicit_ra or valyu_ra_conf >= 0.6) and not has_hf

