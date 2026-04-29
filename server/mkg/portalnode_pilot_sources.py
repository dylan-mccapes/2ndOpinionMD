"""
PortalNode / FORWARD pilot ``rag_corpus.source`` keys and LLM-facing blurbs.

The authoritative allowlist is ``scripts/portalnode_rag_slice_sources.txt`` (one key per line).
``PORTALNODE_PILOT_SOURCE_DESCRIPTIONS`` must contain exactly those keys; import asserts sync.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, FrozenSet, Iterable, Mapping, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_LIST = _REPO_ROOT / "scripts" / "portalnode_rag_slice_sources.txt"


def pilot_rag_source_keys(*, list_path: Optional[Path] = None) -> Tuple[str, ...]:
    """Return ordered source keys from the portal slice list (comments and blanks skipped)."""
    path = list_path or _DEFAULT_LIST
    if not path.is_file():
        raise FileNotFoundError(f"portal slice list not found: {path}")
    keys: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        keys.append(line.lower())
    return tuple(keys)


# One-line context for Ollama / operators: what each ``source`` value means in rag_corpus.
PORTALNODE_PILOT_SOURCE_DESCRIPTIONS: Dict[str, str] = {
    # Ontologies & lexicons
    "rxnorm": "NLM RxNorm drug and ingredient concepts (RxCUI, names, TTYs).",
    "loinc": "LOINC laboratory and clinical observation codes with long names.",
    "hpo": "Human Phenotype Ontology terms (phenotypes, disease manifestations).",
    "snomed": "SNOMED CT clinical concepts (disorders, findings, procedures).",
    "icd10cm": "ICD-10-CM diagnosis codes and official long titles (US clinical modification).",
    "icd11": "WHO ICD-11 foundation mortality and morbidity content mirrored for search.",
    "orphanet": "Orphanet rare disease names, synonyms, and classification text.",
    "chv": "Consumer Health Vocabulary — lay-language terms linked to clinical concepts (UMLS CHV).",
    # VA + multisociety guidelines
    "va_guidelines": "VA/DoD clinical practice guideline sections ingested as rag_corpus chunks.",
    "acc_aha_valvular_2020": "2020 ACC/AHA guideline on valvular heart disease (chunked text).",
    "ada_dm_2024": "American Diabetes Association Standards of Care (diabetes mellitus, 2024 vintage).",
    "kdigo_ckd_2021": "KDIGO 2021 clinical practice guideline for chronic kidney disease (CKD).",
    "kdigo_ckd_2024": "KDIGO 2024 CKD evaluation and management guideline excerpts.",
    "kdigo_gn_ln_2021": "KDIGO 2021 guideline for glomerular diseases including lupus nephritis.",
    "kdigo_anemia_ckd_2023": "KDIGO 2023 clinical practice guideline for anemia in CKD.",
    "gold_copd_2023": "GOLD 2023 Global Strategy for Diagnosis, Management, and Prevention of COPD.",
    "gold_copd_2024": "GOLD 2024 COPD strategy document excerpts.",
    "gina_asthma_2023": "GINA 2023 Global Strategy for Asthma Management and Prevention.",
    "cdc_opioid": "CDC opioid prescribing guideline narrative sections (structured plain text).",
    # ACR / EULAR / companion rheum
    "acr_eular": "Joint ACR/EULAR classification or criteria publications (combined tag).",
    "acr_ild_2023": "ACR guidance on idiopathic inflammatory myopathies with ILD (2023).",
    "acr_ra_2021": "ACR guideline or guidance on rheumatoid arthritis management (2021).",
    "acr_npf_psa_2018": "ACR/NPF joint guideline on psoriasis and psoriatic arthritis (2018).",
    "acr_vf_anca_2021": "ACR/VF guideline on ANCA-associated vasculitis (2021).",
    "acr_reproductive_health_2020": "ACR reproductive health guidance for rheumatic disease (2020).",
    "eular_acr_sle_2019": "EULAR/ACR classification criteria or lupus management collaboration (2019).",
    "eular_ra_2022": "EULAR recommendations for rheumatoid arthritis management (2022).",
    "eular_psa_2020": "EULAR recommendations for psoriatic arthritis pharmacologic therapy (2020).",
    "eular_sle_nephritis_2025": "EULAR recommendations on management of lupus nephritis (2025).",
    "eular_anca_2022": "EULAR recommendations for ANCA-associated vasculitis (2022).",
    "eular_lvv_2018": "EULAR recommendations for large-vessel vasculitis (2018).",
    "eular_axspa_2022": "EULAR recommendations for axial spondyloarthritis (2022).",
    "asas_eular_axspa_2022": "ASAS–EULAR recommendations for axial spondyloarthritis (2022).",
    "diagrules": "Curated diagnostic-rule narrative cards used as RAG chunks.",
    # Ethos canon
    "eoh_canon_v6": "Ethos of Health canon v6 narrative chunks (foundational clinical ethos text).",
    "eoh_2025": "Ethos of Health 2025 corpus excerpts in rag_corpus.",
    "eoh_gold_2025": "Ethos of Health × GOLD COPD 2025 cross-reference or summary chunks.",
    "ethos_model": "Short Ethos-of-Health model or meta documents (small row count).",
}


def _assert_keys_match_file() -> None:
    file_keys = set(pilot_rag_source_keys())
    dict_keys = set(PORTALNODE_PILOT_SOURCE_DESCRIPTIONS)
    if file_keys != dict_keys:
        only_file = sorted(file_keys - dict_keys)
        only_dict = sorted(dict_keys - file_keys)
        msg = ["portalnode_rag_slice_sources.txt and PORTALNODE_PILOT_SOURCE_DESCRIPTIONS are out of sync."]
        if only_file:
            msg.append(f"  In txt but missing descriptions: {only_file}")
        if only_dict:
            msg.append(f"  Described but not in txt: {only_dict}")
        raise RuntimeError("\n".join(msg))


_assert_keys_match_file()


def pilot_source_descriptions(
    *,
    sources: Optional[Iterable[str]] = None,
    list_path: Optional[Path] = None,
) -> Dict[str, str]:
    """
    Return ``source`` → description for pilot slice keys.

    If ``sources`` is given, only those keys are returned (unknown keys skipped).
    """
    base: Mapping[str, str] = PORTALNODE_PILOT_SOURCE_DESCRIPTIONS
    if sources is None:
        order = pilot_rag_source_keys(list_path=list_path)
        return {k: base[k] for k in order}
    out: Dict[str, str] = {}
    for s in sources:
        k = (s or "").strip().lower()
        if k in base:
            out[k] = base[k]
    return out


def pilot_source_key_set(*, list_path: Optional[Path] = None) -> FrozenSet[str]:
    return frozenset(pilot_rag_source_keys(list_path=list_path))


def format_modelfile_rag_sources_block() -> str:
    """
    Plain-text block for Ollama SYSTEM prompts / Modelfile maintenance.

    Keeps wording in sync with ``PORTALNODE_PILOT_SOURCE_DESCRIPTIONS`` (single source of truth).
    Uses ASCII punctuation so shells and Modelfiles stay portable.
    """
    lines = [
        "MKG PILOT - public.rag_corpus.source (PortalNode slice; scripts/portalnode_rag_slice_sources.txt):",
    ]
    for k in pilot_rag_source_keys():
        desc = PORTALNODE_PILOT_SOURCE_DESCRIPTIONS[k]
        lines.append(f"  - {k}: {desc}")
    return "\n".join(lines)
