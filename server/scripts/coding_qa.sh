#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-https://2ndopinionmd.ai}"

run_test() {
  local name="$1"
  local query="$2"
  local sources="$3"
  local limit="$4"
  local ctx_k="$5"

  echo
  echo "================================================================================"
  echo "TEST: $name"
  echo "================================================================================"
  echo

  curl -N "${BASE_URL}/api/rag/coding_stream" \
    --get \
    --data-urlencode "q=${query}" \
    --data-urlencode "sources=${sources}" \
    --data-urlencode "limit=${limit}" \
    --data-urlencode "ctx_k=${ctx_k}" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "use_valyu=0"
}

# 1) HFrEF guideline-based bundle (dx + meds + labs)
run_test \
  "01_hfref_bundle_guideline_coding" \
  "In an adult with chronic HFrEF (EF ≤40%) on guideline-directed therapy, provide ICD-10-CM, ICD-11, SNOMED CT, LOINC, and RxNorm codes for: (1) the primary HFrEF diagnosis, (2) evidence-based HF medications (ACEi/ARB/ARNI, evidence-based beta-blockers, MRA, SGLT2 inhibitors), and (3) key monitoring labs (BNP/NT-proBNP, basic metabolic panel, potassium, creatinine, and eGFR). Avoid generic heart failure codes when more specific HFrEF or acute-on-chronic codes are present." \
  "icd10cm,icd11,snomed,loinc,rxnorm,hpo,chv" \
  20 \
  128

# 2) Sepsis + organ failures (ICU septic shock)
run_test \
  "02_septic_shock_aki_resp_failure" \
  "Provide ICD-10-CM, ICD-11, SNOMED CT, LOINC, and RxNorm codes for septic shock in an ICU patient with acute kidney injury and acute respiratory failure. Include separate slots for: (1) underlying sepsis/septic shock, (2) acute organ failures (AKI and respiratory failure), (3) key sepsis labs such as lactate, blood cultures, and a basic metabolic panel, and (4) vasopressor and broad-spectrum antibiotic therapy. Prefer shock-specific and organ-failure-specific codes over generic sepsis codes when available." \
  "icd10cm,icd11,snomed,loinc,rxnorm,hpo,chv" \
  20 \
  128

# 3) CKD with HTN and diabetes
run_test \
  "03_ckd3b_diabetes_hypertension" \
  "For an adult with type 2 diabetes, chronic kidney disease stage 3b, and hypertension, provide ICD-10-CM, ICD-11, SNOMED CT, LOINC, and RxNorm codes for: (1) CKD stage and etiology (diabetic nephropathy if appropriate), (2) essential hypertension and diabetic hypertension variants, (3) diabetes with renal complications, (4) monitoring labs (BMP, ACR, eGFR, potassium), and (5) common ACEi/ARB therapy. Prefer codes that explicitly link diabetes, CKD, and hypertension when such combination codes exist." \
  "icd10cm,icd11,snomed,loinc,rxnorm,hpo,chv" \
  20 \
  128

# 4) Premenopausal ER+/PR+/HER2- breast cancer
run_test \
  "04_premenop_breast_ca_erpr_her2neg" \
  "In a premenopausal woman with newly diagnosed stage III ER-positive, PR-positive, HER2-negative invasive ductal carcinoma of the left breast, who is planned for neoadjuvant chemotherapy followed by surgery and adjuvant endocrine therapy, provide ICD-10-CM, ICD-11, SNOMED CT, LOINC, and RxNorm codes for: (1) primary breast cancer diagnosis including laterality and receptor status when available, (2) relevant staging or metastasis codes, (3) core pathology and receptor testing labs, and (4) representative chemotherapy and endocrine therapy options. Avoid overly generic breast cancer codes when more specific ones exist." \
  "icd10cm,icd11,snomed,loinc,rxnorm,hpo,chv" \
  24 \
  128

# 5) Ulcerative colitis pancolitis moderate-to-severe
run_test \
  "05_uc_pancolitis_mod_severe" \
  "For an adult with long-standing ulcerative colitis presenting with moderate-to-severe pancolitis, provide ICD-10-CM, ICD-11, SNOMED CT, LOINC, and RxNorm codes for: (1) UC pancolitis with severity, (2) colonoscopy and biopsy procedures, (3) inflammatory markers and stool studies, and (4) step-up medical therapy options (5-ASA, systemic steroids, biologics, and JAK inhibitors). Prefer codes that distinguish pancolitis from left-sided colitis when available." \
  "icd10cm,icd11,snomed,loinc,rxnorm,hpo,chv" \
  20 \
  128

