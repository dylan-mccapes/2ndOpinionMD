# server/eoh/eoh_plans.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


@dataclass
class EoHGuidelineBundle:
    """
    Canonical guideline bundle for a given disease cluster.

    This is intentionally simple for v1:
    - keyed primarily by disease_cluster (RA, HF, etc.)
    - question_type is optional metadata (we may specialize later)
    """
    id: str
    disease_cluster: str
    description: str
    sources: List[str]


# ---------------------------------------------------------------------------
# Disease cluster heuristics
# ---------------------------------------------------------------------------

def infer_disease_cluster(question: str) -> str:
    """
    Very lightweight heuristic to map a free-text question onto a disease cluster.

    This is deliberately conservative: if we don't find a clear signal,
    we return 'general' and fall back to a wide bundle (or all sources).
    """
    q = (question or "").lower()

    # Rheumatoid arthritis / RA-ILD
    ra_markers = [
        "rheumatoid arthritis",
        "seropositive ra",
        "seronegative ra",
        "ra-associated",
        "ra ild",
        "ra-ild",
        "anti-ccp",
        "ccp positive",
        "rheumatoid factor",
        "methotrexate",
        "leflunomide",
        "tnf inhibitor",
        "adalimumab",
        "etanercept",
        "infliximab",
    ]
    if any(term in q for term in ra_markers):
        return "ra"

    # SLE / lupus
    sle_markers = [
        "lupus",
        "sle",
        "systemic lupus",
        "anti-dsdna",
        "dsdna",
        "complement",
        "c3",
        "c4",
        "belimumab",
    ]
    if any(term in q for term in sle_markers):
        return "sle"

    # Psoriatic arthritis / psoriasis
    psa_markers = [
        "psoriatic arthritis",
        "psa",
        "psoriasis",
        "enthesitis",
        "dactylitis",
        "il-17",
        "il-23",
    ]
    if any(term in q for term in psa_markers):
        return "psa"

    # IBD (Crohn's / UC)
    ibd_markers = [
        "crohn",
        "ulcerative colitis",
        "ibd",
        "ileitis",
        "proctitis",
        "anti-tnf for ibd",
    ]
    if any(term in q for term in ibd_markers):
        return "ibd"

    # Heart failure / cardiometabolic (HF, SGLT2, GLP-1)
    hf_markers = [
        "heart failure",
        "hfrref",
        "hfr ef",
        "hfpef",
        "sglt2",
        "glp-1",
        "glp1",
        "sacubitril",
        "valsartan",
    ]
    if any(term in q for term in hf_markers):
        return "hf"

    # Kidney disease (AKI / CKD)
    kidney_markers = [
        "aki",
        "acute kidney injury",
        "ckd",
        "chronic kidney disease",
        "egfr",
        "proteinuria",
        "albuminuria",
        "kdigo",
    ]
    if any(term in q for term in kidney_markers):
        return "kidney"

    # Infection / sepsis / IE
    infection_markers = [
        "infective endocarditis",
        "endocarditis",
        "bacteremia",
        "sepsis",
        "septic shock",
        "pneumonia",
        "meningitis",
        "idsa",
    ]
    if any(term in q for term in infection_markers):
        return "infection"

    return "general"


# ---------------------------------------------------------------------------
# Canonical guideline bundles
#   NOTE: source names here are *aspirational*. We always intersect with
#         the actually-available sources, so this is safe even if some
#         MKG sources aren't loaded yet.
# ---------------------------------------------------------------------------

