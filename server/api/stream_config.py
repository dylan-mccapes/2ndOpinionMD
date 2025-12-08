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
BASE_RRF_K = 32
BASE_LIMIT = 10

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
    # -------------------------
    # AASLD – Hepatology
    # -------------------------
    "aasld_hcc_2018": {
        "title": "AASLD 2018 Guidance on Hepatocellular Carcinoma",
        "society": "AASLD",
        "year": 2018,
        "domain": "hepatology_oncology",
        "condition": "hepatocellular_carcinoma",
        "file_name": "aasld-hcc-2018.pdf",
        "summary": (
            "Surveillance, diagnosis, staging, and treatment selection for HCC in patients "
            "with chronic liver disease and cirrhosis."
        ),
    },
    "aasld_nafld_nash_2018": {
        "title": "AASLD 2018 Guidance on Nonalcoholic Fatty Liver Disease",
        "society": "AASLD",
        "year": 2018,
        "domain": "hepatology",
        "condition": "nonalcoholic_fatty_liver_disease",
        "file_name": "aasld-nafld-nash-2018.pdf",
        "summary": (
            "Workup of suspected NAFLD/NASH, fibrosis risk stratification, lifestyle and "
            "pharmacologic treatment, and long-term monitoring."
        ),
    },
    "aasld_portal_hypertension_2024": {
        "title": "AASLD 2024 Guidance on Portal Hypertension",
        "society": "AASLD",
        "year": 2024,
        "domain": "hepatology",
        "condition": "portal_hypertension_cirrhosis",
        "file_name": "aasld-portal-hypertension-2024.pdf",
        "summary": (
            "Screening and management of varices and portal hypertension in cirrhosis, "
            "including nonselective beta-blockers, endoscopic therapy, and TIPS."
        ),
    },

    # -------------------------
    # ACC/AHA – Cardiology
    # -------------------------
    "acc_aha_afib_2019": {
        "title": "2019 AHA/ACC/HRS Atrial Fibrillation Guideline",
        "society": "AHA_ACC_HRS",
        "year": 2019,
        "domain": "cardiology_electrophysiology",
        "condition": "atrial_fibrillation",
        "file_name": "acc-aha-afib-2019.pdf",
        "summary": (
            "Evaluation and management of atrial fibrillation including rate/rhythm control, "
            "stroke prevention, and ablation considerations."
        ),
    },
    "acc_aha_ccd_2023": {
        "title": "2023 AHA/ACC Guideline for Chronic Coronary Disease",
        "society": "AHA_ACC",
        "year": 2023,
        "domain": "cardiology",
        "condition": "chronic_coronary_disease",
        "file_name": "acc-aha-ccd-2023.pdf",
        "summary": (
            "Diagnosis and long-term management of chronic coronary disease, including "
            "antianginal therapy, lipid lowering, and secondary prevention."
        ),
    },
    "acc_aha_chest_pain_2021": {
        "title": "2021 ACC/AHA Guideline for Evaluation of Chest Pain",
        "society": "ACC_AHA",
        "year": 2021,
        "domain": "cardiology_emergency",
        "condition": "suspected_ischemic_chest_pain",
        "file_name": "acc-aha-chest-pain-2021.pdf",
        "summary": (
            "Structured evaluation of acute and stable chest pain, risk stratification, "
            "and selection of noninvasive and invasive testing."
        ),
    },
    "acc_aha_chol_2018": {
        "title": "2018 ACC/AHA Blood Cholesterol Guideline",
        "society": "ACC_AHA",
        "year": 2018,
        "domain": "cardiology_prevention",
        "condition": "hyperlipidemia",
        "file_name": "acc-aha-cholesterol-2018.pdf",
        "summary": (
            "Statin and non-statin therapy for ASCVD prevention, including risk estimation, "
            "treatment thresholds, and intensity selection."
        ),
    },
    "acc_aha_hcm_2020": {
        "title": "2020 AHA/ACC Hypertrophic Cardiomyopathy Guideline",
        "society": "AHA_ACC",
        "year": 2020,
        "domain": "cardiology",
        "condition": "hypertrophic_cardiomyopathy",
        "file_name": "acc-aha-hcm-2020.pdf",
        "summary": (
            "Diagnosis and management of HCM including family screening, risk "
            "stratification for SCD, and medical or septal reduction therapies."
        ),
    },
    "acc_aha_hfsa_hf_2022": {
        "title": "2022 ACC/AHA/HFSA Heart Failure Guideline",
        "society": "ACC_AHA_HFSA",
        "year": 2022,
        "domain": "cardiology",
        "condition": "heart_failure",
        "file_name": "acc-aha-hfsa-hf-2022.pdf",
        "summary": (
            "Diagnosis, staging, and guideline-directed medical therapy for HFrEF and "
            "HFpEF, plus devices and advanced HF management."
        ),
    },
    "acc_aha_htn_2017": {
        "title": "2017 ACC/AHA Hypertension Guideline",
        "society": "ACC_AHA",
        "year": 2017,
        "domain": "cardiology",
        "condition": "hypertension",
        "file_name": "acc-aha-htn-2017.pdf",
        "summary": (
            "Blood pressure classification, cardiovascular risk assessment, and treatment "
            "targets and regimens in adults with hypertension."
        ),
    },
    "acc_aha_pad_2016": {
        "title": "2016 AHA/ACC Peripheral Artery Disease Guideline",
        "society": "ACC_AHA",
        "year": 2016,
        "domain": "cardiology_vascular",
        "condition": "pad_lower_extremity",
        "file_name": "acc-aha-pad-2016.pdf",
        "summary": (
            "Diagnosis and treatment of lower extremity PAD, including antiplatelet "
            "therapy, exercise programs, and revascularization."
        ),
    },
    "acc_aha_primary_prevention_2019": {
        "title": "2019 ACC/AHA Primary Prevention of Cardiovascular Disease",
        "society": "ACC_AHA",
        "year": 2019,
        "domain": "cardiology_prevention",
        "condition": "atherosclerotic_cvd_prevention",
        "file_name": "acc-aha-primary-prevention-2019.pdf",
        "summary": (
            "Risk estimation and primary prevention strategies with lifestyle, blood "
            "pressure, lipids, and diabetes management."
        ),
    },
    "acc_aha_valvular_2020": {
        "title": "2020 ACC/AHA Valvular Heart Disease Guideline",
        "society": "ACC_AHA",
        "year": 2020,
        "domain": "cardiology",
        "condition": "valvular_heart_disease",
        "file_name": "acc-aha-valvular-2020.pdf",
        "summary": (
            "Evaluation and timing of intervention for valve lesions, including choice "
            "between surgical and transcatheter therapies."
        ),
    },

    # -------------------------
    # ACG / ACOG – GI & OB
    # -------------------------
    "acg_crohns_2018": {
        "title": "ACG Guideline: Management of Crohn’s Disease in Adults",
        "society": "ACG",
        "year": 2018,
        "domain": "gastroenterology",
        "condition": "crohns_disease",
        "file_name": "acg-crohns-2018.pdf",
        "summary": (
            "Diagnosis, risk stratification, and induction/maintenance treatment choices "
            "for Crohn’s disease including biologics and immunomodulators."
        ),
    },
    "acg_gerd_2022": {
        "title": "ACG 2022 Guideline for GERD",
        "society": "ACG",
        "year": 2022,
        "domain": "gastroenterology",
        "condition": "gastroesophageal_reflux",
        "file_name": "acg-gerd-2022.pdf",
        "summary": (
            "Evaluation of typical and atypical GERD, PPI therapy, diagnostic testing, "
            "and when to consider antireflux procedures."
        ),
    },
    "acg_lower_gi_bleed_2016": {
        "title": "ACG Guideline: Acute Lower Gastrointestinal Bleeding",
        "society": "ACG",
        "year": 2016,
        "domain": "gastroenterology",
        "condition": "lower_gi_bleeding",
        "file_name": "acg-lower-gi-bleeding-2016.pdf",
        "summary": (
            "Initial stabilization, timing and preparation for colonoscopy, and "
            "endoscopic, radiologic, or surgical management of lower GI bleeding."
        ),
    },
    "acg_pancreatitis_2013": {
        "title": "ACG Guideline: Management of Acute Pancreatitis",
        "society": "ACG",
        "year": 2013,
        "domain": "gastroenterology",
        "condition": "acute_pancreatitis",
        "file_name": "acg-acute-pancreatitis-2013.pdf",
        "summary": (
            "Diagnosis, early risk assessment, fluid resuscitation, nutrition, and "
            "management of gallstone and necrotizing pancreatitis."
        ),
    },
    "acg_uc_2019": {
        "title": "ACG Guideline: Ulcerative Colitis in Adults",
        "society": "ACG",
        "year": 2019,
        "domain": "gastroenterology",
        "condition": "ulcerative_colitis",
        "file_name": "acg-ulcerative-colitis-2019.pdf",
        "summary": (
            "Induction and maintenance therapy for UC, including outpatient and inpatient "
            "severe disease and dysplasia surveillance strategies."
        ),
    },
    "acog_htn_pregnancy_2020": {
        "title": "ACOG 2020 Hypertension in Pregnancy Guidance",
        "society": "ACOG",
        "year": 2020,
        "domain": "obstetrics",
        "condition": "gestational_hypertensive_disorders",
        "file_name": "acog-hypertension-pregnancy-2020.pdf",
        "summary": (
            "Diagnosis and management of gestational hypertension and preeclampsia, "
            "including timing of delivery and medication choices in pregnancy."
        ),
    },

    # -------------------------
    # ACR – Rheumatology
    # -------------------------
    "acr_ild_2023": {
        "title": "ACR 2023 Guideline for SARD-Associated ILD",
        "society": "ACR",
        "year": 2023,
        "domain": "rheumatology_pulmonology",
        "condition": "sard_interstitial_lung_disease",
        "file_name": "acr-2023-ild-treatment.pdf",
        "summary": (
            "Screening and management of interstitial lung disease in systemic autoimmune "
            "rheumatic diseases, including RA-ILD."
        ),
    },
    "acr_ra_2021": {
        "title": "ACR 2021 Guideline for Treatment of Rheumatoid Arthritis",
        "society": "ACR",
        "year": 2021,
        "domain": "rheumatology",
        "condition": "rheumatoid_arthritis",
        "file_name": "ra-guideline-2021.pdf",
        "summary": (
            "Choice and sequencing of csDMARDs, biologic, and targeted synthetic DMARDs "
            "for RA across disease activity states and comorbidities."
        ),
    },
    "acr_reproductive_health_2020": {
        "title": "ACR 2020 Guideline for Reproductive Health in Rheumatic Disease",
        "society": "ACR",
        "year": 2020,
        "domain": "rheumatology_obstetrics",
        "condition": "reproductive_health_rmd",
        "file_name": "acr-reproductive-health-2020.pdf",
        "summary": (
            "Pre-conception counseling, medication safety, and pregnancy management for "
            "people with rheumatic and musculoskeletal diseases."
        ),
    },
    "acr_vf_anca_2021": {
        "title": "ACR/VF 2021 ANCA-Associated Vasculitis Guideline",
        "society": "ACR_VF",
        "year": 2021,
        "domain": "rheumatology",
        "condition": "anca_associated_vasculitis",
        "file_name": "acr-vf-anca-vasculitis-2021.pdf",
        "summary": (
            "Induction and maintenance therapy for GPA and MPA, including glucocorticoid-"
            "sparing regimens and relapse management."
        ),
    },

    # -------------------------
    # ADA / Endocrine / Obesity
    # -------------------------
    "ada_diabetes_2024": {
        "title": "ADA 2024 Diabetes Management Guideline",
        "society": "ADA",
        "year": 2024,
        "domain": "endocrinology",
        "condition": "diabetes_mellitus",
        "file_name": "ada-diabetes-2024.pdf",
        "summary": (
            "High-level recommendations for screening, diagnosis, and treatment of "
            "diabetes, complementary to the full Standards of Care."
        ),
    },
    "ada_dm_2024": {
        "title": "ADA 2024 Standards of Care in Diabetes",
        "society": "ADA",
        "year": 2024,
        "domain": "endocrinology",
        "condition": "diabetes",
        "file_name": "ada-diabetes-standards-2024.pdf",
        "summary": (
            "Comprehensive standards for diabetes care including glycemic targets, "
            "pharmacotherapy, cardiovascular risk, CKD, and special populations."
        ),
    },
    "aha_acc_tos_obesity_2013": {
        "title": "2013 AHA/ACC/TOS Obesity Management Guideline",
        "society": "AHA_ACC_TOS",
        "year": 2013,
        "domain": "cardiometabolic",
        "condition": "overweight_obesity",
        "file_name": "aha-acc-tos-obesity-2013.pdf",
        "summary": (
            "Assessment and treatment of overweight and obesity with lifestyle, "
            "pharmacologic, and surgical weight-loss interventions."
        ),
    },
    "endocrine_osteoporosis_2019": {
        "title": "Endocrine Society 2019 Osteoporosis Guideline",
        "society": "Endocrine_Society",
        "year": 2019,
        "domain": "endocrinology",
        "condition": "postmenopausal_osteoporosis",
        "file_name": "endocrine-osteoporosis-postmenopausal-2019.pdf",
        "summary": (
            "Evaluation and treatment of postmenopausal osteoporosis, including fracture "
            "risk assessment, calcium/vitamin D, and pharmacotherapy."
        ),
    },

    # -------------------------
    # Stroke & VTE
    # -------------------------
    "aha_asa_stroke_2019_acute": {
        "title": "2019 AHA/ASA Acute Ischemic Stroke Guideline",
        "society": "AHA_ASA",
        "year": 2019,
        "domain": "neurology_stroke",
        "condition": "acute_ischemic_stroke",
        "file_name": "aha_asa_stroke_2019_acute.pdf",
        "summary": (
            "Time-sensitive evaluation, IV thrombolysis, and endovascular therapy for "
            "acute ischemic stroke."
        ),
    },
    "aha_asa_stroke_2023": {
        "title": "AHA/ASA 2023 Stroke Systems and Care Update",
        "society": "AHA_ASA",
        "year": 2023,
        "domain": "neurology_stroke",
        "condition": "acute_ischemic_stroke",
        "file_name": "aha-asa-stroke-2023.pdf",
        "summary": (
            "Updated recommendations around systems of care, triage, and management of "
            "acute ischemic stroke and related emergencies."
        ),
    },
    "chest_vte_2021": {
        "title": "CHEST 2021 Venous Thromboembolism Guideline",
        "society": "CHEST",
        "year": 2021,
        "domain": "hematology_thrombosis",
        "condition": "venous_thromboembolism",
        "file_name": "chest-vte-2021.pdf",
        "summary": (
            "Diagnosis and treatment of DVT and PE, choice and duration of "
            "anticoagulation, and management in special populations."
        ),
    },

    # -------------------------
    # Pulmonology / Asthma / COPD / PH
    # -------------------------
    "ats_ers_severe_asthma_2020": {
        "title": "ATS/ERS 2020 Severe Asthma Guideline",
        "society": "ATS_ERS",
        "year": 2020,
        "domain": "pulmonology",
        "condition": "severe_asthma",
        "file_name": "ats-ers-severe-asthma-2020.pdf",
        "summary": (
            "Definition, phenotyping, and biologic treatment strategies for severe "
            "asthma refractory to standard therapy."
        ),
    },
    "gina_asthma_2023": {
        "title": "GINA 2023 Global Strategy for Asthma",
        "society": "GINA",
        "year": 2023,
        "domain": "pulmonology",
        "condition": "asthma",
        "file_name": "gina-asthma-2023.pdf",
        "summary": (
            "Stepwise asthma management emphasizing inhaled corticosteroids, "
            "reliever strategies, and risk-based treatment adjustment."
        ),
    },
    "gold_copd_2023": {
        "title": "GOLD 2023 COPD Report",
        "society": "GOLD",
        "year": 2023,
        "domain": "pulmonology",
        "condition": "chronic_obstructive_pulmonary_disease",
        "file_name": "gold-copd-2023.pdf",
        "summary": (
            "Diagnosis, ABCD/ABE assessment, pharmacologic and non-pharmacologic "
            "treatment, and exacerbation prevention in COPD."
        ),
    },
    "gold_copd_2024": {
        "title": "GOLD 2024 COPD Report",
        "society": "GOLD",
        "year": 2024,
        "domain": "pulmonology",
        "condition": "copd",
        "file_name": "gold-2024-report.pdf",
        "summary": (
            "Updated COPD recommendations, including symptom/risk grouping, inhaler "
            "regimens, and follow-up strategies."
        ),
    },
    "esc_ers_ph_2022": {
        "title": "2022 ESC/ERS Pulmonary Hypertension Guideline",
        "society": "ESC_ERS",
        "year": 2022,
        "domain": "cardiology_pulmonology",
        "condition": "pulmonary_hypertension",
        "file_name": "esc-ers-2022-pulmonary-hypertension.pdf",
        "summary": (
            "Workup of suspected PH, hemodynamic classification, risk assessment, and "
            "PAH-targeted therapy selection."
        ),
    },

    # -------------------------
    # ESC – Cardiology
    # -------------------------
    "esc_nste_acs_2020": {
        "title": "ESC 2020 Non-ST-Elevation ACS Guideline",
        "society": "ESC",
        "year": 2020,
        "domain": "cardiology",
        "condition": "nste_acs",
        "file_name": "esc-nste-acs-2020.pdf",
        "summary": (
            "Diagnosis, risk stratification, antithrombotic therapy, and invasive "
            "strategy in patients with NSTE-ACS."
        ),
    },

    # -------------------------
    # ESMO – Hematologic Malignancies
    # -------------------------
    "esmo_cll_2020": {
        "title": "ESMO 2020 Guideline for Chronic Lymphocytic Leukaemia",
        "society": "ESMO",
        "year": 2020,
        "domain": "hematology_oncology",
        "condition": "cll",
        "file_name": "esmo_cll_2020.pdf",
        "summary": (
            "Diagnosis, staging, and first-line and relapsed/refractory treatment "
            "options for CLL."
        ),
    },
    "esmo_dlbcl_2020": {
        "title": "ESMO 2020 Diffuse Large B-Cell Lymphoma Guideline",
        "society": "ESMO",
        "year": 2020,
        "domain": "hematology_oncology",
        "condition": "dlbcl",
        "file_name": "esmo-dlbcl-2020.pdf",
        "summary": (
            "Initial and salvage therapy for DLBCL, including role of chemoimmunotherapy "
            "and consolidation approaches."
        ),
    },
    "esmo_fl_2025": {
        "title": "ESMO 2025 Follicular Lymphoma Guideline",
        "society": "ESMO",
        "year": 2025,
        "domain": "hematology_oncology",
        "condition": "follicular_lymphoma",
        "file_name": "esmo-fl-2025.pdf",
        "summary": (
            "Risk stratification, watchful waiting vs treatment, and systemic options "
            "for follicular lymphoma."
        ),
    },
    "esmo_mzl_2020": {
        "title": "ESMO 2020 Marginal Zone Lymphoma Guideline",
        "society": "ESMO",
        "year": 2020,
        "domain": "hematology_oncology",
        "condition": "marginal_zone_lymphoma",
        "file_name": "esmo-mzl-2020.pdf",
        "summary": (
            "Workup and management of nodal, extranodal, and splenic marginal zone "
            "lymphomas, including systemic and local therapies."
        ),
    },

    # -------------------------
    # EULAR / ASAS – Rheumatology
    # -------------------------
    "eular_acr_sle_2019": {
        "title": "2019 EULAR/ACR SLE Classification Criteria",
        "society": "EULAR_ACR",
        "year": 2019,
        "domain": "rheumatology",
        "condition": "sle_classification",
        "file_name": "eular-acr-2019-sle-classification.pdf",
        "summary": (
            "Classification criteria for systemic lupus erythematosus used to support "
            "diagnosis and research cohort definition."
        ),
    },
    "eular_axspa_2022": {
        "title": "ASAS/EULAR 2022 Axial Spondyloarthritis Recommendations",
        "society": "ASAS_EULAR",
        "year": 2022,
        "domain": "rheumatology",
        "condition": "axial_spondyloarthritis",
        "file_name": "asas-eular-axspa-2022.pdf",
        "summary": (
            "Treatment algorithm for axial spondyloarthritis including NSAIDs, biologics, "
            "and treatment targets."
        ),
    },
    "eular_ra_2022": {
        "title": "EULAR 2022 RA Management Recommendations",
        "society": "EULAR",
        "year": 2022,
        "domain": "rheumatology",
        "condition": "rheumatoid_arthritis",
        "file_name": "eular-ra-management-2022.pdf",
        "summary": (
            "Treat-to-target RA strategy with csDMARDs, biologics, and JAK inhibitors, "
            "including comorbidity considerations."
        ),
    },
    "eular_sle_nephritis_2025": {
        "title": "EULAR 2025 Lupus Nephritis Recommendations",
        "society": "EULAR",
        "year": 2025,
        "domain": "rheumatology_nephrology",
        "condition": "lupus_nephritis",
        "file_name": "eular-2025-sle-nephritis.pdf",
        "summary": (
            "Biopsy indications, histologic classes, and induction and maintenance "
            "regimens for lupus nephritis."
        ),
    },

    # -------------------------
    # IDSA / Infectious Diseases
    # -------------------------
    "idsa_asymptomatic_bacteriuria_2019": {
        "title": "IDSA 2019 Asymptomatic Bacteriuria Guideline",
        "society": "IDSA",
        "year": 2019,
        "domain": "infectious_disease",
        "condition": "asymptomatic_bacteriuria",
        "file_name": "idsa-asymptomatic-bacteriuria-2019.pdf",
        "summary": (
            "When to screen for and treat asymptomatic bacteriuria and when antibiotics "
            "should be avoided."
        ),
    },
    "idsa_candidiasis_2016_2018": {
        "title": "IDSA 2016 Candidiasis Guideline (updated 2018)",
        "society": "IDSA",
        "year": 2018,
        "domain": "infectious_disease",
        "condition": "invasive_candidiasis",
        "file_name": "idsa-invasive-candidiasis-2016-2018.pdf",
        "summary": (
            "Management of candidemia and deep-seated Candida infections with antifungal "
            "selection by host and site of infection."
        ),
    },
    "idsa_cap_2022": {
        "title": "IDSA/ATS Community-Acquired Pneumonia Guideline",
        "society": "IDSA_ATS",
        "year": 2022,
        "domain": "infectious_disease_pulmonology",
        "condition": "community_acquired_pneumonia",
        "file_name": "idsa-cap-2022.pdf",
        "summary": (
            "Diagnosis and severity scoring of CAP, site-of-care decisions, and empiric "
            "antibiotic regimens for adults."
        ),
    },
    "idsa_cdi_2016_2018": {
        "title": "IDSA/SHEA C. difficile Infection Guideline",
        "society": "IDSA",
        "year": 2018,
        "domain": "infectious_disease",
        "condition": "c_difficile_infection",
        "file_name": "idsa-cdi-2016-2018.pdf",
        "summary": (
            "Testing, initial and recurrent treatment of CDI, including vancomycin, "
            "fidaxomicin, and consideration of FMT."
        ),
    },
    "idsa_diabetic_foot_2012": {
        "title": "IDSA 2012 Diabetic Foot Infection Guideline",
        "society": "IDSA",
        "year": 2012,
        "domain": "infectious_disease_endocrinology",
        "condition": "diabetic_foot_infection",
        "file_name": "idsa-diabetic-foot-2012.pdf",
        "summary": (
            "Classification, cultures, imaging, and antimicrobial and surgical "
            "management of diabetic foot infections."
        ),
    },
    "idsa_endocarditis_2015": {
        "title": "AHA/IDSA 2015 Infective Endocarditis Guideline",
        "society": "AHA_IDSA",
        "year": 2015,
        "domain": "infectious_disease_cardiology",
        "condition": "infective_endocarditis",
        "file_name": "idsa-endocarditis-2015.pdf",
        "summary": (
            "Diagnosis and antimicrobial and surgical management of native and prosthetic "
            "valve infective endocarditis."
        ),
    },
    "idsa_hap_vap_2016": {
        "title": "IDSA/ATS 2016 HAP/VAP Guideline",
        "society": "IDSA_ATS",
        "year": 2016,
        "domain": "infectious_disease_critical_care",
        "condition": "hap_vap",
        "file_name": "idsa-hap-vap-2016.pdf",
        "summary": (
            "Empiric and targeted therapy for hospital-acquired and ventilator-associated "
            "pneumonia, including MRSA and Pseudomonas coverage decisions."
        ),
    },
    "idsa_opat_2018": {
        "title": "IDSA 2018 Outpatient Parenteral Antimicrobial Therapy Guideline",
        "society": "IDSA",
        "year": 2018,
        "domain": "infectious_disease",
        "condition": "outpatient_iv_antibiotics",
        "file_name": "idsa-opat-2018.pdf",
        "summary": (
            "Patient selection, vascular access, monitoring, and antimicrobial choices "
            "for IV antibiotics given outside the hospital."
        ),
    },
    "idsa_ssti_2014": {
        "title": "IDSA 2014 Skin and Soft Tissue Infection Guideline",
        "society": "IDSA",
        "year": 2014,
        "domain": "infectious_disease",
        "condition": "skin_and_soft_tissue_infections",
        "file_name": "idsa-ssti-2014.pdf",
        "summary": (
            "Management of SSTIs from cellulitis to necrotizing infections, including "
            "MRSA coverage and surgical consultation."
        ),
    },
    "idsa_vertebral_osteomyelitis_2015": {
        "title": "IDSA 2015 Vertebral Osteomyelitis Guideline",
        "society": "IDSA",
        "year": 2015,
        "domain": "infectious_disease",
        "condition": "vertebral_osteomyelitis",
        "file_name": "idsa-vertebral-osteomyelitis-2015.pdf",
        "summary": (
            "Diagnosis and prolonged antimicrobial management of vertebral "
            "osteomyelitis, including when to pursue surgery."
        ),
    },

    # -------------------------
    # KDIGO – Nephrology
    # -------------------------
    "kdigo_aki_2012": {
        "title": "KDIGO 2012 Acute Kidney Injury Guideline",
        "society": "KDIGO",
        "year": 2012,
        "domain": "nephrology",
        "condition": "acute_kidney_injury",
        "file_name": "kdigo-aki-2012.pdf",
        "summary": (
            "Definition and staging of AKI, evaluation of causes, fluid and hemodynamic "
            "management, and initiation of renal replacement therapy."
        ),
    },
    "kdigo_anemia_ckd_2023": {
        "title": "KDIGO 2023 Anemia in CKD Guideline",
        "society": "KDIGO",
        "year": 2023,
        "domain": "nephrology",
        "condition": "anemia_in_ckd",
        "file_name": "kdigo-anemia-ckd-2023.pdf",
        "summary": (
            "Workup and targets for anemia in CKD, iron therapy, ESA and HIF-PHI use, "
            "and transfusion practices."
        ),
    },
    "kdigo_bp_ckd_2021": {
        "title": "KDIGO 2021 Blood Pressure in CKD Guideline",
        "society": "KDIGO",
        "year": 2021,
        "domain": "nephrology",
        "condition": "chronic_kidney_disease",
        "file_name": "kdigo-bp-ckd-2021.pdf",
        "summary": (
            "Blood pressure targets and preferred agents (ACEi/ARB, others) in "
            "patients with CKD, including albuminuria-based thresholds."
        ),
    },
    "kdigo_ckd_2021": {
        "title": "KDIGO 2021 CKD Guideline",
        "society": "KDIGO",
        "year": 2021,
        "domain": "nephrology",
        "condition": "chronic_kidney_disease",
        "file_name": "kdigo-ckd-2021.pdf",
        "summary": (
            "Definition and staging of CKD, risk prediction, and management of CKD "
            "complications and progression."
        ),
    },
    "kdigo_ckd_2024": {
        "title": "KDIGO 2024 CKD Guideline Update",
        "society": "KDIGO",
        "year": 2024,
        "domain": "nephrology",
        "condition": "chronic_kidney_disease",
        "file_name": "kdigo-2024-ckd.pdf",
        "summary": (
            "Updated CKD guidance including refined risk prediction, expanded roles "
            "for SGLT2 inhibitors and other disease-modifying agents."
        ),
    },
    "kdigo_diabetes_ckd_2020": {
        "title": "KDIGO 2020 Diabetes Management in CKD Guideline",
        "society": "KDIGO",
        "year": 2020,
        "domain": "nephrology_endocrinology",
        "condition": "diabetic_ckd",
        "file_name": "kdigo-diabetes-ckd-2020.pdf",
        "summary": (
            "Glycemic targets and kidney-protective therapies for people with diabetes "
            "and CKD, including SGLT2i and RAAS blockade."
        ),
    },
    "kdigo_gn_ln_2021": {
        "title": "KDIGO 2021 Glomerular Diseases Guideline",
        "society": "KDIGO",
        "year": 2021,
        "domain": "nephrology",
        "condition": "glomerular_disease_lupus_nephritis",
        "file_name": "kdigo-2021-glomerular-diseases.pdf",
        "summary": (
            "Evaluation and immunosuppressive treatment of glomerular diseases, "
            "including detailed sections on lupus nephritis."
        ),
    },

    # -------------------------
    # NICE & VA – Multi-condition
    # -------------------------
    "nice": {
        "title": "NICE Guidance Corpus (Cardio-metabolic Subset)",
        "society": "NICE",
        "year": None,
        "domain": "multi",
        "condition": "multi",
        "file_name": None,
        "summary": (
            "Subset of NICE guidelines (e.g., chronic heart failure, diabetes) used for "
            "comparative therapy and pathway recommendations."
        ),
    },
    "nice_ta397_belimumab": {
        "title": "NICE TA397: Belimumab for Active SLE",
        "society": "NICE",
        "year": 2016,
        "domain": "rheumatology",
        "condition": "sle_belimumab_technology_appraisal",
        "file_name": "nice-ta397-belimumab.pdf",
        "summary": (
            "Technology appraisal for use of belimumab in active systemic lupus "
            "erythematosus based on disease activity and prior therapy."
        ),
    },
    "va_guidelines": {
        "title": "VA/DoD Clinical Practice Guideline Collection",
        "society": "VA_DoD",
        "year": None,
        "domain": "multi",
        "condition": "multi",
        "file_name": None,
        "summary": (
            "Mixed VA/DoD guidelines spanning mental health, chronic pain, opioid "
            "therapy, and common chronic medical conditions."
        ),
    },

    # -------------------------
    # Surviving Sepsis Campaign
    # -------------------------
    "ssc_sepsis_2021": {
        "title": "2021 Surviving Sepsis Campaign Guideline",
        "society": "SSC",
        "year": 2021,
        "domain": "critical_care_infectious_disease",
        "condition": "sepsis",
        "file_name": "ssc-2021-sepsis.pdf",
        "summary": (
            "Hour-1 bundle, hemodynamic resuscitation, vasopressor and ventilation "
            "strategies, and adjunctive therapies in sepsis and septic shock."
        ),
    },

    # -------------------------
    # Internal EoH “Guideline”
    # -------------------------
    "eoh_2025": {
        "title": "EoH 2025 Internal Chronic Disease Modeling Corpus",
        "society": "Internal_EOH",
        "year": 2025,
        "domain": "eoh_internal",
        "condition": "chronic_multisystem_disease",
        "file_name": "eoh_gold_2025.pdf",
        "summary": (
            "Internal Ethos-of-Health corpus defining chronic disease patterns, "
            "trajectories, and shared decision frameworks across conditions."
        ),
    },
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

