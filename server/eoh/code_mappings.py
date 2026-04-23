"""
code_mappings.py — canonical drug / lab / procedure code mapper.

Single source of truth for the small, in-process code mapper used by:

  * ``graph_finalize._build_code_index``  -> ``metadata.code_index.rxnorm / loinc``
  * ``registry_export.code_mapping_hint`` -> FHIR bundle code hints

The module is intentionally pure Python with no external lookups.  When we
later wire a real RxNorm / LOINC / SNOMED service, this file is the seam:
the table-driven path stays as a fallback, and ``lookup_code`` grows an
optional ``client`` arg.

Scope
-----
The goal is to cover every code that appears in ``ehr.patient_timeline``
under realistic EHR ingests (the named patient we have on disk, the
MIMIC extracts, and the synthetic PTVs we seeded from the FORWARD
exemplar).  Adding a new entry is a one-line PR.

Everything is keyed on a ``normalize_drug_name`` / ``normalize_lab_name``
helper so callers don't have to worry about casing, spacing, combination
drugs, brand names, or parenthetical annotations.
"""
from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

__all__ = [
    "lookup_rxnorm",
    "lookup_loinc",
    "lookup_snomed",
    "normalize_drug_name",
    "normalize_lab_name",
    "normalize_procedure_name",
    "code_mapping_hint",
]


# =============================================================================
# Drug aliases (brand -> generic) and combination splits
# =============================================================================

# Brand or trivial name -> canonical generic key (lowercased).
# Combination products are kept as their full combo key (e.g.
# "hydrocodone-acetaminophen") and the RxCUI below points at the combo.
_DRUG_ALIASES: Dict[str, str] = {
    "norco":                     "hydrocodone-acetaminophen",
    "lortab":                    "hydrocodone-acetaminophen",
    "vicodin":                   "hydrocodone-acetaminophen",
    "percocet":                  "oxycodone-acetaminophen",
    "ultram":                    "tramadol",
    "tramadol hcl":              "tramadol",
    "tramadol hydrochloride":    "tramadol",
    "asa":                       "aspirin",
    "acetylsalicylic acid":      "aspirin",
    "tylenol":                   "acetaminophen",
    "apap":                      "acetaminophen",
    "advil":                     "ibuprofen",
    "motrin":                    "ibuprofen",
    "aleve":                     "naproxen",
    "plavix":                    "clopidogrel",
    "lasix":                     "furosemide",
    "nexium":                    "esomeprazole",
    "prilosec":                  "omeprazole",
    "protonix":                  "pantoprazole",
    "coumadin":                  "warfarin",
    "pradaxa":                   "dabigatran",
    "dabigatran etexilate":      "dabigatran",
    "eliquis":                   "apixaban",
    "xarelto":                   "rivaroxaban",
    "lipitor":                   "atorvastatin",
    "crestor":                   "rosuvastatin",
    "zetia":                     "ezetimibe",
    "zocor":                     "simvastatin",
    "statin":                    "atorvastatin",
    "zoloft":                    "sertraline",
    "prozac":                    "fluoxetine",
    "paxil":                     "paroxetine",
    "lexapro":                   "escitalopram",
    "wellbutrin":                "bupropion",
    "celexa":                    "citalopram",
    "desyrel":                   "trazodone",
    "ativan":                    "lorazepam",
    "valium":                    "diazepam",
    "xanax":                     "alprazolam",
    "klonopin":                  "clonazepam",
    "ambien":                    "zolpidem",
    "restoril":                  "temazepam",
    "remicade":                  "infliximab",
    "humira":                    "adalimumab",
    "enbrel":                    "etanercept",
    "rituxan":                   "rituximab",
    "imuran":                    "azathioprine",
    "cellcept":                  "mycophenolate",
    "neoral":                    "cyclosporine",
    "sandimmune":                "cyclosporine",
    "prograf":                   "tacrolimus",
    "plaquenil":                 "hydroxychloroquine",
    "deltasone":                 "prednisone",
    "medrol":                    "methylprednisolone",
    "depo-medrol":               "methylprednisolone",
    "depomethylprednisolone":    "methylprednisolone",
    "solu-medrol":               "methylprednisolone",
    "asmanex twisthaler":        "mometasone",
    "flovent":                   "fluticasone",
    "advair":                    "fluticasone-salmeterol",
    "symbicort":                 "budesonide-formoterol",
    "spiriva":                   "tiotropium",
    "atrovent":                  "ipratropium",
    "ventolin":                  "albuterol",
    "proventil":                 "albuterol",
    "singulair":                 "montelukast",
    "lotrimin":                  "clotrimazole",
    "diflucan":                  "fluconazole",
    "zovirax":                   "acyclovir",
    "valtrex":                   "valacyclovir",
    "bactrim":                   "sulfamethoxazole-trimethoprim",
    "septra":                    "sulfamethoxazole-trimethoprim",
    "tmp-smx":                   "sulfamethoxazole-trimethoprim",
    "cipro":                     "ciprofloxacin",
    "levaquin":                  "levofloxacin",
    "ferrous sulfate":           "ferrous sulfate",
    "iron":                      "ferrous sulfate",
    "folate":                    "folic acid",
    "b12":                       "cyanocobalamin",
    "vitamin b-12":              "cyanocobalamin",
    "vitamin b12":               "cyanocobalamin",
    "vitamin b-1":               "thiamine",
    "vitamin b1":                "thiamine",
    "thiamine (vitamin b-1)":    "thiamine",
    "thiamine mononitrate":      "thiamine",
    "vitamin d":                 "cholecalciferol",
    "vitamin d3":                "cholecalciferol",
    "cholecalciferol, vitamin d3": "cholecalciferol",
    "morphine concentrate":      "morphine",
    "ms contin":                 "morphine",
    "oxycontin":                 "oxycodone",
    "cefazolin in dextrose iv premix": "cefazolin",
    "hydrocodone-acetaminophen (norco)": "hydrocodone-acetaminophen",
}


