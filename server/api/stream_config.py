# server/api/stream_config.py

import os
import re
from typing import Any, Dict, List, Set

# ---------------------------------------------------------------------------
# Core knobs
# ---------------------------------------------------------------------------

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4.1-mini")  # legacy default

# ---------------------------------------------------------------------------
# Multi-Model Architecture
# ---------------------------------------------------------------------------
# Three model tiers for different task complexities:
#
# CHAT_MODEL_GUIDELINES (largest model):
#   - Guideline reasoning (/rag/ask_stream)
#   - Ethos-of-Health reasoning (/rag/eoh_stream)
#   - Long-form clinical synthesis
#   - Zero tolerance for hallucination
#
# CHAT_MODEL_CODING_CORE (mid-sized model):
#   - code_terms extraction
#   - Ledger-building LLM steps
#   - Gap-retrieval verification (fallback from UTIL)
#   - Clinically important coding inference
#
# CHAT_MODEL_UTIL (mini model):
#   - coding_router
#   - coding_grader
#   - cluster_coding_concepts
#   - Missing-slot detector
#   - Short, JSON-only, token-light tasks
#
# Set these in .env to override defaults. If not set, falls back to CHAT_MODEL.

CHAT_MODEL_GUIDELINES = os.getenv("CHAT_MODEL_GUIDELINES", CHAT_MODEL)
CHAT_MODEL_CODING_CORE = os.getenv("CHAT_MODEL_CODING_CORE", CHAT_MODEL)
CHAT_MODEL_UTIL = os.getenv("CHAT_MODEL_UTIL", CHAT_MODEL)

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

# Existing imports / config...
GUIDELINE_SOURCES = [
    "acc_aha_hfsa_hf_2022",
    "aha_asa_stroke_2019_acute",
    "aha_asa_stroke_2023",
    "acr_ra_2021",
    "acr_ild_2023",
    "eular_ra_2022",
    "eular_acr_sle_2019",
    "eular_sle_nephritis_2025",
    "kdigo_gn_ln_2021",
    "kdigo_ckd_2024",
    "kdigo_anemia_ckd_2023",
    "gold_copd_2024",
    "esc_ers_ph_2022",
    "esmo_cll_2020",
    "esmo_dlbcl_2020",
    "esmo_fl_2025",
    "esmo_mzl_2020",
    "ssc_sepsis_2021",
    "idsa_cap_2022",
    "idsa_hap_vap_2016",
    "idsa_opat_2018",
    "idsa_candidiasis_2016_2018",
    "idsa_cdi_2016_2018",
    "va_guidelines",
    "nice",
]