When the question implies a set of clinically essential items (e.g., a syndrome defined by diagnostic criteria, a medication class, a lab panel), you must ensure all clinically essential elements are represented unless they do not exist in the corpus.

If test variants differ only by method, specimen, or reporting format, treat them as clinically equivalent unless the question implies a specific constraint.

If the question implies a clinically essential element by definition (e.g., major diagnostic criteria, core drug classes, canonical tests), ensure they appear unless the corpus truly lacks them.

You must prioritize CLINICAL INTENTION over literal surface wording. 
If the clinical meaning is unambiguous but the exact phrasing is not present in the code title, treat the closest specific alternative as the correct match. 
Do NOT ignore clinically appropriate codes simply because the exact slot wording is not verbatim in the title.

For each returned code, provide a one-sentence justification describing WHY it satisfies the clinical intention. 
If a code is excluded despite semantic similarity, explicitly state WHY it does NOT satisfy the intention (e.g., wrong laterality, disorder vs procedure, nonspecific, body structure only).

BODY STRUCTURE or DISORDER codes must NOT be used to satisfy PROCEDURE slots unless the user explicitly requests anatomical structures or disorders. 
If provided in context, treat them as supportive information only, never as primary coded concepts.

When multiple codes are clinically valid:
Choose the MOST SPECIFIC code available.
Preference order:
1. Specific artery / organ / site
2. Specific variant of procedure or medication class
3. General procedure or diagnostic category
Only fall back to general codes when no specific code is found.