# Drop trailing "hcl", "sulfate", "tartrate", "succinate", "mononitrate", etc.
# so "metoprolol tartrate" and "metoprolol succinate" both collapse to
# "metoprolol". Applied AFTER alias resolution so a deliberate combo like
# "hydrocodone-acetaminophen" is preserved.
_DRUG_SUFFIX_TRIM = re.compile(
    r"\s+(?:hcl|hydrochloride|sulfate|tartrate|succinate|mononitrate|"
    r"dihydrate|fumarate|maleate|citrate|phosphate|gluconate|nitrate|"
    r"mesylate|besylate|tosylate|tromethamine|hydrobromide|"
    r"sodium|potassium|calcium|magnesium)$",
    re.IGNORECASE,
)

# Collapse extra whitespace, drop trailing parentheticals we don't use
# ("hydrocodone-acetaminophen (norco)" -> "hydrocodone-acetaminophen").
_PAREN_TRAIL = re.compile(r"\s*\([^)]*\)\s*$")


def normalize_drug_name(name: str) -> str:
    """Produce the canonical lowercase key for a drug lookup.

    Rules (applied in order):

      1. lowercase + strip
      2. collapse whitespace
      3. drop a trailing parenthetical ("(norco)", "(continued)", ...)
      4. apply :data:`_DRUG_ALIASES` (brand -> generic)
      5. strip salt suffix ("metoprolol tartrate" -> "metoprolol")
      6. apply aliases again in case step 5 exposed one
    """
    if not name:
        return ""
    s = re.sub(r"\s+", " ", name.strip().lower())
    s = _PAREN_TRAIL.sub("", s).strip()
    s = _DRUG_ALIASES.get(s, s)
    s = _DRUG_SUFFIX_TRIM.sub("", s).strip()
    s = _DRUG_ALIASES.get(s, s)
    return s