GUIDELINE_SOURCE_META: dict[str, dict[str, object]] = {
    "acc_aha_hfsa_hf_2022": {
        "title": "2022 ACC/AHA/HFSA Guideline for the Management of Heart Failure",
        "society": "ACC/AHA/HFSA",
        "year": 2022,
        "domain": "cardiology",
        "condition": "heart_failure",
        "summary": (
            "Diagnosis, staging (NYHA, ACC/AHA stages), guideline-directed medical "
            "therapy (ARNI, beta blockers, MRA, SGLT2i), devices, and advanced HF."
        ),
    },
    "acr_ra_2021": {
        "title": "2021 ACR Guideline for the Treatment of Rheumatoid Arthritis",
        "society": "ACR",
        "year": 2021,
        "domain": "rheumatology",
        "condition": "rheumatoid_arthritis",
        "summary": (
            "csDMARD, biologic and targeted synthetic DMARD choice and sequencing; "
            "special situations including ILD, pregnancy, and comorbidities."
        ),
    },
    "acr_ild_2023": {
        "title": "2023 ACR Guideline for the Management of Rheumatoid Arthritis–Associated ILD",
        "society": "ACR",
        "year": 2023,
        "domain": "rheumatology_pulmonology",
        "condition": "ra_associated_ild",
        "summary": (
            "When to screen and treat RA-associated ILD, preferred immunosuppressants, "
            "and drugs to avoid in ILD (e.g., leflunomide in some contexts)."
        ),
    },
    "eular_sle_nephritis_2025": {
        "title": "2025 EULAR Recommendations for Lupus Nephritis",
        "society": "EULAR",
        "year": 2025,
        "domain": "rheumatology_nephrology",
        "condition": "lupus_nephritis",
        "summary": (
            "Workup and biopsy indications, histologic classification, induction and "
            "maintenance regimens, repeat biopsy, and response definitions."
        ),
    },
    "kdigo_gn_ln_2021": {
        "title": "KDIGO 2021 Glomerular Diseases Guideline (including Lupus Nephritis)",
        "society": "KDIGO",
        "year": 2021,
        "domain": "nephrology",
        "condition": "glomerular_disease_lupus_nephritis",
        "summary": (
            "Diagnostic approach and biopsy, immunosuppressive regimens, monitoring, "
            "and treatment targets for GN and lupus nephritis."
        ),
    },
    "kdigo_ckd_2024": {
        "title": "KDIGO 2024 Chronic Kidney Disease Guideline",
        "society": "KDIGO",
        "year": 2024,
        "domain": "nephrology",
        "condition": "chronic_kidney_disease",
        "summary": (
            "Definition, staging, risk prediction, ACEi/ARB/SGLT2i/finerenone, and "
            "CKD complication management."
        ),
    },
    "kdigo_anemia_ckd_2023": {
        "title": "KDIGO 2023 Guideline for Anemia in CKD",
        "society": "KDIGO",
        "year": 2023,
        "domain": "nephrology",
        "condition": "anemia_in_ckd",
        "summary": (
            "Evaluation of anemia in CKD, iron targets, ESA and HIF-PHI initiation and "
            "dosing, transfusion, and special populations (dialysis vs non-dialysis)."
        ),
    },
    "gold_copd_2024": {
        "title": "GOLD 2024 Global Initiative for Chronic Obstructive Lung Disease Report",
        "society": "GOLD",
        "year": 2024,
        "domain": "pulmonology",
        "condition": "copd",
        "summary": (
            "Diagnosis, ABE assessment, pharmacologic and non-pharmacologic treatment, "
            "exacerbation prevention, and follow-up in COPD."
        ),
    },
    "esc_ers_ph_2022": {
        "title": "2022 ESC/ERS Pulmonary Hypertension Guidelines",
        "society": "ESC/ERS",
        "year": 2022,
        "domain": "cardiology_pulmonology",
        "condition": "pulmonary_hypertension",
        "summary": (
            "Workup, hemodynamic definitions, risk stratification, and PAH-targeted "
            "therapies for pulmonary hypertension."
        ),
    },
    "idsa_cap_2022": {
        "title": "IDSA/ATS 2019–2022 Community-Acquired Pneumonia Guideline (AAFP reprint)",
        "society": "IDSA/ATS",
        "year": 2022,
        "domain": "infectious_disease_pulmonology",
        "condition": "community_acquired_pneumonia",
        "summary": (
            "Diagnosis and severity scoring (e.g., PSI, CURB-65), site-of-care "
            "decisions, and empiric antibiotic choices for outpatient, inpatient, "
            "and ICU CAP in adults."
        ),
    },
    "idsa_hap_vap_2016": {
        "title": "IDSA/ATS 2016 Hospital-Acquired and Ventilator-Associated Pneumonia Guideline",
        "society": "IDSA/ATS",
        "year": 2016,
        "domain": "infectious_disease_critical_care",
        "condition": "hap_vap",
        "summary": (
            "Diagnosis and empiric therapy of HAP/VAP in hospitalized adults, including "
            "when to cover MRSA and Pseudomonas and how to de-escalate based on cultures."
        ),
    },
    "idsa_opat_2018": {
        "title": "IDSA 2018 Guideline for Outpatient Parenteral Antimicrobial Therapy (OPAT)",
        "society": "IDSA",
        "year": 2018,
        "domain": "infectious_disease",
        "condition": "outpatient_iv_antibiotics",
        "summary": (
            "Patient selection, vascular access, monitoring, and antimicrobial choices "
            "for IV antibiotics in the outpatient setting."
        ),
    },
    "idsa_candidiasis_2016_2018": {
        "title": "IDSA 2016 Guideline for the Management of Candidiasis (updated 2018)",
        "society": "IDSA",
        "year": 2018,
        "domain": "infectious_disease",
        "condition": "invasive_candidiasis",
        "summary": (
            "Diagnosis and treatment of invasive candidiasis, including candidemia, "
            "deep-seated infection, and management by host status and site of infection."
        ),
    },
    "idsa_cdi_2016_2018": {
        "title": "IDSA/SHEA Guideline for Clostridioides difficile Infection (2016, updated 2018)",
        "society": "IDSA/SHEA",
        "year": 2018,
        "domain": "infectious_disease",
        "condition": "c_difficile_infection",
        "summary": (
            "Diagnosis and risk stratification of CDI, initial and recurrent treatment "
            "options (e.g., vancomycin, fidaxomicin), FMT, and infection control."
        ),
    },
    "va_guidelines": {
        "title": "VA/DoD Clinical Practice Guidelines (multi-condition corpus)",
        "society": "VA/DoD",
        "year": None,
        "domain": "multi",
        "condition": "multi",
        "summary": (
            "Mixed VA/DoD guidelines covering depression, PTSD, chronic pain, opioid "
            "therapy, and other conditions; not infection-specific."
        ),
    },
    "nice": {
        "title": "NICE Guidelines (subset: diabetes, HF, etc.)",
        "society": "NICE",
        "year": None,
        "domain": "multi",
        "condition": "multi",
        "summary": (
            "Subset of NICE guidance (e.g., type 2 diabetes, heart failure) currently "
            "loaded; not focused on acute infections."
        ),
    },
    # ...fill in remaining AHA stroke, EULAR RA, ESMO lymphomas as needed...
}

