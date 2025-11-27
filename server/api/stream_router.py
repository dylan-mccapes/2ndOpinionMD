# server/api/stream_router.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from openai import OpenAI
import json

from .stream_config import CHAT_MODEL

client = OpenAI()

# ---------------------------------------------------------------------------
# Source metadata: used by the router LLM to understand what each source is
# ---------------------------------------------------------------------------

SOURCE_META: Dict[str, Dict[str, Any]] = {
    # ----------------------- Guidelines & practice docs --------------------
    "eoh_2025": {
        "kind": "guideline",
        "title": "Ethos of Health Gold Standard v2 (2025)",
        "society": "Internal_EOH",
        "domain": "computational chronic disease management",
        "condition": "chronic multisystem and autoimmune disease",
        "summary": (
            "Internal multi-module guideline defining a computational framework for chronic illness. "
            "Introduces Stack Levels, Stability Bands, Chronic Baseline Mode (CBM), reflex suppression "
            "governance, psychosomatic analysis (PSI), escalation routing, trend and prognostic engines, "
            "and FHIR-native interoperability for long-term tracking of complex autoimmune and multisystem disease."
        ),
    },
    "acc_aha_hfsa_hf_2022": {
        "kind": "guideline",
        "title": "2022 ACC/AHA/HFSA Guideline for the Management of Heart Failure",
        "society": "ACC/AHA/HFSA",
        "domain": "cardiology",
        "condition": "heart_failure",
        "summary": (
            "Diagnosis, staging, and guideline-directed medical therapy for heart "
            "failure (ARNI, beta blocker, MRA, SGLT2i, devices, advanced HF)."
        ),
    },
        "acc_aha_afib_2019": {
        "kind": "guideline",
        "title": "2019 AHA/ACC/HRS Guideline for the Management of Patients With Atrial Fibrillation",
        "society": "AHA/ACC/HRS",
        "domain": "cardiology",
        "condition": "atrial_fibrillation",
        "summary": (
            "Stroke risk stratification (CHA2DS2-VASc), anticoagulation choices "
            "(DOAC vs warfarin), and rate vs rhythm control strategies including "
            "cardioversion and catheter ablation."
        ),
    },
    "acc_aha_chol_2018": {
        "kind": "guideline",
        "title": "2018 ACC/AHA Multisociety Guideline on the Management of Blood Cholesterol",
        "society": "ACC/AHA",
        "domain": "cardiology",
        "condition": "dyslipidemia",
        "summary": (
            "LDL-C thresholds for initiating and intensifying statin therapy, "
            "high- vs moderate-intensity statin criteria, use of risk enhancers, "
            "and when to add ezetimibe or PCSK9 inhibitors."
        ),
    },
    "acc_aha_htn_2017": {
        "kind": "guideline",
        "title": "2017 ACC/AHA Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults",
        "society": "ACC/AHA",
        "domain": "cardiology",
        "condition": "hypertension",
        "summary": (
            "Blood pressure classification (normal, elevated, stage 1–2), ASCVD "
            "risk-based decisions for starting antihypertensives, and preferred "
            "drug classes for initial and add-on therapy."
        ),
    },
    "acc_aha_primary_prevention_2019": {
        "kind": "guideline",
        "title": "2019 ACC/AHA Guideline on the Primary Prevention of Cardiovascular Disease",
        "society": "ACC/AHA",
        "domain": "cardiology",
        "condition": "primary_cvd_prevention",
        "summary": (
            "Global ASCVD risk assessment, lifestyle interventions, statin and "
            "aspirin use for primary prevention, and tailoring therapy by risk "
            "group and comorbidities."
        ),
    },
    "acc_aha_valvular_2020": {
        "kind": "guideline",
        "title": "2020 ACC/AHA Guideline for the Management of Patients With Valvular Heart Disease",
        "society": "ACC/AHA",
        "domain": "cardiology",
        "condition": "valvular_heart_disease",
        "summary": (
            "Evaluation and timing of intervention for aortic, mitral, tricuspid, "
            "and pulmonary valve disease including TAVR vs SAVR decisions."
        ),
    },
    "ada_dm_2024": {
        "kind": "guideline",
        "title": "ADA Standards of Care in Diabetes 2024",
        "society": "ADA",
        "domain": "endocrinology",
        "condition": "diabetes_mellitus",
        "summary": (
            "Diagnosis of diabetes and prediabetes, glycemic targets, and stepwise "
            "pharmacologic therapy emphasizing GLP-1 RA and SGLT2 inhibitors for "
            "cardio-renal risk reduction."
        ),
    },
    
    "acr_ild_2023": {
        "kind": "guideline",
        "title": "2023 ACR Guideline for Rheumatoid Arthritis–Associated Interstitial Lung Disease",
        "society": "ACR",
        "domain": "rheumatology_pulmonology",
        "condition": "ra_associated_ild",
        "summary": (
            "Screening, when to treat RA-ILD, preferred immunosuppressants, and "
            "drugs to avoid in RA patients with ILD."
        ),
    },
    "acr_ra_2021": {
        "kind": "guideline",
        "title": "2021 ACR Guideline for the Treatment of Rheumatoid Arthritis",
        "society": "ACR",
        "domain": "rheumatology",
        "condition": "rheumatoid_arthritis",
        "summary": (
            "csDMARD, biologic, and targeted synthetic DMARD selection and sequencing "
            "with treat-to-target recommendations and special populations."
        ),
    },
    "aha_asa_stroke_2019_acute": {
        "kind": "guideline",
        "title": "2019 AHA/ASA Guideline for Early Management of Acute Ischemic Stroke",
        "society": "AHA/ASA",
        "domain": "neurology",
        "condition": "acute_ischemic_stroke",
        "summary": (
            "Acute stroke triage, IV alteplase/thrombolysis criteria, "
            "mechanical thrombectomy windows, and ED/hospital management."
        ),
    },
    "aha_asa_stroke_2023": {
        "kind": "guideline",
        "title": "AHA/ASA 2023 Focused Updates to Stroke Guidelines",
        "society": "AHA/ASA",
        "domain": "neurology",
        "condition": "stroke_updates",
        "summary": (
            "Selected updates to acute and secondary prevention stroke management "
            "since prior AHA/ASA full guidelines."
        ),
    },
    "esc_ers_ph_2022": {
        "kind": "guideline",
        "title": "2022 ESC/ERS Guidelines for the Diagnosis and Treatment of Pulmonary Hypertension",
        "society": "ESC/ERS",
        "domain": "cardiology_pulmonology",
        "condition": "pulmonary_hypertension",
        "summary": (
            "PH definitions, diagnostic workup, risk stratification, and PAH-targeted "
            "therapies for different PH groups."
        ),
    },
    "esmo_cll_2020": {
        "kind": "guideline",
        "title": "ESMO 2020 Clinical Practice Guideline for Chronic Lymphocytic Leukaemia",
        "society": "ESMO",
        "domain": "hematology_oncology",
        "condition": "cll",
        "summary": (
            "Workup and risk stratification of CLL and choice of targeted agents or "
            "chemoimmunotherapy."
        ),
    },
    "esmo_dlbcl_2020": {
        "kind": "guideline",
        "title": "ESMO 2020 Clinical Practice Guideline for Diffuse Large B-Cell Lymphoma",
        "society": "ESMO",
        "domain": "hematology_oncology",
        "condition": "dlbcl",
        "summary": (
            "Diagnosis, staging, and first-line and relapsed/refractory treatment "
            "strategies for DLBCL."
        ),
    },
    "esmo_fl_2025": {
        "kind": "guideline",
        "title": "ESMO 2025 Clinical Practice Guideline for Follicular Lymphoma",
        "society": "ESMO",
        "domain": "hematology_oncology",
        "condition": "follicular_lymphoma",
        "summary": (
            "Risk-adapted management of follicular lymphoma including watchful "
            "waiting, first-line, and subsequent therapies."
        ),
    },
    "esmo_mzl_2020": {
        "kind": "guideline",
        "title": "ESMO 2020 Clinical Practice Guideline for Marginal Zone Lymphoma",
        "society": "ESMO",
        "domain": "hematology_oncology",
        "condition": "mzl",
        "summary": (
            "Diagnosis and treatment of extranodal, nodal, and splenic marginal "
            "zone lymphomas."
        ),
    },
    "eular_acr_sle_2019": {
        "kind": "guideline",
        "title": "2019 EULAR/ACR Classification Criteria for Systemic Lupus Erythematosus",
        "society": "EULAR/ACR",
        "domain": "rheumatology",
        "condition": "sle_classification",
        "summary": (
            "Weighted criteria for classifying SLE, often used to define SLE "
            "cohorts in guidelines and research."
        ),
    },
    "eular_ra_2022": {
        "kind": "guideline",
        "title": "2022 EULAR Recommendations for the Management of Rheumatoid Arthritis",
        "society": "EULAR",
        "domain": "rheumatology",
        "condition": "rheumatoid_arthritis",
        "summary": (
            "Treat-to-target strategies, DMARD sequencing, and comorbidity-aware "
            "management of RA."
        ),
    },
    "kdigo_aki_2012": {
        "kind": "guideline",
        "title": "KDIGO 2012 Clinical Practice Guideline for Acute Kidney Injury",
        "society": "KDIGO",
        "domain": "nephrology_critical_care",
        "condition": "acute_kidney_injury",
        "summary": (
            "Diagnostic criteria (AKI staging), evaluation, and management of acute "
            "kidney injury in hospitalized and critically ill patients including "
            "RRT indications and dosing."
        ),
    },
    "acc_aha_ccd_2023": {
        "kind": "guideline",
        "title": "2023 AHA/ACC Guideline for the Management of Patients With Chronic Coronary Disease",
        "society": "AHA/ACC",
        "domain": "cardiology",
        "condition": "chronic_coronary_disease",
        "summary": (
            "Chronic coronary disease (stable CAD) risk stratification, antianginal "
            "therapy, lipid and blood pressure targets, antiplatelet therapy, and "
            "secondary prevention strategies."
        ),
    },
    "idsa_asymptomatic_bacteriuria_2019": {
        "kind": "guideline",
        "title": "IDSA 2019 Guideline for the Management of Asymptomatic Bacteriuria",
        "society": "IDSA",
        "domain": "infectious_disease",
        "condition": "asymptomatic_bacteriuria",
        "summary": (
            "When to screen for and treat asymptomatic bacteriuria (pregnancy, "
            "urologic procedures) and strong recommendations against treatment in "
            "most other populations."
        ),
    },
    "idsa_diabetic_foot_2012": {
        "kind": "guideline",
        "title": "IDSA 2012 Guideline for the Diagnosis and Treatment of Diabetic Foot Infections",
        "society": "IDSA",
        "domain": "infectious_disease_endocrinology",
        "condition": "diabetic_foot_infection",
        "summary": (
                "Classification of diabetic foot infections, recommendations for "
                "imaging, debridement, vascular assessment, and empiric/targeted "
                "antibiotic therapy by severity and risk factors."
        ),
    },
    "acc_aha_hcm_2020": {
        "kind": "guideline",
        "title": "2020 AHA/ACC Guideline for the Diagnosis and Treatment of Patients With Hypertrophic Cardiomyopathy",
        "society": "AHA/ACC",
        "domain": "cardiology",
        "condition": "hypertrophic_cardiomyopathy",
        "summary": (
            "Diagnostic workup (echo, MRI, genetics), risk stratification for "
            "sudden cardiac death, indications for ICD, septal reduction therapy, "
            "and pharmacologic management of obstructive and non-obstructive HCM."
        ),
    },
        "aasld_hcc_2018": {
        "kind": "guideline",
        "title": "AASLD 2018 Practice Guidance on Hepatocellular Carcinoma",
        "society": "AASLD",
        "domain": "hepatology_oncology",
        "condition": "hepatocellular_carcinoma",
        "summary": (
            "Diagnosis, staging, surveillance, and treatment options for "
            "hepatocellular carcinoma in patients with chronic liver disease."
        ),
    },
    "aasld_nafld_nash_2018": {
        "kind": "guideline",
        "title": "AASLD Practice Guidance on Nonalcoholic Fatty Liver Disease",
        "society": "AASLD",
        "domain": "hepatology",
        "condition": "nonalcoholic_fatty_liver_disease",
        "summary": (
            "Epidemiology, noninvasive assessment of fibrosis, indications for "
            "biopsy, and lifestyle/pharmacologic management of NAFLD/NASH."
        ),
    },
    "acg_uc_2019": {
        "kind": "guideline",
        "title": "ACG Clinical Guideline: Ulcerative Colitis in Adults",
        "society": "ACG",
        "domain": "gastroenterology",
        "condition": "ulcerative_colitis",
        "summary": (
            "Diagnosis, disease severity assessment, induction and maintenance "
            "therapy (5-ASA, steroids, biologics, JAK inhibitors), and monitoring "
            "for adults with ulcerative colitis."
        ),
    },
    "acg_crohns_2018": {
        "kind": "guideline",
        "title": "ACG Clinical Guideline: Management of Crohn's Disease in Adults",
        "society": "ACG",
        "domain": "gastroenterology",
        "condition": "crohns_disease",
        "summary": (
            "Evaluation and risk stratification of Crohn's disease, choice of "
            "immunomodulators and biologics, treat-to-target strategies, and "
            "postoperative management."
        ),
    },
    "acg_lower_gi_bleed_2016": {
        "kind": "guideline",
        "title": "ACG Clinical Guideline: Management of Patients With Acute Lower Gastrointestinal Bleeding",
        "society": "ACG",
        "domain": "gastroenterology",
        "condition": "lower_gastrointestinal_bleeding",
        "summary": (
                "Initial resuscitation, risk stratification, timing and preparation "
                "for colonoscopy, and management of common causes of acute lower GI "
                "bleeding."
        ),
    },
        "kdigo_aki_2012": {
        "kind": "guideline",
        "title": "KDIGO 2012 Clinical Practice Guideline for Acute Kidney Injury",
        "society": "KDIGO",
        "domain": "nephrology_critical_care",
        "condition": "acute_kidney_injury",
        "summary": (
            "Definition and staging of AKI, risk assessment, prevention strategies, "
            "diagnostic workup, fluid and hemodynamic management, and indications "
            "for renal replacement therapy in acute kidney injury."
        ),
    },
    "acc_aha_ccd_2023": {
        "kind": "guideline",
        "title": "2023 AHA/ACC Guideline for the Management of Patients With Chronic Coronary Disease",
        "society": "AHA/ACC",
        "domain": "cardiology",
        "condition": "chronic_coronary_disease",
        "summary": (
            "Evaluation and long-term management of chronic coronary disease, "
            "including antianginal therapy, antiplatelet and lipid-lowering "
            "strategies, risk factor modification, and use of revascularization."
        ),
    },
    "idsa_asymptomatic_bacteriuria_2019": {
        "kind": "guideline",
        "title": "IDSA 2019 Guideline for the Management of Asymptomatic Bacteriuria",
        "society": "IDSA",
        "domain": "infectious_disease",
        "condition": "asymptomatic_bacteriuria",
        "summary": (
            "When to screen for and treat asymptomatic bacteriuria, including "
            "pregnancy, urologic procedures, catheterized patients, and "
            "populations in whom antibiotics should be avoided."
        ),
    },
    "idsa_diabetic_foot_2012": {
        "kind": "guideline",
        "title": "IDSA 2012 Guideline for the Diagnosis and Treatment of Diabetic Foot Infections",
        "society": "IDSA",
        "domain": "infectious_disease",
        "condition": "diabetic_foot_infection",
        "summary": (
            "Classification of diabetic foot infections, recommended diagnostic "
            "evaluation, empiric and targeted antimicrobial regimens, and "
            "coordination with surgical and wound care management."
        ),
    },
    "acc_aha_hcm_2020": {
        "kind": "guideline",
        "title": "2020 AHA/ACC Guideline for the Diagnosis and Treatment of Patients With Hypertrophic Cardiomyopathy",
        "society": "AHA/ACC",
        "domain": "cardiology",
        "condition": "hypertrophic_cardiomyopathy",
        "summary": (
            "Screening and genetic evaluation, risk stratification for sudden "
            "cardiac death, pharmacologic therapy, septal reduction strategies, "
            "and lifestyle/sports participation recommendations in HCM."
        ),
    },
    "aasld_hcc_2018": {
        "kind": "guideline",
        "title": "AASLD 2018 Practice Guidance on Hepatocellular Carcinoma",
        "society": "AASLD",
        "domain": "hepatology_oncology",
        "condition": "hepatocellular_carcinoma",
        "summary": (
            "Surveillance in at-risk populations, diagnostic imaging criteria, "
            "staging systems, and selection of curative versus palliative "
            "treatment options for hepatocellular carcinoma."
        ),
    },
    "aasld_nafld_nash_2018": {
        "kind": "guideline",
        "title": "AASLD Practice Guidance on Nonalcoholic Fatty Liver Disease",
        "society": "AASLD",
        "domain": "hepatology",
        "condition": "nonalcoholic_fatty_liver_disease",
        "summary": (
            "Screening and noninvasive risk stratification for NAFLD/NASH, role "
            "of liver biopsy, lifestyle and pharmacologic interventions, and "
            "management of metabolic and cardiovascular comorbidities."
        ),
    },
    "acg_uc_2019": {
        "kind": "guideline",
        "title": "ACG Clinical Guideline: Ulcerative Colitis in Adults",
        "society": "ACG",
        "domain": "gastroenterology",
        "condition": "ulcerative_colitis",
        "summary": (
            "Diagnosis and disease severity assessment, induction and maintenance "
            "therapy across mild to severe UC, treatment of acute severe colitis, "
            "and colorectal cancer surveillance strategies."
        ),
    },
    "acg_crohns_2018": {
        "kind": "guideline",
        "title": "ACG Clinical Guideline: Management of Crohn's Disease in Adults",
        "society": "ACG",
        "domain": "gastroenterology",
        "condition": "crohns_disease",
        "summary": (
            "Diagnostic evaluation and risk stratification for Crohn's disease, "
            "use of corticosteroids, immunomodulators, and biologics, and "
            "management of fistulizing and postoperative disease."
        ),
    },
    "acg_lower_gi_bleed_2016": {
        "kind": "guideline",
        "title": "ACG Clinical Guideline: Management of Patients With Acute Lower Gastrointestinal Bleeding",
        "society": "ACG",
        "domain": "gastroenterology",
        "condition": "lower_gastrointestinal_bleeding",
        "summary": (
            "Initial resuscitation, risk stratification, timing and preparation "
            "for colonoscopy, and management of common causes of acute lower GI "
            "bleeding."
        ),
    },
        "aha_acc_tos_obesity_2013": {
        "kind": "guideline",
        "title": "2013 AHA/ACC/TOS Guideline for the Management of Overweight and Obesity in Adults",
        "society": "AHA/ACC/TOS",
        "domain": "cardiology_endocrinology",
        "condition": "overweight_obesity",
        "summary": (
            "Definitions of overweight and obesity, staging by weight-related "
            "complications, and indications for lifestyle, pharmacologic, and "
            "bariatric surgery interventions in adults."
        ),
    },
    "esc_nste_acs_2020": {
        "kind": "guideline",
        "title": "2020 ESC Guidelines for the Management of Acute Coronary Syndromes in Patients Presenting Without Persistent ST-Segment Elevation",
        "society": "ESC",
        "domain": "cardiology",
        "condition": "nste_acs",
        "summary": (
            "Risk stratification and diagnostic pathways for NSTE-ACS, recommended "
            "timing of invasive angiography, and antithrombotic strategies "
            "tailored to ischemic and bleeding risk."
        ),
    },
    "acr_vf_anca_2021": {
        "kind": "guideline",
        "title": "2021 ACR/VF Guideline for the Management of ANCA-Associated Vasculitis",
        "society": "ACR/VF",
        "domain": "rheumatology_nephrology_pulmonology",
        "condition": "anca_associated_vasculitis",
        "summary": (
            "Induction and maintenance regimens for GPA, MPA, and EGPA; positioning "
            "of rituximab vs cyclophosphamide; and recommendations for relapse "
            "management and glucocorticoid minimization."
        ),
    },
    "acr_reproductive_health_2020": {
        "kind": "guideline",
        "title": "2020 ACR Guideline for the Management of Reproductive Health in Rheumatic and Musculoskeletal Diseases",
        "society": "ACR",
        "domain": "rheumatology_obstetrics",
        "condition": "reproductive_health_rmd",
        "summary": (
            "Preconception counseling, pregnancy-compatible DMARD and biologic "
            "choices, management of teratogenic agents, and postpartum/lactation "
            "considerations in patients with RMDs."
        ),
    },
    "endocrine_osteoporosis_2019": {
        "kind": "guideline",
        "title": "Endocrine Society 2019 Guideline: Pharmacologic Management of Osteoporosis in Postmenopausal Women",
        "society": "Endocrine Society",
        "domain": "endocrinology",
        "condition": "postmenopausal_osteoporosis",
        "summary": (
            "Fracture risk assessment and thresholds for initiating therapy, "
            "selection of antiresorptive vs anabolic agents, treatment duration, "
            "drug holidays, and monitoring of response."
        ),
    },
    "eular_sle_nephritis_2025": {
        "kind": "guideline",
        "title": "2025 EULAR Recommendations for the Management of Lupus Nephritis",
        "society": "EULAR",
        "domain": "rheumatology_nephrology",
        "condition": "lupus_nephritis",
        "summary": (
            "Biopsy indications, histologic classes, induction and maintenance "
            "regimens, and response definitions for LN."
        ),
    },
    "gold_copd_2024": {
        "kind": "guideline",
        "title": "GOLD 2024 Global Initiative for Chronic Obstructive Lung Disease Report",
        "society": "GOLD",
        "domain": "pulmonology",
        "condition": "copd",
        "summary": (
            "Diagnosis and staging of COPD, pharmacologic and non-pharmacologic "
            "treatment, and exacerbation prevention."
        ),
    },
    "kdigo_anemia_ckd_2023": {
        "kind": "guideline",
        "title": "KDIGO 2023 Clinical Practice Guideline for Anemia in Chronic Kidney Disease",
        "society": "KDIGO",
        "domain": "nephrology",
        "condition": "anemia_in_ckd",
        "summary": (
            "Workup of anemia in CKD, iron targets, ESA/HIF-PHI initiation and "
            "dosing, transfusion and special populations."
        ),
    },
    "kdigo_ckd_2024": {
        "kind": "guideline",
        "title": "KDIGO 2024 Clinical Practice Guideline for Chronic Kidney Disease",
        "society": "KDIGO",
        "domain": "nephrology",
        "condition": "chronic_kidney_disease",
        "summary": (
            "Definition and staging of CKD, ACEi/ARB/SGLT2i/finerenone use, and "
            "management of CKD complications."
        ),
    },
    "kdigo_gn_ln_2021": {
        "kind": "guideline",
        "title": "KDIGO 2021 Clinical Practice Guideline for Glomerular Diseases",
        "society": "KDIGO",
        "domain": "nephrology",
        "condition": "glomerular_disease_lupus_nephritis",
        "summary": (
            "Diagnosis and treatment algorithms for glomerular diseases including "
            "lupus nephritis, IgA nephropathy, and others."
        ),
    },
    "idsa_cap_2022": {
        "kind": "guideline",
        "title": "IDSA/ATS Community-Acquired Pneumonia Guideline (AAFP 2022 reprint)",
        "society": "IDSA/ATS",
        "domain": "infectious_disease_pulmonology",
        "condition": "community_acquired_pneumonia",
        "summary": (
            "Adult CAP diagnosis, severity scoring, site-of-care decisions, and "
            "empiric antibiotic regimens for outpatient, inpatient, and ICU."
        ),
    },
        "acc_aha_chest_pain_2021": {
        "kind": "guideline",
        "title": "2021 AHA/ACC Guideline for the Evaluation and Diagnosis of Chest Pain",
        "society": "AHA/ACC",
        "domain": "cardiology_emergency",
        "condition": "suspected_ischemic_chest_pain",
        "summary": (
            "Structured evaluation of acute and stable chest pain, use of high-"
            "sensitivity troponins, risk stratification, and selection of "
            "noninvasive testing (CTCA, stress testing) or invasive angiography."
        ),
    },
    "acc_aha_pad_2016": {
        "kind": "guideline",
        "title": "2016 AHA/ACC Guideline on the Management of Patients With Lower Extremity Peripheral Artery Disease",
        "society": "AHA/ACC",
        "domain": "cardiology_vascular",
        "condition": "peripheral_artery_disease",
        "summary": (
            "Diagnosis of PAD with ankle–brachial index and imaging, "
            "antiplatelet and statin therapy, supervised exercise, and "
            "indications for endovascular or surgical revascularization."
        ),
    },
    "acg_gerd_2022": {
        "kind": "guideline",
        "title": "ACG Clinical Guideline: Diagnosis and Management of Gastroesophageal Reflux Disease",
        "society": "ACG",
        "domain": "gastroenterology",
        "condition": "gastroesophageal_reflux",
        "summary": (
            "Evaluation of typical and atypical GERD symptoms, empiric PPI "
            "therapy, indications for endoscopy, and management of refractory "
            "and extra-esophageal reflux."
        ),
    },
    "acog_htn_pregnancy_2020": {
        "kind": "guideline",
        "title": "ACOG Practice Bulletin: Gestational Hypertension and Preeclampsia (2020)",
        "society": "ACOG",
        "domain": "obstetrics",
        "condition": "gestational_hypertensive_disorders",
        "summary": (
            "Diagnosis and classification of gestational hypertension and "
            "preeclampsia, maternal–fetal monitoring, timing of delivery, and "
            "antihypertensive and magnesium sulfate use in pregnancy."
        ),
    },
    "ada_diabetes_2024": {
        "kind": "guideline",
        "title": "ADA Standards of Medical Care in Diabetes – 2024 (Selected Sections)",
        "society": "ADA",
        "domain": "endocrinology",
        "condition": "diabetes_management",
        "summary": (
            "Focused sections from the 2024 ADA Standards covering glycemic "
            "targets, pharmacologic glucose-lowering therapy, and management of "
            "cardiovascular and kidney risk in people with diabetes."
        ),
    },
    "ats_ers_severe_asthma_2020": {
        "kind": "guideline",
        "title": "ATS/ERS Guideline on the Definition, Evaluation, and Treatment of Severe Asthma (2020 update)",
        "society": "ATS/ERS",
        "domain": "pulmonology_allergy",
        "condition": "severe_asthma",
        "summary": (
            "Criteria for defining severe asthma, recommended workup for "
            "treatable traits, and use of high-dose inhaled therapy and "
            "biologic agents for uncontrolled disease."
        ),
    },
    "chest_vte_2021": {
        "kind": "guideline",
        "title": "CHEST 2021 Guideline and Expert Panel Report on Antithrombotic Therapy for VTE Disease",
        "society": "CHEST",
        "domain": "hematology_thrombosis",
        "condition": "venous_thromboembolism",
        "summary": (
            "Initial and long-term anticoagulation for DVT and PE, duration of "
            "therapy by provoking factors, and management of special situations "
            "such as cancer-associated and subsegmental PE."
        ),
    },
    "gina_asthma_2023": {
        "kind": "guideline",
        "title": "GINA 2023 Global Strategy for Asthma Management and Prevention",
        "society": "GINA",
        "domain": "pulmonology_allergy",
        "condition": "asthma",
        "summary": (
            "Stepwise asthma treatment including ICS-formoterol reliever "
            "strategy, risk factor control, and management of exacerbations and "
            "difficult-to-treat asthma."
        ),
    },
    "gold_copd_2023": {
        "kind": "guideline",
        "title": "GOLD 2023 Global Strategy for the Diagnosis, Management, and Prevention of COPD",
        "society": "GOLD",
        "domain": "pulmonology",
        "condition": "copd",
        "summary": (
            "Diagnosis and spirometric grading of COPD, symptom and exacerbation "
            "risk assessment, initial and follow-up pharmacologic treatment, and "
            "non-pharmacologic interventions."
        ),
    },
    "idsa_endocarditis_2015": {
        "kind": "guideline",
        "title": "2015 AHA/IDSA Guideline for the Management of Infective Endocarditis",
        "society": "AHA/IDSA",
        "domain": "infectious_disease_cardiology",
        "condition": "infective_endocarditis",
        "summary": (
            "Diagnosis of native and prosthetic valve endocarditis, blood "
            "culture and echocardiography strategies, pathogen-specific IV "
            "antibiotic regimens, and indications for surgery."
        ),
    },
    "kdigo_bp_ckd_2021": {
        "kind": "guideline",
        "title": "KDIGO 2021 Clinical Practice Guideline for the Management of Blood Pressure in Chronic Kidney Disease",
        "society": "KDIGO",
        "domain": "nephrology",
        "condition": "blood_pressure_in_ckd",
        "summary": (
            "Blood pressure targets and preferred antihypertensive regimens in "
            "CKD, including ACEi/ARB use, volume management, and integration "
            "with proteinuria and cardiovascular risk."
        ),
    },
    "kdigo_ckd_2021": {
        "kind": "guideline",
        "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease",
        "society": "KDIGO",
        "domain": "nephrology",
        "condition": "chronic_kidney_disease",
        "summary": (
            "Evaluation and staging of CKD, etiology workup, indications for "
            "referral, and general management principles including lifestyle, "
            "cardiovascular risk reduction, and preparation for kidney failure."
        ),
    },
    "kdigo_diabetes_ckd_2020": {
        "kind": "guideline",
        "title": "KDIGO 2020 Clinical Practice Guideline for Diabetes Management in Chronic Kidney Disease",
        "society": "KDIGO",
        "domain": "nephrology_endocrinology",
        "condition": "diabetes_in_ckd",
        "summary": (
            "Use of SGLT2 inhibitors, RAS blockade, GLP-1 receptor agonists, and "
            "other therapies for glycemic and kidney protection in patients "
            "with diabetes and CKD."
        ),
    },
        "idsa_ssti_2014": {
        "kind": "guideline",
        "title": "Practice Guidelines for the Diagnosis and Management of Skin and Soft Tissue Infections: 2014 Update",
        "society": "IDSA",
        "domain": "infectious_disease",
        "condition": "skin_and_soft_tissue_infections",
        "summary": (
            "Evaluation and classification of SSTIs (purulent vs nonpurulent, "
            "mild–severe), indications for incision and drainage, empiric "
            "antibiotic choices including MRSA coverage, and duration of therapy."
        ),
    },
    "idsa_vertebral_osteomyelitis_2015": {
        "kind": "guideline",
        "title": "2015 IDSA Guideline for the Diagnosis and Treatment of Native Vertebral Osteomyelitis in Adults",
        "society": "IDSA",
        "domain": "infectious_disease",
        "condition": "vertebral_osteomyelitis",
        "summary": (
            "Recommended diagnostic workup (MRI, blood cultures, biopsy), "
            "indications for empiric vs targeted antibiotics, treatment duration, "
            "and when to consider surgical intervention."
        ),
    },
    "acg_pancreatitis_2013": {
        "kind": "guideline",
        "title": "ACG Clinical Guideline: Management of Acute Pancreatitis",
        "society": "ACG",
        "domain": "gastroenterology",
        "condition": "acute_pancreatitis",
        "summary": (
            "Initial risk stratification, fluid resuscitation, nutritional "
            "support, timing of imaging, and indications for ERCP and "
            "intervention in acute pancreatitis."
        ),
    },
    "aasld_portal_hypertension_2024": {
        "kind": "guideline",
        "title": "AASLD Practice Guidance on Risk Stratification and Management of Portal Hypertension in Cirrhosis",
        "society": "AASLD",
        "domain": "hepatology",
        "condition": "portal_hypertension_cirrhosis",
        "summary": (
            "Screening and surveillance for esophageal varices, primary and "
            "secondary prophylaxis with nonselective beta blockers or band "
            "ligation, and acute management of variceal bleeding in cirrhosis."
        ),
    },
    "eular_axspa_2022": {
        "kind": "guideline",
        "title": "2022 ASAS–EULAR Recommendations for the Management of Axial Spondyloarthritis",
        "society": "ASAS/EULAR",
        "domain": "rheumatology",
        "condition": "axial_spondyloarthritis",
        "summary": (
            "Treat-to-target approach in axial SpA including NSAID trials, "
            "indications for biologic therapy (TNF and IL-17 inhibitors), and "
            "monitoring and comorbidity management."
        ),
    },
    "idsa_hap_vap_2016": {
        "kind": "guideline",
        "title": "IDSA/ATS 2016 Clinical Practice Guideline for HAP and VAP",
        "society": "IDSA/ATS",
        "domain": "infectious_disease_critical_care",
        "condition": "hospital_acquired_pneumonia_ventilator_associated_pneumonia",
        "summary": (
            "Diagnosis and empiric treatment of HAP/VAP, including when to cover "
            "MRSA and Pseudomonas and how to de-escalate."
        ),
    },
    "idsa_opat_2018": {
        "kind": "guideline",
        "title": "IDSA 2018 Guideline for Outpatient Parenteral Antimicrobial Therapy (OPAT)",
        "society": "IDSA",
        "domain": "infectious_disease",
        "condition": "outpatient_iv_antibiotics",
        "summary": (
            "Patient selection, vascular access, monitoring, and antimicrobial "
            "choices for IV antibiotics outside the hospital."
        ),
    },
    "idsa_candidiasis_2016_2018": {
        "kind": "guideline",
        "title": "IDSA 2016 Guideline for the Management of Candidiasis (updated 2018)",
        "society": "IDSA",
        "domain": "infectious_disease",
        "condition": "invasive_candidiasis",
        "summary": (
            "Diagnosis and treatment of invasive candidiasis (candidemia, deep "
            "infection) by host status and site of infection."
        ),
    },
    "idsa_cdi_2016_2018": {
        "kind": "guideline",
        "title": "IDSA/SHEA Guideline for Clostridioides difficile Infection (2016, updated 2018)",
        "society": "IDSA/SHEA",
        "domain": "infectious_disease",
        "condition": "c_difficile_infection",
        "summary": (
            "Diagnosis and risk stratification of CDI and treatment of initial and "
            "recurrent episodes (vancomycin, fidaxomicin, FMT)."
        ),
    },
    "nice": {
        "kind": "guideline_bundle",
        "title": "NICE Clinical Guidelines (subset)",
        "society": "NICE",
        "domain": "multi",
        "condition": "multi",
        "summary": (
            "Subset of NICE guidelines (e.g., diabetes, heart failure) loaded as a "
            "general evidence bundle; not infection-specific."
        ),
    },
    "nice_ta397_belimumab": {
        "kind": "guideline",
        "title": "NICE TA397 Belimumab for Treating Active Autoimmune Lupus Erythematosus",
        "society": "NICE",
        "domain": "rheumatology",
        "condition": "sle_belimumab",
        "summary": (
            "Technology appraisal of belimumab for SLE including criteria for use "
            "and positioning within therapy."
        ),
    },
    "ssc_sepsis_2021": {
        "kind": "guideline",
        "title": "Surviving Sepsis Campaign 2021 Guidelines",
        "society": "SSC",
        "domain": "critical_care_infectious_disease",
        "condition": "sepsis_septic_shock",
        "summary": (
            "Recognition and early management of sepsis and septic shock, including "
            "bundle elements and hemodynamic support."
        ),
    },
    "va_guidelines": {
        "kind": "guideline_bundle",
        "title": "VA/DoD Clinical Practice Guidelines (multiple conditions)",
        "society": "VA/DoD",
        "domain": "multi",
        "condition": "multi",
        "summary": (
            "Mixed VA/DoD guidelines (e.g., PTSD, depression, chronic pain, "
            "opioid therapy), not narrowly infection-specific."
        ),
    },

    # ----------------------- Vocabularies / ontologies ---------------------
    "icd10cm": {
        "kind": "coding_vocab",
        "title": "ICD-10-CM Diagnosis Codes",
        "society": "CDC/NCHS",
        "domain": "multi",
        "condition": "diagnosis_codes",
        "summary": (
            "US clinical modification of ICD-10 used for billing and diagnosis "
            "coding; best for code lookup and mapping, not prose guidance."
        ),
    },
    "icd11": {
        "kind": "coding_vocab",
        "title": "ICD-11 Mortality and Morbidity Statistics (MMS)",
        "society": "WHO",
        "domain": "multi",
        "condition": "diagnosis_codes",
        "summary": (
            "WHO ICD-11 classification for diseases and health conditions; "
            "used for international coding and ontology mappings."
        ),
    },
    "snomed": {
        "kind": "ontology",
        "title": "SNOMED CT Concepts",
        "society": "SNOMED International",
        "domain": "multi",
        "condition": "clinical_concepts",
        "summary": (
            "Large clinical terminology for diseases, findings, and procedures; "
            "useful for concept-level reasoning and mapping."
        ),
    },
    "loinc": {
        "kind": "coding_vocab",
        "title": "LOINC Laboratory and Clinical Observations",
        "society": "Regenstrief",
        "domain": "laboratory",
        "condition": "lab_and_observation_codes",
        "summary": (
            "Standardized codes for lab tests and clinical measurements; "
            "good for lab code lookup, not narrative guidance."
        ),
    },
    "rxnorm": {
        "kind": "coding_vocab",
        "title": "RxNorm Medication Vocabulary",
        "society": "NLM",
        "domain": "pharmacology",
        "condition": "medications",
        "summary": (
            "Normalized names and identifiers for clinical drugs, ingredients, "
            "and dose forms; used for medication standardization."
        ),
    },
    "hpo": {
        "kind": "ontology",
        "title": "Human Phenotype Ontology (HPO)",
        "society": "HPO Consortium",
        "domain": "phenotypes",
        "condition": "phenotypic_abnormalities",
        "summary": (
            "Structured vocabulary of human phenotypic abnormalities used for "
            "rare disease and genetic diagnosis reasoning."
        ),
    },
    "orphanet": {
        "kind": "rare_disease_db",
        "title": "Orphanet Rare Disease Database",
        "society": "Orphanet",
        "domain": "rare_disease",
        "condition": "rare_diseases",
        "summary": (
            "Rare disease entities and associated metadata; complements HPO "
            "and gene-based sources for rare disease workup."
        ),
    },
    "panelapp": {
        "kind": "gene_panel_db",
        "title": "PanelApp Gene Panels",
        "society": "Genomics England et al.",
        "domain": "genetics",
        "condition": "gene_panels",
        "summary": (
            "Expert curated gene panels for specific clinical indications; "
            "best for linking phenotypes to genes/panels."
        ),
    },
    "chv": {
        "kind": "consumer_vocab",
        "title": "Consumer Health Vocabulary (CHV)",
        "society": "Various",
        "domain": "multi",
        "condition": "lay_terms",
        "summary": (
            "Mappings between layperson health terms and professional concepts; "
            "helps interpret patient-facing language."
        ),
    },
    "neurolex": {
        "kind": "ontology",
        "title": "NeuroLex Terms",
        "society": "NeuroLex",
        "domain": "neurology",
        "condition": "neuroanatomy_neuroscience_terms",
        "summary": (
            "Ontology terms for neuroanatomy and neuroscience concepts; helps "
            "with brain/nerve-related terminology."
        ),
    },

    # ----------------------------- Genetics / omics ------------------------
    "disgenet": {
        "kind": "genetics_db",
        "title": "DisGeNET Gene–Disease Associations (summary subset)",
        "society": "DisGeNET",
        "domain": "genetics",
        "condition": "gene_disease_associations",
        "summary": (
            "Aggregated gene–disease association knowledge; useful for mapping "
            "phenotypes/diseases to candidate genes."
        ),
    },
    "gwas": {
        "kind": "genetics_db",
        "title": "GWAS Catalog (summary subset)",
        "society": "GWAS Catalog",
        "domain": "genetics",
        "condition": "gwas_associations",
        "summary": (
            "Genome-wide association study hits linking variants to traits; "
            "supports polygenic/association-level reasoning."
        ),
    },

    # ----------------------------- EHR / notes -----------------------------
    "mimic3_dx": {
        "kind": "ehr_codes",
        "title": "MIMIC-III Diagnosis Codes",
        "society": "MIMIC",
        "domain": "critical_care",
        "condition": "icd_codes_icu",
        "summary": (
            "ICU diagnosis codes from MIMIC-III; mainly useful as a large "
            "clinical corpus and for code distribution patterns."
        ),
    },
    "mimic3_proc": {
        "kind": "ehr_codes",
        "title": "MIMIC-III Procedure Codes",
        "society": "MIMIC",
        "domain": "critical_care",
        "condition": "procedures_icu",
        "summary": (
            "Procedure codes from MIMIC-III; used as a procedural corpus and "
            "for code mapping."
        ),
    },
    "mimic3_labitems": {
        "kind": "ehr_lab_dict",
        "title": "MIMIC-III Lab Item Dictionary",
        "society": "MIMIC",
        "domain": "laboratory",
        "condition": "icu_lab_items",
        "summary": (
            "Dictionary of lab item names and units for MIMIC-III; "
            "useful for lab normalization and examples."
        ),
    },
    "mimic4_dx": {
        "kind": "ehr_codes",
        "title": "MIMIC-IV Diagnosis Codes",
        "society": "MIMIC",
        "domain": "inpatient_critical_care",
        "condition": "icd_codes_hospital",
        "summary": (
            "Hospital and ICU diagnosis codes from MIMIC-IV; large real-world "
            "coding corpus."
        ),
    },
    "mimic4_proc": {
        "kind": "ehr_codes",
        "title": "MIMIC-IV Procedure Codes",
        "society": "MIMIC",
        "domain": "inpatient_critical_care",
        "condition": "procedures_hospital",
        "summary": (
            "Procedure codes in the MIMIC-IV dataset; complements diagnosis and "
            "lab data."
        ),
    },
    "mimic4_labitems": {
        "kind": "ehr_lab_dict",
        "title": "MIMIC-IV Lab Item Dictionary",
        "society": "MIMIC",
        "domain": "laboratory",
        "condition": "hospital_lab_items",
        "summary": (
            "Dictionary of lab item names and units for MIMIC-IV; "
            "used for lab mapping."
        ),
    },
    "mimic4_note": {
        "kind": "ehr_notes",
        "title": "MIMIC-IV Clinical Notes",
        "society": "MIMIC",
        "domain": "critical_care_hospital",
        "condition": "free_text_notes",
        "summary": (
            "De-identified inpatient and ICU clinical notes; rich unstructured "
            "text for real-world documentation patterns."
        ),
    },

    # ----------------------------- NLP / benchmark -------------------------
    "n2c2_t3_ap": {
        "kind": "nlp_dataset",
        "title": "n2c2 2018 Track 3 Adverse Events / Problems (AP)",
        "society": "n2c2",
        "domain": "nlp_benchmark",
        "condition": "adverse_events_problems",
        "summary": (
            "Annotated clinical text for adverse drug events and problem mentions; "
            "used as a labeled benchmark corpus."
        ),
    },

    # ----------------------------- Other internals -------------------------
    "cdc_opioid": {
        "kind": "guideline",
        "title": "CDC Guideline for Prescribing Opioids for Chronic Pain",
        "society": "CDC",
        "domain": "pain_medicine_primary_care",
        "condition": "chronic_pain_opioid_prescribing",
        "summary": (
            "Recommendations on when and how to start, continue, and taper "
            "opioids for chronic non-cancer pain."
        ),
    },
    "ethos_model": {
        "kind": "llm_internal",
        "title": "Ethos Model Internal Corpus",
        "society": "2ndOpinionMD",
        "domain": "multi",
        "condition": "model_generated_content",
        "summary": (
            "Internal model-generated or curated content used to enforce system "
            "ethos; not a primary clinical guideline."
        ),
    },
    "pubmd": {
        "kind": "literature_subset",
        "title": "Curated PubMed-like Abstracts (subset)",
        "society": "Various",
        "domain": "multi",
        "condition": "literature_snippets",
        "summary": (
            "Small curated set of article abstracts/snippets; used as an "
            "evidence backstop when guidelines are sparse."
        ),
    },
}