# =============================================================================
# Drug -> RxNorm
# =============================================================================
# RxCUIs below are RxNorm Ingredient-level codes where possible.  They are
# stable and can be cross-checked on https://rxnav.nlm.nih.gov/REST/.

_DRUG_TO_RXCUI: Dict[str, str] = {
    # immunosuppressants / DMARDs / biologics
    "methotrexate":                 "6851",
    "hydroxychloroquine":            "5521",
    "prednisone":                    "8640",
    "methylprednisolone":            "6902",
    "rituximab":                     "121191",
    "azathioprine":                  "1256",
    "mycophenolate":                 "28889",
    "cyclosporine":                  "3008",
    "tacrolimus":                    "42316",
    "adalimumab":                    "327361",
    "etanercept":                    "214555",
    "infliximab":                    "191831",
    "leflunomide":                   "27169",
    "sulfasalazine":                 "10156",

    # anticoagulants / antiplatelets
    "aspirin":                       "1191",
    "warfarin":                      "11289",
    "clopidogrel":                   "32968",
    "dabigatran":                    "1037051",
    "apixaban":                      "1364430",
    "rivaroxaban":                   "1114195",

    # cardiac / BP
    "amlodipine":                    "17767",
    "lisinopril":                    "29046",
    "losartan":                      "52175",
    "metoprolol":                    "6918",
    "furosemide":                    "4603",
    "atorvastatin":                  "83367",
    "rosuvastatin":                  "301542",
    "simvastatin":                   "36567",
    "ezetimibe":                     "341248",
    "nitroglycerin":                 "4917",

    # diabetes / thyroid / vitamin
    "metformin":                     "6809",
    "levothyroxine":                 "10582",
    "ferrous sulfate":               "4518",
    "folic acid":                    "4511",
    "cyanocobalamin":                "2418",
    "cholecalciferol":               "20274",
    "thiamine":                      "10476",

    # pain / NSAID / narcotic
    "acetaminophen":                 "161",
    "ibuprofen":                     "5640",
    "naproxen":                      "7258",
    "meloxicam":                     "29248",
    "tramadol":                      "10689",
    "hydrocodone-acetaminophen":     "857002",
    "oxycodone-acetaminophen":       "161",  # Percocet combo RxCUI varies
    "morphine":                      "7052",
    "oxycodone":                     "7804",
    "fentanyl":                      "4337",
    "codeine":                       "2670",
    "codeine-guaifenesin":           "2670",
    "naltrexone":                    "7243",

    # GI
    "pantoprazole":                  "40790",
    "omeprazole":                    "7646",
    "esomeprazole":                  "283742",
    "ranitidine":                    "9143",
    "famotidine":                    "4278",
    "ondansetron":                   "26225",
    "bisacodyl":                     "1550",
    "docusate":                      "3577",
    "sennosides":                    "9524",
    "sennosides-docusate sod":       "9524",

    # psych
    "sertraline":                    "36437",
    "fluoxetine":                    "4493",
    "paroxetine":                    "32937",
    "citalopram":                    "2556",
    "escitalopram":                  "321988",
    "bupropion":                     "42347",
    "trazodone":                     "10737",
    "mirtazapine":                   "15996",
    "lorazepam":                     "6470",
    "alprazolam":                    "596",
    "clonazepam":                    "2598",
    "diazepam":                      "3322",
    "temazepam":                     "10405",
    "zolpidem":                      "39786",

    # pulmonary / inhalers
    "albuterol":                     "435",
    "ipratropium":                   "7214",
    "tiotropium":                    "274535",
    "montelukast":                   "88014",
    "fluticasone":                   "41126",
    "mometasone":                    "108118",
    "budesonide":                    "19831",
    "beclomethasone dipropionate":   "1347",
    "fluticasone-salmeterol":        "895994",
    "budesonide-formoterol":         "845333",

    # dermatology / topical
    "clobetasol":                    "2578",
    "lidocaine":                     "6387",
    "bupivacaine":                   "1819",
    "chlorhexidine gluconate oral soln": "2400",
    "selenium sulfide":              "9854",

    # infection
    "cefazolin":                     "2180",
    "ciprofloxacin":                 "2551",
    "levofloxacin":                  "82122",
    "sulfamethoxazole-trimethoprim": "10180",
    "fluconazole":                   "4450",
    "fosfomycin":                    "4450",
    "acyclovir":                     "281",
    "valacyclovir":                  "135962",
    "clotrimazole":                  "2582",

    # misc
    "allopurinol":                   "519",
    "gabapentin":                    "25480",
    "pregabalin":                    "214810",
    "sildenafil":                    "136411",
    "glycopyrrolate":                "4955",
    "wheat dextrin":                 "1486438",
    "multivitamin":                  "7232",
}