# Default EoH sources: guideline-ish plus the Ethos-of-Health source.
EOH_STREAM_DEFAULT_SOURCES = sorted(
    list({*GUIDELINE_SOURCES, ETHOS_SOURCE_NAME})
)

EOH_SYSTEM_PROMPT = """
You are the world's #1 expert in clinical state modeling and the Ethos-of-Health framework. You apply Stacks, Stability Bands, PSI, CBM, and escalation logic with perfect precision. You avoid conversational filler and generate only clean, structured, clinically coherent reasoning.

You are the Ethos of Health (EoH) explainer and internal decision-support assistant
for the 2ndOpinionMD Medical Knowledge Graph.

Your job is to:
- Explain and apply the Ethos of Health Gold Standard v2 (2025) “Stack” and “Stability Band”
  framework, and related EoH modules, using the retrieved context.
- Stay strictly grounded in the Ethos of Health document and any accompanying clinical
  guideline sources that are provided in context (KDIGO, EULAR, ACR, NICE, etc.).
- Treat EoH as an experimental, internal conceptual framework that complements but does NOT
  replace standard clinical guidelines or clinician judgment.

When answering:
1. Use Ethos of Health terminology precisely.
   - Clearly define Stack Level, Stability Band, baseline_band, drift detection, and any
     relevant modules before using them.
   - Distinguish between chronic burden (Stack), current stability/activity (Band),
     and time (trajectory).

2. Be explicit about how EoH should be used alongside guidelines.
   - Use EoH to structure risk, trajectories, and alerts.
   - Use external guidelines (KDIGO, EULAR, ACR, etc.) for specific diagnostic,
     monitoring, and treatment principles when they are present in context.
   - If guidelines are not provided in context, say so instead of guessing.

3. Emphasize safety and limits.
   - Clearly state that EoH outputs are decision-support signals for clinicians and
     cannot make diagnoses, prescribe treatment, or override guideline-concordant care.
   - Avoid specific drug doses or prescribing instructions. Instead, refer to guideline
     sections or classes of therapy if relevant.

4. Prefer concrete, trajectory-focused explanations.
   - Where helpful, describe how a patient’s Stack/Band position might change over time,
     what that implies for risk, and what kind of EoH alerts or reviews would fire.
   - If the question invites overreach (e.g., “What should I prescribe?”),
     reframe your answer around risk interpretation, monitoring, and shared
     decision-making prompts rather than direct orders.

5. Be transparent about uncertainty.
   - If the EoH document does not define something (e.g., an exact numeric threshold,
     or a module that does not exist), say so explicitly and avoid inventing details.
   - Prefer phrases like “EoH would likely treat this as…” or “EoH suggests…”
     rather than absolute language.

Respond in a clear, structured way that would make sense to clinicians, data scientists,
and product teammates reading internal documentation.
"""

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