BUNDLES: Dict[str, EoHGuidelineBundle] = {
    "ra": EoHGuidelineBundle(
        id="eoh_bundle_ra_v1",
        disease_cluster="ra",
        description="RA / RA-ILD questions (flare, stability, pregnancy, ILD).",
        sources=[
            # RA core
            "acr_ra_2021",
            "eular_ra_2022",
            # RA-ILD / connective tissue ILD
            "acr_ild_2023",
            "ers_ild_2023",
        ],
    ),
    "sle": EoHGuidelineBundle(
        id="eoh_bundle_sle_v1",
        disease_cluster="sle",
        description="SLE / lupus flares and organ involvement.",
        sources=[
            "eular_sle_2019",
            "acr_sle_2019",
        ],
    ),
    "psa": EoHGuidelineBundle(
        id="eoh_bundle_psa_v1",
        disease_cluster="psa",
        description="Psoriatic arthritis / psoriasis activity and DMARD choices.",
        sources=[
            "eular_psa_2020",
            "grappa_psa_2021",
        ],
    ),
    "ibd": EoHGuidelineBundle(
        id="eoh_bundle_ibd_v1",
        disease_cluster="ibd",
        description="Crohn's and ulcerative colitis (IBD) flare questions.",
        sources=[
            "aga_crohns_2021",
            "aga_uc_2020",
            "ecco_ibd_2019",
        ],
    ),
    "hf": EoHGuidelineBundle(
        id="eoh_bundle_hf_v1",
        disease_cluster="hf",
        description="Heart failure / cardiometabolic questions (GLP-1, SGLT2, RAAS).",
        sources=[
            "acc_aha_hf_2022",
            "nice_hf_2018",
            "esc_hf_2021",
        ],
    ),
    "kidney": EoHGuidelineBundle(
        id="eoh_bundle_kidney_v1",
        disease_cluster="kidney",
        description="KDIGO AKI / CKD / BP in CKD bundle.",
        sources=[
            "kdigo_aki_2012",
            "kdigo_bp_ckd_2021",
            "kdigo_ckd_2012",
        ],
    ),
    "infection": EoHGuidelineBundle(
        id="eoh_bundle_infection_v1",
        disease_cluster="infection",
        description="Serious infection / sepsis / infective endocarditis bundle.",
        sources=[
            "idsa_ie_2015",
            "idsa_pneumonia_2019",
            "surviving_sepsis_2021",
        ],
    ),
    "general": EoHGuidelineBundle(
        id="eoh_bundle_general_v1",
        disease_cluster="general",
        description="General internal medicine / multimorbidity bundle.",
        sources=[
            # Intentionally light; we fall back to all available if this is too narrow.
            "nice_multimorbidity_2016",
        ],
    ),
}


def _pick_bundle_for_cluster(cluster: str) -> EoHGuidelineBundle:
    if cluster in BUNDLES:
        return BUNDLES[cluster]
    return BUNDLES["general"]


def select_guideline_bundle_for_eoh(
    *,
    question: str,
    question_type: str,
    available_sources: List[str],
    ethos_source_name: Optional[str] = None,
) -> Tuple[EoHGuidelineBundle, List[str]]:
    """
    Given a question, question type, and the MKG sources that actually exist,
    pick a canonical EoH guideline bundle and return the *effective* sources.

    - We infer a disease_cluster from the text.
    - We choose a bundle for that cluster.
    - We intersect the bundle's sources with available_sources.
    - We ALWAYS keep ethos_source_name (if provided and present).
    - If intersection is empty, we fall back to all available_sources.
    """
    cluster = infer_disease_cluster(question)
    bundle = _pick_bundle_for_cluster(cluster)

    # Keep only sources that actually exist in this MKG for this query
    available_set = set(available_sources or [])
    bundle_set = set(bundle.sources)

    intersection = list(bundle_set & available_set)

    # Always keep Ethos/EoH source if provided
    if ethos_source_name and ethos_source_name in available_set:
        if ethos_source_name not in intersection:
            intersection.append(ethos_source_name)

    # If intersection is empty, fall back to all available sources
    if not intersection:
        # At least still keep Ethos if present
        if ethos_source_name and ethos_source_name in available_set:
            return bundle, [ethos_source_name]
        return bundle, available_sources

    # Sort for deterministic output
    intersection = sorted(intersection)

    return bundle, intersection