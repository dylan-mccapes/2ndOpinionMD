# server/eoh/module_50_runtime.py
"""
Runtime scaffolding for Module 50 – DxLandscapeFromEoH.

This wraps Andras's spec in Python dataclasses and provides a thin async
entrypoint that other code (e.g., eoh_stream) can call. Right now it is a
shape-correct stub; you can gradually replace internals with real models.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Literal, Optional
from datetime import datetime, timezone
import logging

import asyncpg  # you'll already have this in the project

logger = logging.getLogger(__name__)

ScoreType = Literal["probability", "risk_score", "ranking_score"]
AcuityType = Literal["acute", "subacute", "chronic", "episodic"]
ExplainabilityLevel = Literal["none", "basic", "full"]

# ---------------------------------------------------------------------------
# Core dataclasses – direct translation of Andras's TS spec (trimmed a bit)
# ---------------------------------------------------------------------------

@dataclass
class CodeableConcept:
    system: str
    code: str
    display: str


@dataclass
class EvidenceSourceRef:
    eohFactId: Optional[str] = None
    fhirResourceRef: Optional[Dict[str, str]] = None
    derivedFeatureId: Optional[str] = None


@dataclass
class EvidenceValue:
    numericValue: Optional[float] = None
    unit: Optional[str] = None
    codedValue: Optional[CodeableConcept] = None
    freeText: Optional[str] = None


@dataclass
class EvidenceItem:
    evidenceId: str
    type: str  # "symptom" | "sign" | "lab" | ...
    polarity: Literal["supports", "contradicts", "neutral"]
    sourceRef: EvidenceSourceRef
    description: str
    weight: Optional[float] = None
    value: Optional[EvidenceValue] = None
    observedAt: Optional[str] = None  # ISO-8601


@dataclass
class EvidenceSummary:
    nSupporting: int
    nContradicting: int
    strongestItems: List[EvidenceItem] = field(default_factory=list)


@dataclass
class FeatureContribution:
    featureId: str
    featureLabel: str
    contribution: float
    evidenceRefs: List[EvidenceSourceRef] = field(default_factory=list)


@dataclass
class FeatureAttributionSummary:
    method: Optional[str] = None  # shap | permutation_importance | ...
    topFeatures: List[FeatureContribution] = field(default_factory=list)


@dataclass
class ActionSuggestion:
    actionId: str
    type: str  # order_test | refer_specialist | ...
    label: str
    description: Optional[str] = None
    priority: Optional[Literal["low", "medium", "high"]] = None
    code: Optional[CodeableConcept] = None
    targetCandidateId: Optional[str] = None
    targetClusterId: Optional[str] = None


@dataclass
class CandidateProvenance:
    # intentionally light for now; you can enrich later
    sourceModuleIds: List[str] = field(default_factory=list)
    notes: Optional[str] = None


@dataclass
class DxCandidate:
    candidateId: str
    code: CodeableConcept
    label: str
    score: float
    scoreType: ScoreType
    scoreRank: Optional[int] = None
    stage: Optional[str] = None
    acuity: Optional[AcuityType] = None
    onsetLikelihood: Optional[Literal["new", "preexisting", "uncertain"]] = None
    positiveEvidence: List[EvidenceItem] = field(default_factory=list)
    negativeEvidence: List[EvidenceItem] = field(default_factory=list)
    conflictingEvidence: List[EvidenceItem] = field(default_factory=list)
    featureAttributions: Optional[FeatureAttributionSummary] = None
    recommendedActions: List[ActionSuggestion] = field(default_factory=list)
    provenance: CandidateProvenance = field(default_factory=CandidateProvenance)


@dataclass
class DxCluster:
    clusterId: str
    name: str
    clusterScore: float
    description: Optional[str] = None
    semanticTag: Optional[str] = None
    candidates: List[DxCandidate] = field(default_factory=list)
    clusterEvidenceSummary: Optional[EvidenceSummary] = None
    recommendedActionsSummary: List[ActionSuggestion] = field(default_factory=list)


@dataclass
class KeyFlag:
    code: str
    label: str
    severity: Optional[Literal["info", "warning", "critical"]] = None
    rationale: Optional[str] = None


@dataclass
class DxLandscapeSummary:
    title: str
    shortText: str
    longText: Optional[str] = None
    keyFlags: List[KeyFlag] = field(default_factory=list)


@dataclass
class SubjectRef:
    patientId: str
    demographics: Optional[Dict[str, Any]] = None


@dataclass
class EpisodeRef:
    eohId: str
    label: Optional[str] = None
    startedAt: Optional[str] = None
    endedAt: Optional[str] = None


@dataclass
class GlobalDxSignal:
    signalId: str
    label: str
    score: float
    supportingCandidates: List[str] = field(default_factory=list)


@dataclass
class ModelOutputSignal:
    signalId: str
    label: str
    value: float
    scaledValue: Optional[float] = None
    unit: Optional[str] = None


@dataclass
class ModelToCandidateMapping:
    signalId: str
    candidateId: str
    mappingType: Literal["direct", "heuristic", "cluster_membership"]


@dataclass
class ModelContribution:
    modelId: str
    modelVersion: str
    modelType: Literal["classification", "regression", "clustering", "rules_engine"]
    focus: Optional[str] = None
    outputs: List[ModelOutputSignal] = field(default_factory=list)
    mappedCandidates: List[ModelToCandidateMapping] = field(default_factory=list)
    performance: Optional[Dict[str, Any]] = None


@dataclass
class DxLandscape:
    subject: SubjectRef
    episode: EpisodeRef
    summary: DxLandscapeSummary
    clusters: List[DxCluster] = field(default_factory=list)
    modelContributions: List[ModelContribution] = field(default_factory=list)
    globalSignals: List[GlobalDxSignal] = field(default_factory=list)


@dataclass
class DxLandscapeOptions:
    focusSets: Optional[List[str]] = None
    minCandidateScore: Optional[float] = None
    maxClusters: Optional[int] = None
    maxCandidatesPerCluster: Optional[int] = None
    explainabilityLevel: Optional[ExplainabilityLevel] = None
    includeStageAndAcuity: Optional[bool] = None
    includeModelContributions: Optional[bool] = None
    timeHorizon: Optional[Literal["point_in_time", "1_year", "5_year"]] = None


@dataclass
class DxLandscapeFromEoHRequest:
    tenantId: str
    eohId: str
    versionId: Optional[str] = None
    options: DxLandscapeOptions = field(default_factory=DxLandscapeOptions)
    context: Optional[Dict[str, Any]] = None


@dataclass
class GenerationContext:
    optionsApplied: DxLandscapeOptions
    inputSnapshotId: Optional[str] = None
    runtimeMs: Optional[int] = None


@dataclass
class DxLandscapeDebugInfo:
    rawModelInputs: Optional[Dict[str, Any]] = None
    rawModelOutputs: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class DxLandscapeFromEoHResponse:
    moduleId: str
    moduleVersion: str
    eohId: str
    eohVersionId: Optional[str]
    generatedAt: str
    generationContext: GenerationContext
    landscape: DxLandscape
    debugInfo: Optional[DxLandscapeDebugInfo] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Thin runtime entrypoint
# ---------------------------------------------------------------------------

async def compute_dx_landscape_from_eoh(
    pool: asyncpg.Pool,
    *,
    tenant_id: str,
    eoh_id: str,
    version_id: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> DxLandscapeFromEoHResponse:
    """
    Main entrypoint for Module 50.

    For now this is a conservative stub:
    - It introspects basic timeline facts if available (TODO).
    - It returns a single empty cluster with a narrative summary.
    - Importantly: it returns the full, shape-correct object, so downstream
      code and the EoH router can be wired against it without breaking later
      when we add real models.
    """

    opts = DxLandscapeOptions(**(options or {}))

    # TODO: pull basic demographic + episode label from your EoH schema
    # For now, we just mirror the ids.
    subject = SubjectRef(patientId=eoh_id)
    episode = EpisodeRef(eohId=eoh_id, label=f"EoH {eoh_id}")

    summary = DxLandscapeSummary(
        title="Diagnostic landscape (stub)",
        shortText="Module 50 is wired but does not yet execute real models.",
        longText=(
            "This is a placeholder DxLandscape produced by Module 50. "
            "The structure is stable; internal scoring and clustering will "
            "be filled in as we add model integration."
        ),
    )

    landscape = DxLandscape(
        subject=subject,
        episode=episode,
        summary=summary,
        clusters=[],          # no clusters yet
        modelContributions=[],  # no models yet
        globalSignals=[],
    )

    gen_ctx = GenerationContext(
        optionsApplied=opts,
        inputSnapshotId=None,
        runtimeMs=None,
    )

    resp = DxLandscapeFromEoHResponse(
        moduleId="Module50.DxLandscapeFromEoH",
        moduleVersion="0.0.1-stub",
        eohId=eoh_id,
        eohVersionId=version_id,
        generatedAt=datetime.now(timezone.utc).isoformat(),
        generationContext=gen_ctx,
        landscape=landscape,
        debugInfo=DxLandscapeDebugInfo(
            errors=[],
            warnings=["Module 50 is running in stub mode; scores are not calibrated."],
        ),
    )

    logger.info(
        "Module50 DxLandscapeFromEoH stub executed for eoh_id=%s tenant_id=%s",
        eoh_id,
        tenant_id,
    )
    return resp