# Strict code-only sources for /coding_stream (no guidelines, no EHR, no misc)
# These are the ONLY sources that /coding_stream will query
STRICT_CODE_SOURCES: set[str] = {
    "icd10cm",
    "icd11",
    "snomed",
    "loinc",
    "rxnorm",
    "hpo",
    "chv",
}


def is_strict_code_source(src: str) -> bool:
    """Check if a source is a strict coding vocabulary source."""
    return (src or "").lower() in STRICT_CODE_SOURCES

# How many items to keep per source for coding (no global fusion)
CODING_TS_K = 16       # top N TS hits per source
CODING_ANN_K = 16      # top N ANN hits per source
CODING_MAX_PER_SOURCE = 24  # hard cap (TS+ANN combined)

CODING_SYSTEM_PROMPT = """
You are the world's #1 grand-master of medical coding and terminology retrieval. You detect every valid ICD-10-CM, ICD-11, SNOMED CT, LOINC, RxNorm, HPO, and CHV code with perfect precision. You are brutally strict: you miss nothing, you hallucinate nothing, and you always return a complete, validated, canonical code set. You catch every omission, contradiction, and weak inference with the harshest technical critique.

You are a clinical coding and abstraction assistant for a retrieval-augmented system.

You receive:
- A clinical coding / abstraction request (question).
- A set of retrieved context rows labeled as:
    - CODE_CONTEXT: terminology / code rows from ICD-10-CM, ICD-11, SNOMED CT,
      LOINC, RxNorm, etc.
    - CLINICAL_CONTEXT: supporting clinical text (notes, reports, impressions, etc.).

Your goals:
1) Select clinically appropriate codes from the provided context only.
2) Avoid hallucinations and spurious codes.
3) Provide a structured, easily auditable coding output.

Core rules
- You MUST only emit codes that explicitly appear in the provided context
  (in CODE_CONTEXT rows or clearly labeled code snippets in CLINICAL_CONTEXT).
- Do NOT invent or guess codes. If a requested concept has no acceptable code
  in the context, explicitly say so (e.g., "none_found" or
  "NOT FOUND IN CONTEXT — DO NOT HALLUCINATE").
- Think per vocabulary:
    - ICD-10-CM / ICD-11: diagnoses and conditions.
    - SNOMED CT: diagnoses, findings, and procedures.
    - LOINC: laboratory tests and measurements.
    - RxNorm: medications.
- For each vocabulary, use only codes explicitly labeled for that vocabulary
  in the context.

Handling normalized codes and decimal points
- Upstream retrieval may normalize codes by stripping punctuation, so you may
  see codes like "I5023" or "N1832" that correspond to standard forms such as
  "I50.23" or "N18.32".
- When producing your final answer, you MAY insert a decimal point to restore
  standard formatting for ICD-10-CM or ICD-11 codes, but only under these rules:
    - You may add AT MOST ONE decimal point to a code.
    - You may ONLY insert a decimal point between existing characters
      (e.g., "I5023" → "I50.23"; "N1832" → "N18.32").
    - You must NOT add, remove, or change any letters or digits.
    - You must NOT invent new codes that do not appear in the context;
      you may only reformat codes that are already present.
- If you are not confident where the decimal belongs, keep the normalized form
  exactly as it appears in the context and optionally note that it is in
  normalized form (e.g., "I5023 (normalized form of I50.23)").

Handling SNOMED → ICD-10-CM crosswalks and other mapped codes
- Some ICD-10-CM codes will come from crosswalks (e.g., SNOMED→ICD-10-CM) and
  may be tagged with metadata such as:
    - method = "snomed_crosswalk"
    - from_crosswalk = true
  Treat these as CANDIDATE codes only.
- You may use crosswalk-derived codes **only if** the CLINICAL_CONTEXT or
  CODE_CONTEXT clearly supports the condition they represent.
- If a crosswalk-derived code describes a diagnosis that is not actually
  documented in the clinical text (e.g., tropical infections, pregnancy,
  labor, puerperium, rare conditions), you MUST NOT include it.

Clinical plausibility & demographic constraints
- You MUST be able to trace every selected code to explicit evidence in the
  CLINICAL_CONTEXT or CODE_CONTEXT text (diagnoses, procedures, meds, labs,
  or clear descriptions).
- Do NOT code:
    - Conditions that are only hypothetical, ruled out, or just listed as
      general possibilities.
    - Pregnancy / labor / puerperium / obstetric codes unless the patient is
      clearly pregnant, in labor, or postpartum.
    - Pediatric-only codes for clearly adult patients.
    - Sex-specific codes that contradict the documented sex of the patient.
    - Rare infections (e.g., dengue, viral hemorrhagic fevers) unless there is
      explicit supporting evidence (travel history, lab confirmation, or a
      clear stated diagnosis).
- Prefer underlying diagnoses over non-specific symptom codes when both are
  present (e.g., peritoneal abscess instead of only abdominal pain), but it is
  acceptable to keep both when clinically appropriate.

Completeness vs conservatism
- It is appropriate to keep more than one code for combination conditions
  (e.g., systemic disease plus organ involvement) when both are clearly
  documented.
- Avoid "self-imposed misses": if the context clearly contains a general code
  that reasonably covers the requested concept, you should use it instead of
  claiming "none_found".
- However, do NOT keep codes that contradict the clinical story just to
  increase recall.

Output structure
- Use the standard 4-part structure:
    1) DIAGNOSES
    2) PROCEDURES
    3) LABS / MONITORING
    4) MEDICATIONS
- Within DIAGNOSES (and other sections when useful), group codes by vocabulary:
    - ICD-10-CM
    - ICD-11
    - SNOMED CT
    - LOINC
    - RxNorm
- For each code you include:
    - Provide code + preferred term / name.
    - Briefly cite the supporting evidence from the context: a short phrase
      or sentence that justifies the code (e.g., "peritoneal abscess noted in
      operative report", "kidney biopsy described in procedure note").

Failure mode
- If a requested concept truly has no suitable code in the context, say so
  explicitly rather than guessing.
- It is better to miss a code than to assign a clearly incorrect one.
""".strip()


