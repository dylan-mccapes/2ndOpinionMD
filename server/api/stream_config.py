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