Codes from vocabularies outside the requested domain (e.g., body structure, lab, disorder, SNOMED CT finding) MUST NOT be returned when the request asks only for a specific vocabulary or code domain.
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

A code is a valid match if its title is semantically equivalent, a broader/narrower synonym, or a clinically related expression of the same concept — not only exact phrasing of the slot_label.

A slot may be satisfied by semantically equivalent codes even if the wording differs — do NOT require exact lexical match.

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

Do NOT down-rank or exclude codes merely because they appear less frequently, are lower-confidence matches, or differ in specificity. Clinical correctness outweighs score.
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

A slot may be satisfied by semantically equivalent codes even if the wording differs — do NOT require exact lexical match.

You must aggressively attempt to satisfy every slot. 
A slot may only remain 'unsatisfied' if:
1. No matching codes exist in ledger_snapshot, AND
2. No clinically appropriate near-match exists that partially expresses the concept.

When in doubt, choose the code that best approximates the clinical intention and mark the slot as satisfied.
""".strip()

GUIDELINE_ANSWER_SYSTEM_PROMPT = """
You are the guideline-focused clinical QA model for 2ndOpinionMD.

You always:
- Ground your answer strictly in the fused context you are given.
- Treat formal guidelines as the backbone of the answer.
- Treat research articles (Valyu/PubMed) and case-analog notes (e.g. MIMIC) as supporting evidence.
- Use conservative, uncertainty-aware language.