# 6) RA high disease activity + pregnancy planning (mixed guideline/coding)
run_test \
  "06_ra_high_activity_ild_pregnancy" \
  "In a 32-year-old woman with high disease activity rheumatoid arthritis and mild RA-associated interstitial lung disease who wishes to conceive in the next 1–2 years, provide ICD-10-CM, ICD-11, SNOMED CT, LOINC, and RxNorm codes for: (1) seropositive RA with erosions, (2) RA-associated ILD, (3) RA activity markers and monitoring labs, and (4) pregnancy-compatible csDMARDs and biologics versus drugs that should be avoided. Distinguish RA-ILD from idiopathic ILD when possible." \
  "icd10cm,icd11,snomed,loinc,rxnorm,hpo,chv" \
  20 \
  128

# 7) HPO-driven adult cerebellar ataxia phenotype
run_test \
  "07_hpo_adult_cerebellar_ataxia" \
  "You are coding for an adult patient with progressive gait ataxia, dysarthria, nystagmus, and limb incoordination with strong suspicion for a hereditary spinocerebellar ataxia syndrome. Provide HPO, SNOMED CT, ICD-10-CM, and ICD-11 codes for: (1) the cerebellar ataxia phenotype, (2) associated ocular and speech findings, and (3) a generic hereditary ataxia diagnosis. Emphasize clean phenotype coverage in HPO while also surfacing appropriate billing codes." \
  "icd10cm,icd11,snomed,hpo,chv" \
  18 \
  128

# 8) HPO-driven child with global developmental delay and hypotonia
run_test \
  "08_hpo_child_gdd_hypotonia" \
  "For a 3-year-old child with global developmental delay, axial hypotonia, poor head control, and delayed gross motor milestones, provide HPO, SNOMED CT, ICD-10-CM, and ICD-11 codes for: (1) global developmental delay and intellectual disability risk, (2) motor and tone phenotypes, and (3) a non-specific genetic syndrome placeholder. Prioritize high-quality HPO coverage, then map to core billing codes." \
  "icd10cm,icd11,snomed,hpo,chv" \
  18 \
  128

# 9) Chronic coronary disease: prior MI, HTN, hyperlipidemia
run_test \
  "09_chronic_coronary_disease_followup" \
  "In an adult with a history of prior MI, stable angina, hypertension, and hyperlipidemia on guideline-directed secondary prevention, provide ICD-10-CM, ICD-11, SNOMED CT, LOINC, and RxNorm codes for: (1) chronic coronary syndrome/prior MI, (2) hypertension and hyperlipidemia, (3) key secondary-prevention medications (aspirin, high-intensity statin, beta-blocker, ACEi/ARB), and (4) monitoring labs (lipid panel, liver function tests, basic metabolic panel). Prefer stable, chronic disease codes rather than acute MI codes." \
  "icd10cm,icd11,snomed,loinc,rxnorm,hpo,chv" \
  20 \
  128

# 10) SNOMED-only PCI + stent procedure focus
run_test \
  "10_snomed_only_pci_lad_des" \
  "Provide SNOMED CT procedure codes only for invasive coronary angiography with percutaneous coronary intervention (PCI) to the left anterior descending (LAD) artery with drug-eluting stent placement. Include: (1) diagnostic coronary angiography, (2) PCI to the LAD, and (3) deployment of a drug-eluting stent in the LAD. Retrieve all clinically relevant SNOMED CT procedure codes first, then cluster away only trivial duplicates while preserving distinct clinically meaningful variants. Do NOT return ICD-10-CM, ICD-11, LOINC, RxNorm, HPO, or CHV codes." \
  "snomed" \
  16 \
  128

# 11) RxNorm-heavy HF medication mapping
run_test \
  "11_rxnorm_hf_medication_mapping" \
  "For a patient with chronic HFrEF on guideline-directed medical therapy, map the following medication classes to RxNorm codes and, where relevant, SNOMED CT products: ACE inhibitors, ARBs, ARNIs, evidence-based beta-blockers, mineralocorticoid receptor antagonists, and SGLT2 inhibitors. Provide representative but not exhaustive RxNorm clinical drugs and ingredient-level concepts. Focus purely on medications; do not return diagnosis, lab, or procedure codes." \
  "rxnorm,snomed" \
  24 \
  128

# 12) LOINC-heavy sepsis lab panel
run_test \
  "12_loinc_sepsis_lab_panel" \
  "Create a sepsis-focused laboratory panel using LOINC (with optional supporting SNOMED CT), including: (1) serum lactate, (2) blood cultures, (3) complete blood count with differential, (4) basic metabolic panel, and (5) liver function tests. Provide the most commonly used LOINC codes suitable for adult ICU sepsis care, clustering trivial variants but preserving distinct clinically meaningful options where needed. Do not include diagnosis or medication codes." \
  "loinc,snomed" \
  20 \
  128