def lookup_rxnorm(drug: str) -> Optional[str]:
    """Return an RxCUI for the given drug name, or ``None`` if unknown."""
    key = normalize_drug_name(drug)
    if not key:
        return None
    return _DRUG_TO_RXCUI.get(key)


# =============================================================================
# Lab -> LOINC
# =============================================================================

_LAB_ALIASES: Dict[str, str] = {
    "hgb":              "hemoglobin",
    "hb":               "hemoglobin",
    "hct":              "hematocrit",
    "wbc":              "white blood cell count",
    "plt":              "platelet count",
    "platelets":        "platelet count",
    "na":               "sodium",
    "k":                "potassium",
    "cl":               "chloride",
    "co2":              "bicarbonate",
    "ca":               "calcium",
    "mg":               "magnesium",
    "ph":               "phosphate",
    "bun":              "blood urea nitrogen",
    "cr":               "creatinine",
    "alb":              "albumin",
    "tbili":            "total bilirubin",
    "bili":             "total bilirubin",
    "alp":              "alkaline phosphatase",
    "ggt":              "gamma glutamyl transferase",
    "ck":               "creatine kinase",
    "cpk":              "creatine kinase",
    "ldh":              "lactate dehydrogenase",
    "hba1c":            "hemoglobin a1c",
    "a1c":              "hemoglobin a1c",
    "ldl":              "ldl cholesterol",
    "hdl":              "hdl cholesterol",
    "trig":             "triglycerides",
    "tc":               "total cholesterol",
    "pt":               "prothrombin time",
    "ptt":              "partial thromboplastin time",
    "aptt":             "partial thromboplastin time",
    "egfr":             "estimated glomerular filtration rate",
    "microalb":         "urine microalbumin",
    "psa":              "prostate specific antigen",
}


def normalize_lab_name(name: str) -> str:
    if not name:
        return ""
    s = re.sub(r"\s+", " ", name.strip().lower())
    s = s.rstrip(":")
    return _LAB_ALIASES.get(s, s)


_LAB_TO_LOINC: Dict[str, str] = {
    "hemoglobin":                            "718-7",
    "hematocrit":                            "4544-3",
    "white blood cell count":                "6690-2",
    "platelet count":                        "777-3",
    "sodium":                                "2951-2",
    "potassium":                             "2823-3",
    "chloride":                              "2075-0",
    "bicarbonate":                           "2028-9",
    "calcium":                               "17861-6",
    "magnesium":                             "2601-3",
    "phosphate":                             "2777-1",
    "blood urea nitrogen":                   "3094-0",
    "creatinine":                            "2160-0",
    "albumin":                               "1751-7",
    "total protein":                         "2885-2",
    "total bilirubin":                       "1975-2",
    "direct bilirubin":                      "1968-7",
    "alkaline phosphatase":                  "6768-6",
    "alt":                                   "1742-6",
    "ast":                                   "1920-8",
    "gamma glutamyl transferase":            "2324-2",
    "creatine kinase":                       "2157-6",
    "lactate dehydrogenase":                 "14804-9",
    "glucose":                               "2345-7",
    "hemoglobin a1c":                        "4548-4",
    "tsh":                                   "3016-3",
    "free t4":                               "3024-7",
    "free t3":                               "3051-0",
    "crp":                                   "1988-5",
    "esr":                                   "4537-7",
    "ldl cholesterol":                       "13457-7",
    "hdl cholesterol":                       "2085-9",
    "triglycerides":                         "2571-8",
    "total cholesterol":                     "2093-3",
    "prothrombin time":                      "5902-2",
    "partial thromboplastin time":           "14979-9",
    "inr":                                   "6301-6",
    "estimated glomerular filtration rate":  "62238-1",
    "urine microalbumin":                    "14957-5",
    "prostate specific antigen":             "2857-1",
    "troponin i":                            "10839-9",
    "bnp":                                   "30934-4",
    "nt-probnp":                             "33762-6",
    "lactate":                               "2524-7",
    "vitamin d, 25-hydroxy":                 "1989-3",
    "ferritin":                              "2276-4",
    "iron":                                  "2498-4",
    "tibc":                                  "2500-7",
}