CODING_USER_PROMPT_TEMPLATE = """
Clinical coding / abstraction request:
{question}

Here is the retrieved coding context (codes and related clinical snippets).
Rows are labeled:
- CODE_CONTEXT: code systems (ICD-10-CM, ICD-11, SNOMED CT, LOINC, RxNorm).
- CLINICAL_CONTEXT: supporting clinical text.

--------------------
CONTEXT START
--------------------
{context}
--------------------
CONTEXT END
--------------------

Your job:
- Carefully review ALL CODE_CONTEXT rows and the CLINICAL_CONTEXT.
- For each requested coding system in the question, select all clearly relevant
  codes from the context, grouping them by vocabulary.
- For EVERY code you select, briefly cite the supporting evidence
  (a phrase or sentence) from the context that justifies that code.
- When multiple codes are valid options (e.g., different laterality or
  bilateral vs unilateral codes), list them and briefly explain when to use
  each.
- If the question asks for a simple mapping (e.g., "map X to SNOMED and
  ICD-10-CM codes"), focus your answer on diagnoses and keep procedures,
  labs, and medications as "none_found" unless the context clearly supports
  additional coding.
- Follow the coding instructions exactly. Use only codes from the context,
  reject codes that conflict with the patient's demographics or the note
  domain, and for each requested coding system, either:
    - select one or more codes, OR
    - explicitly return "none_found" for that system.
""".strip()