You CANNOT:
- Invent new trial names, guideline titles, page numbers, URLs, dosing tables, or statistics.
- Make up probabilities, percentages, or effect sizes that do not appear explicitly in the context.
- Treat ICU note corpora (MIMIC) as guidelines or as calibrated prospective evidence.

-------------------------------------------------------------------------------
SOURCE TYPES & GUARDRAILS
-------------------------------------------------------------------------------

You may see different kinds of sources in the fused context:

1. Guideline sources  
   Examples (source names & titles may include):
   - ACR, EULAR, KDIGO, GOLD, ACC/AHA, ESC/ERS, IDSA, NICE, VA, WHO.
   These are the **primary backbone** for management recommendations.

   Rules:
   - When you give concrete treatment recommendations, anchor them to specific
     guideline snippets (e.g. “According to ACR 2021 RA guideline…”).
   - If multiple guidelines disagree or emphasize different priorities, say so.
   - Do not infer details that are not visible in the snippets you were given.

2. Research / trial sources (Valyu / PubMed)
   - Sources whose name or title suggests PubMed, Valyu, trial, cohort, RCT, etc.
   - These refine mechanistic understanding, flare/relapse risks, and special cases.

   Rules:
   - Use them to say things like “consistent with trial data showing…” or
     “observational cohorts suggest…”.
   - Do not fabricate numbers; only repeat numeric values that appear in text.
   - Do not over-generalize small or highly selected cohorts.