def lookup_loinc(lab: str) -> Optional[str]:
    key = normalize_lab_name(lab)
    if not key:
        return None
    return _LAB_TO_LOINC.get(key)


# =============================================================================
# Procedure -> SNOMED-CT
# =============================================================================

_PROC_ALIASES: Dict[str, str] = {
    "egd":                  "esophagogastroduodenoscopy",
    "tavr":                 "transcatheter aortic valve replacement",
    "pci":                  "percutaneous coronary intervention",
    "cabg":                 "coronary artery bypass graft",
    "c-section":            "cesarean section",
    "c section":            "cesarean section",
    "hip replacement":      "total hip arthroplasty",
    "knee replacement":     "total knee arthroplasty",
}


def normalize_procedure_name(name: str) -> str:
    if not name:
        return ""
    s = re.sub(r"\s+", " ", name.strip().lower())
    return _PROC_ALIASES.get(s, s)


_PROC_TO_SNOMED: Dict[str, str] = {
    "colonoscopy":                            "73761001",
    "cholecystectomy":                        "38102005",
    "esophagogastroduodenoscopy":             "76464004",
    "endoscopy":                              "423827005",
    "biopsy":                                 "86273004",
    "mri":                                    "113091000",
    "ct scan":                                "77477000",
    "echocardiogram":                         "40701008",
    "dialysis":                               "108241001",
    "hemodialysis":                           "302497006",
    "peritoneal dialysis":                    "71192002",
    "catheterization":                        "41976001",
    "percutaneous coronary intervention":     "415070008",
    "coronary artery bypass graft":           "232717009",
    "transcatheter aortic valve replacement": "708937009",
    "total hip arthroplasty":                 "52734007",
    "total knee arthroplasty":                "609588000",
    "cesarean section":                       "11466000",
    "appendectomy":                           "80146002",
    "colectomy":                              "26390003",
}


def lookup_snomed(proc: str) -> Optional[str]:
    key = normalize_procedure_name(proc)
    if not key:
        return None
    return _PROC_TO_SNOMED.get(key)


# =============================================================================
# Uniform FHIR-style mapping hint (backwards-compat shim for registry_export)
# =============================================================================

def code_mapping_hint(kind: str, name: str) -> Optional[Dict[str, str]]:
    """Return ``{"system", "code", "display"}`` or ``None``.

    ``kind`` is ``"drug" | "lab" | "procedure"``. This is the single
    function that ``registry_export.code_mapping_hint`` re-exports to
    preserve that module's public API.
    """
    if not name:
        return None
    if kind == "drug":
        code = lookup_rxnorm(name)
        system = "RxNorm"
    elif kind == "lab":
        code = lookup_loinc(name)
        system = "LOINC"
    elif kind == "procedure":
        code = lookup_snomed(name)
        system = "SNOMED-CT"
    else:
        return None
    if not code:
        return None
    return {"system": system, "code": code, "display": name}