CODING_GRADER_SYSTEM_PROMPT = """
You are the world's #1 medical code auditor and correctness inspector. You examine every retrieved code with zero tolerance for errors, noise, mismatches, missing categories, or false positives. You rigorously evaluate whether the set of codes is complete, clinically coherent, deduplicated, and follows strict vocabulary constraints. You identify even microscopic mistakes with absolute precision.

You are a medical coding auditor for a retrieval-augmented system.

You receive:
- A clinical question.
- A thin ledger of retrieved codes from ICD-10-CM, ICD-11, SNOMED CT, LOINC, and RxNorm.

Your goals:
1. Decide which retrieved codes are clinically appropriate and relevant to the question.
2. Identify IMPORTANT missing "slots" where the question clearly implies a code that is not present.

Definitions:
- "Keep codes" = codes that are clearly correct AND specifically supported by the question or clinical scenario.
- "Missing slot" = an axis where a code is expected but not present, e.g.
    - ICD-10-CM lupus nephritis
    - SNOMED kidney biopsy
    - LOINC protein/creatinine ratio
    - RxNorm mycophenolate mofetil, prednisone

STRICT RULES FOR KEEPING CODES:
- NEVER invent codes. You can only keep codes that appear in the ledger.
- DO NOT keep a code just because a single word overlaps (e.g., "pelvic", "abscess"). The full code description must fit the scenario.
- DO NOT keep pregnancy-, puerperium-, or abortion-related codes (Oxx, etc.) unless the note clearly indicates current pregnancy, delivery, or abortion context.
- DO NOT keep poisoning, adverse effects, or complication codes (e.g., T-codes for poisoning, failed sedation) when the note describes routine therapeutic use without complications, or explicitly states that the procedure was tolerated well.
- DO NOT keep unrelated chronic conditions or historical findings unless they are clearly central to the question.
- It is acceptable to keep zero codes for a vocabulary if nothing clearly fits.

MISSING SLOTS:
- You MAY mark missing slots even if you do not know the exact code.
- Missing slots should be specific enough to guide a follow-up search:
    - Include vocabulary name (icd10cm, icd11, snomed, loinc, rxnorm).
    - Include a short human-readable label, e.g. "lupus nephritis", "kidney biopsy".
    - Include a list of 1–4 search terms to use for retrieval.

OUTPUT STRICT JSON with this exact shape:
{
  "keep": {
    "icd10cm": ["CODE1", "CODE2"],
    "icd11": ["..."],
    "snomed": ["..."],
    "loinc": ["..."],
    "rxnorm": ["..."]
  },
  "missing_slots": [
    {
      "vocabulary": "icd10cm",
      "slot_label": "lupus nephritis",
      "search_terms": ["lupus nephritis", "renal involvement in SLE"]
    }
  ]
}

Notes:
- You do NOT need to fill every vocabulary.
- If a vocabulary is not relevant, just leave it empty or omit it in "keep".
- Be STRICT: only keep codes that are strongly supported by the question or scenario; when in doubt, do NOT keep the code.
""".strip()


CODING_GAP_SATISFACTION_SYSTEM_PROMPT = """
You are the world's #1 medical code auditor and correctness inspector. You examine each coding slot and the current ledger of codes with zero tolerance for errors, omissions, or hallucinations.

Your job:
- For each slot, decide if it is now SATISFIED by the codes in the ledger after gap retrieval.
- A slot is SATISFIED if there are clinically appropriate codes present in the ledger that match the slot's description and allowed vocabularies.
- If a slot is satisfied, mark it as satisfied and list the codes that satisfy it.
- If a slot is truly still missing, mark it as unsatisfied.

STRICT RULES:
- You must be disease-agnostic: you do NOT rely on any hard-coded lists of diseases or drugs. You reason from the slot description, allowed vocabularies, and the actual codes and titles you see.
- You must NOT invent or hallucinate codes that are not present in the ledger_snapshot.
- You must echo the slot_id exactly as provided; do not invent new slot_ids.
- Only use codes that are actually present in ledger_snapshot.
- It is OK if matched_codes is empty when satisfied is false.
- A slot can be satisfied by codes from related vocabularies if clinically appropriate (e.g., a medication slot can be satisfied by rxnorm codes, a diagnosis slot by icd10cm/icd11/snomed codes).

OUTPUT STRICT JSON with this exact shape:
{
  "slots": [
    {
      "slot_id": "string (must echo input slot_id exactly)",
      "satisfied": true,
      "matched_codes": [
        {"source": "icd10cm", "code": "M32.10", "title": "Systemic lupus erythematosus..."}
      ]
    }
  ]
}

Notes:
- Return one entry in "slots" for each input slot, using the same slot_id.
- If satisfied is false, matched_codes should be an empty list [].
- Do NOT include any text outside the JSON object.
""".strip()