3. Case-analog ICU / EHR notes (MIMIC and similar)
   - Any source whose name contains “mimic” (e.g. mimic4_note) is a **de-identified ICU
     note corpus**, not a guideline or trial.
   - These are useful as **case analogs**, not as normative evidence.

   When you use MIMIC/EHR analogs:
   - Treat them as examples of “how this has looked in de-identified ICU patients”.
   - Never state or imply that they are prospective risk models or official guidance.
   - Use language like:
       - “In de-identified ICU case notes (MIMIC), similar patterns of X were seen…”
       - “These ICU patterns are suggestive but not a substitute for guideline-based care.”
   - Do NOT:
       - Turn blurry ICU patterns into precise risk estimates.
       - Override guideline recommendations with ICU case analogs.
   - If they are not clearly relevant, you may ignore them.

-------------------------------------------------------------------------------
CITATION & EVIDENCE BEHAVIOR
-------------------------------------------------------------------------------

When you refer to evidence, always:
- Use short, **human-readable labels** derived from the context:
  - e.g. “ACR 2021 RA guideline”, “EULAR 2022 RA update”, “KDIGO GN/LN 2021”,
    “MIMIC-4 ICU case analog”, “BeSt RA trial”.
- Do NOT invent labels or codes that are not visible in titles/source names.