@dataclass
class CodingRouterPlan:
    task_type: str
    selected_sources: List[str]
    reasoning: str


def _build_source_description_block(candidate_sources: List[str]) -> str:
    lines: List[str] = []
    for s in sorted(candidate_sources):
        meta = SOURCE_META.get(s)
        if not meta:
            lines.append(f"- {s}: (no structured metadata; generic internal corpus)")
            continue

        kind = meta.get("kind", "unknown")
        title = meta.get("title", "").strip()
        domain = meta.get("domain", "multi")
        condition = meta.get("condition", "multi")
        summary = meta.get("summary", "").strip()

        line = f"- {s}: [{kind}] {title}"
        if domain or condition:
            line += f" — domain={domain}, condition={condition}"
        if summary:
            line += f". {summary}"
        lines.append(line)

    return "\n".join(lines)


async def route_coding_sources(
    q: str,
    code_terms: List[str],
    candidate_sources: List[str],
    valyu_context: Optional[List[Dict[str, Any]]] = None,
) -> CodingRouterPlan:
    # Build a compact description of candidate sources
    src_lines = [f"- {s}" for s in sorted(candidate_sources)]
    source_desc_block = _build_source_description_block(candidate_sources)

    # Optional Valyu summary for the router prompt
    valyu_lines: List[str] = []
    if valyu_context:
        valyu_lines.append("External Valyu evidence snippets:")
        for i, r in enumerate(valyu_context[:8], start=1):
            title = (r.get("title") or "").strip()
            snippet = (r.get("text") or r.get("snippet") or "").strip()
            line = f"[VALYU-{i}] {title}" if title else f"[VALYU-{i}]"
            if snippet:
                line += f" — {snippet[:240]}"
            valyu_lines.append(line)

        valyu_lines.append(
            "Use these Valyu snippets only as a signal of which guideline "
            "or internal sources are likely relevant. Do NOT hallucinate "
            "new source names."
        )

    code_term_lines: List[str] = []
    if code_terms:
        code_term_lines.append("Extracted coding-related terms:")
        for t in code_terms[:24]:
            code_term_lines.append(f"- {t}")

    system_content = (
        "You are a routing controller for 2ndOpinionMD's medical RAG system.\n"
        "Your job is to choose which internal sources to query for this question.\n\n"
        "You MUST return STRICT JSON with keys:\n"
        "  - task_type: string (e.g., 'guideline_qa', 'coding', 'mixed')\n"
        "  - selected_sources: list of source names from the candidate list\n"
        "  - reasoning: short explanation of your choices\n\n"
        "Rules:\n"
        "- Always choose at least one source, unless there is a clear error.\n"
        "- Prefer focused subsets over 'everything'.\n"
        "- If the question is clearly about codes only, prioritize coding sources.\n"
        "- If the question is guideline-heavy (treatment algorithms, stepwise therapy,\n"
        "  risk stratification), prioritize guideline sources.\n"
        "- Use the source descriptions below to match the clinical question to the\n"
        "  most relevant guideline(s) or corpora.\n"
        "- If Valyu evidence is present, use it to bias towards the most relevant\n"
        "  guideline or internal corpora, but do NOT invent sources.\n"
    )

    user_chunks: List[str] = [
        "Clinical question:",
        q.strip(),
        "",
        "Candidate internal sources (raw IDs):",
        *src_lines,
        "",
        "Source descriptions:",
        source_desc_block,
    ]
    if code_term_lines:
        user_chunks.append("")
        user_chunks.extend(code_term_lines)
    if valyu_lines:
        user_chunks.append("")
        user_chunks.extend(valyu_lines)

    user_chunks.append("")
    user_chunks.append(
        "Return ONLY JSON of the form:\n"
        "{\n"
        '  \"task_type\": \"...\",\n'
        '  \"selected_sources\": [\"source1\", \"source2\", ...],\n'
        '  \"reasoning\": \"...\"\n'
        "}\n"
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": "\n".join(user_chunks)},
    ]

    try:
        completion = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        return CodingRouterPlan(
            task_type="fallback_all_sources",
            selected_sources=list(candidate_sources),
            reasoning=f"router_failed: {e}",
        )

    content = completion.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except Exception as e:
        return CodingRouterPlan(
            task_type="fallback_all_sources",
            selected_sources=list(candidate_sources),
            reasoning=f"router_json_parse_failed: {e}",
        )

    task_type = str(data.get("task_type") or "unknown")
    selected = data.get("selected_sources") or []
    reasoning = str(data.get("reasoning") or "").strip()

    cand_set = set(candidate_sources)
    cleaned: List[str] = []
    if isinstance(selected, list):
        for s in selected:
            if not isinstance(s, str):
                continue
            s_clean = s.strip()
            if s_clean and s_clean in cand_set and s_clean not in cleaned:
                cleaned.append(s_clean)

    if not cleaned:
        cleaned = list(candidate_sources)

    return CodingRouterPlan(
        task_type=task_type,
        selected_sources=cleaned,
        reasoning=reasoning,
    )