You do NOT need to output numeric citation indices (e.g. [1], [2]).
Downstream tooling will attach citation metadata based on which context rows
you actually used. Your job is to make the mapping obvious through clear
naming in prose.

-------------------------------------------------------------------------------
REQUIRED OUTPUT LAYOUT
-------------------------------------------------------------------------------

Always respond in **three sections with these exact headings**:

### 1. Clinical answer (guideline-backed)

- 2–5 bullet points or short paragraphs that directly answer the user’s question.
- Anchor concrete recommendations and priorities to guideline themes, for example:
  - “ACR 2021 RA guideline favors methotrexate as first-line csDMARD…”
  - “EULAR 2022 RA update and the 2023 ACR ILD guideline both caution against X…”
- If relevant, make it clear when data are especially strong vs. weak.

### 2. Evidence answer

Organize this section into labeled bullets:

- **Guideline backbone**  
  - Summarize how the key guideline documents you see in context shape the answer.
  - Name them explicitly using their titles/labels.

- **Research & trials (if present)**  
  - Briefly describe any Valyu/PubMed research excerpts that refine risk,
    flare behavior, or special populations.
  - Mention them by short label (e.g. “observational RA-ILD cohort”, “HF RCT with SGLT2i”).

- **Case-analog ICU/EHR notes (if used)**  
  - Only if MIMIC/EHR analogs genuinely clarify the picture.
  - Use them as illustrative examples:
      - “In de-identified ICU notes from MIMIC-4, patients with similar X often had Y…”
  - Explicitly remind the reader that these are **case analogs**, not guidelines.

If a category is not present in context, omit that sub-bullet or say “Not available in retrieved evidence.”

### 3. Limits & uncertainty

Clearly state:
- What you have:
  - Which guideline sets, which types of research, whether MIMIC/EHR notes were present.
- What you do NOT have:
  - No full chart, imaging, local protocol, or live EoH module outputs unless they
    appear explicitly in text/JSON.
- Any important applicability or generalizability limits.
- Encourage guideline-consistent shared decision making rather than rigid rules.

-------------------------------------------------------------------------------
ABSOLUTE PROHIBITIONS
-------------------------------------------------------------------------------
❌ No invented guideline details, citations, or trial names.  
❌ No new numbers (risks, hazard ratios, percentages) beyond what’s shown.  
❌ No treating MIMIC ICU notes as guidelines or calibrated risk tools.  
❌ No claims about data or modules you cannot see in the provided context.
"""


EVIDENCE_MAPPING_SYSTEM_PROMPT = """
You are an evidence-to-claim mapper for 2ndOpinionMD.

Your job:
- Take the final EoH answer text and the list of context documents.
- Break the answer into a small set of clinically meaningful claims.
- For each claim, identify which context docs support it.

Definitions:
- A "claim" is a discrete, clinically relevant statement that a rheumatologist
  might want provenance for. Examples:
    * "This patient's pattern is more RA-like than SLE-like."
    * "Recent flares followed methotrexate dose reductions."
    * "ACR 2021 RA guidelines favor TNF inhibitors unless heart failure is present."

Rules:
- DO NOT invent new evidence or documents.
- Use ONLY the provided context docs as evidence.
- If a claim is more of a conceptual summary and not clearly supported by any
  single doc, you may leave its evidence list empty.
- Prefer a small number of high-signal claims (3–10), not dozens of tiny ones.

Output STRICT JSON with this shape:

{
  "claims": [
    {
      "id": "c1",
      "text": "Short claim text.",
      "category": "diagnostic_landscape" | "flare_risk" | "trajectory" | "guideline" | "research" | "case_analog" | "other",
      "supporting_evidence_ids": ["doc_id_1", "doc_id_2"],
      "support_strength": "strong" | "moderate" | "weak"
    }
  ]
}

Where:
- "doc_id_*" are IDs from the provided context docs.
- Omit claims that are just trivial paraphrases of the question.
"""