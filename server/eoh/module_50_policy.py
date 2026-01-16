# server/eoh/module_50_policy.py
"""
Module 50 – DxLandscapeFromEoH Policy Text

This file just exposes MODULE_TEXT so we can ingest it into rag_corpus
as part of eoh_gold_2025, exactly like modules 49B and 49C.
"""

from __future__ import annotations

MODULE_TEXT = """
## 1. Module 50: Responsibility

> **DxLandscapeFromEoH (Module 50)**
> Input: one Episode of Health (EoH)
> Output: a structured **diagnostic landscape** for that episode: candidate diagnoses, grouped into clinically meaningful clusters, with scores and explainable evidence back to the EoH.

Think of it as: `EoH → DxLandscape`.

---

## 2. Top-level service interface

### 2.1. Request

```ts
// Module 50 – request to compute diagnostic landscape from an Episode of Health
export interface DxLandscapeFromEoHRequest {
  // Either a reference to a stored EoH, or an inline payload
  eohRef?: {
    tenantId: string;
    eohId: string;          // canonical Episode-of-Health identifier
    versionId?: string;     // optional, for reproducible re-runs
  };

  eohInline?: EpisodeOfHealth; // if caller passes the episode directly

  // Optional: narrow or tune the diagnostic scope
  options?: DxLandscapeOptions;

  // Who/what is asking & why (for audit and policy)
  context?: RequestContext;
}
```

Where:

```ts
export interface DxLandscapeOptions {
  // Limit which diagnostic “families” to emphasize (SNOMED, value sets, or internal tags)
  focusSets?: string[];      // e.g. ["fibromyalgia", "axial_spondyloarthritis", "neurodegeneration"]

  // Minimum normalized score (0–1) to include a candidate in the final landscape
  minCandidateScore?: number;     // default e.g. 0.1

  // Maximum number of clusters and candidates per cluster
  maxClusters?: number;           // default e.g. 10
  maxCandidatesPerCluster?: number; // default e.g. 15

  // How much explainability to return
  explainabilityLevel?: "none" | "basic" | "full";

  // Whether to include predictions about stage & acuity
  includeStageAndAcuity?: boolean;   // default true

  // Whether to include model-level metadata/perf
  includeModelContributions?: boolean; // default true

  // Optional time horizon for prognostic views, if supported
  timeHorizon?: "point_in_time" | "1_year" | "5_year";
}
```

```ts
export interface RequestContext {
  requestingUserId?: string;   // clinician / service ID
  requestingSystemId?: string; // EMR/CDS system
  purposeOfUse?: "diagnosis" | "screening" | "research" | "quality_improvement";
  correlationId?: string;      // for traceability across modules
}
```

> `EpisodeOfHealth` here is whatever canonical structure you’ve defined elsewhere (can be FHIR EpisodeOfCare + bundle, or your own EoH schema). Module 50 just assumes it can query clinical facts from it.

---

### 2.2. Response

```ts
export interface DxLandscapeFromEoHResponse {
  moduleId: "Module50.DxLandscapeFromEoH";
  moduleVersion: string;            // semantic version of this module

  eohId: string;
  eohVersionId?: string;

  generatedAt: string;             // ISO-8601 UTC
  generationContext?: GenerationContext;

  landscape: DxLandscape;

  debugInfo?: DxLandscapeDebugInfo; // optional, for internal use
}
```

```ts
export interface GenerationContext {
  optionsApplied: DxLandscapeOptions;
  inputSnapshotId?: string;       // internal ID of the exact EoH snapshot used
  runtimeMs?: number;
}
```

---

## 3. DxLandscape data model

### 3.1. DxLandscape

```ts
export interface DxLandscape {
  subject: SubjectRef;           // patient
  episode: EpisodeRef;           // the EoH this pertains to

  // High-level narrative / summary suitable for UI
  summary: DxLandscapeSummary;

  // Clusters of related diagnoses or phenotypes
  clusters: DxCluster[];

  // Optional: global view of which models contributed and how
  modelContributions?: ModelContribution[];

  // Optional: global signals (e.g., “high neurodegenerative risk”)
  globalSignals?: GlobalDxSignal[];
}
```

```ts
export interface SubjectRef {
  patientId: string;
  demographics?: {
    ageYears?: number;
    sexAtBirth?: "male" | "female" | "other" | "unknown";
    genderIdentity?: string;
  };
}

export interface EpisodeRef {
  eohId: string;
  label?: string;         // e.g. "Fibromyalgia workup – 2025-09-30"
  startedAt?: string;
  endedAt?: string;
}
```

```ts
export interface DxLandscapeSummary {
  title: string;          // short: "Musculoskeletal & Neurocognitive Differential"
  shortText: string;      // 1–2 sentence summary
  longText?: string;      // more detailed narrative if needed
  keyFlags?: KeyFlag[];   // e.g. "Red flag for axial spondyloarthritis"
}

export interface KeyFlag {
  code: string;                     // internal or SNOMED code for flag type
  label: string;
  severity?: "info" | "warning" | "critical";
  rationale?: string;
}
```

---

### 3.2. DxCluster

A cluster groups related candidate diagnoses (e.g. *“central sensitization / fibromyalgia spectrum”*, *“axial spondyloarthritis”*, *“neurodegeneration / dementia”*).

```ts
export interface DxCluster {
  clusterId: string;
  name: string;                  // e.g. "Fibromyalgia / central sensitization"
  description?: string;

  // Overall “weight” for this cluster in [0,1], normalized across clusters
  clusterScore: number;

  // Which disease family or concept set this represents (SNOMED, etc.)
  semanticTag?: string;          // e.g. "fibromyalgia_cluster", "axSpA_cluster"

  candidates: DxCandidate[];

  // Aggregate evidence & actions at the cluster level
  clusterEvidenceSummary?: EvidenceSummary;
  recommendedActionsSummary?: ActionSuggestion[];
}
```

---

### 3.3. DxCandidate

This is one concrete candidate diagnosis in the differential list.

```ts
export interface DxCandidate {
  candidateId: string;

  // Diagnosis concept
  code: CodeableConcept;        // SNOMED/ICD/etc
  label: string;                // human-readable

  // Scoring
  score: number;                // 0–1, calibrated probability or normalized risk
  scoreType: "probability" | "risk_score" | "ranking_score";
  scoreRank?: number;           // rank within cluster (1 = highest)

  // Optional clinical qualifiers
  stage?: string;               // e.g. "early", "advanced", or TNM-like if applicable
  acuity?: "acute" | "subacute" | "chronic" | "episodic";
  onsetLikelihood?: "new" | "preexisting" | "uncertain";

  // Evidence
  positiveEvidence: EvidenceItem[];
  negativeEvidence?: EvidenceItem[];
  conflictingEvidence?: EvidenceItem[];

  // Explainable ML bits (per-candidate)
  featureAttributions?: FeatureAttributionSummary;

  // Suggested next steps if this candidate is considered
  recommendedActions?: ActionSuggestion[];

  // Provenance
  provenance: CandidateProvenance;
}
```

```ts
export interface CodeableConcept {
  system: string;            // e.g. "SNOMED-CT", "ICD10"
  code: string;
  display: string;
}
```

---

### 3.4. Evidence model

We want every candidate to be explainable back to concrete EoH facts.

```ts
export interface EvidenceItem {
  evidenceId: string;

  type:
    | "symptom"
    | "sign"
    | "lab"
    | "imaging"
    | "vital"
    | "questionnaire_score"
    | "history"
    | "physical_exam"
    | "demographic"
    | "medication"
    | "risk_factor"
    | "ai_feature";   // derived feature from Module 20/30/etc

  polarity: "supports" | "contradicts" | "neutral";

  // Reference back to the EoH or derived structure
  sourceRef: EvidenceSourceRef;

  // Text summary for UI
  description: string;         // e.g. "BDI-II score 28 (moderate-severe depression)"

  // Quantitative strength of this evidence for this candidate
  weight?: number;             // 0–1, normalized within candidate

  // Optional structured value
  value?: {
    numericValue?: number;
    unit?: string;
    codedValue?: CodeableConcept;
    freeText?: string;
  };

  // Optional timing information
  observedAt?: string;         // ISO-8601
}
```

```ts
export interface EvidenceSourceRef {
  // At least one of these should be populated
  eohFactId?: string;         // internal EoH fact/observation id
  fhirResourceRef?: {
    resourceType: string;     // e.g. "Observation", "Condition"
    resourceId: string;
  };
  derivedFeatureId?: string;  // feature from earlier feature-engineering module
}
```

```ts
export interface EvidenceSummary {
  nSupporting: number;
  nContradicting: number;
  strongestItems: EvidenceItem[];  // short list for UI
}
```

---

### 3.5. Explainability / feature attribution

```ts
export interface FeatureAttributionSummary {
  method?: "shap" | "permutation_importance" | "linear_coefficients" | "rule_based";
  topFeatures: FeatureContribution[];
}

export interface FeatureContribution {
  featureId: string;          // internal feature key
  featureLabel: string;       // human-readable
  contribution: number;       // positive/negative, magnitude indicates strength
  evidenceRefs?: EvidenceSourceRef[]; // links back to raw facts
}
```

---

### 3.6. ModelContribution (per-model provenance)

This lets you know **which models ran, on what, and what they output**.

```ts
export interface ModelContribution {
  modelId: string;                // e.g. "FM_Severity_Classifier_v3"
  modelVersion: string;           // semantic version / git hash
  modelType: "classification" | "regression" | "clustering" | "rules_engine";

  // What this model was “about”
  focus?: string;                 // e.g. "fibromyalgia_severity", "axSpA_radiographic_progression"

  // Output signals from this model
  outputs: ModelOutputSignal[];

  // Mappings from model outputs to DxCandidates (if not 1:1)
  mappedCandidates?: ModelToCandidateMapping[];

  // Performance metadata (for audit / UI)
  performance?: {
    aucRoc?: number;
    auprc?: number;
    calibrationSlope?: number;
    validationCohort?: string;    // description, e.g. "N=166 FM cohort (Spain, 2021–2022)"
    lastValidatedAt?: string;
  };
}
```

```ts
export interface ModelOutputSignal {
  signalId: string;
  label: string;
  value: number;                // raw score (e.g. logit, risk score, cluster index)
  scaledValue?: number;         // 0–1 scaled
  unit?: string;
}
```

```ts
export interface ModelToCandidateMapping {
  signalId: string;             // from ModelOutputSignal
  candidateId: string;          // from DxCandidate
  mappingType: "direct" | "heuristic" | "cluster_membership";
}
```

---

### 3.7. Global signals

These are high-level “meta” outputs across the whole landscape.

```ts
export interface GlobalDxSignal {
  signalId: string;
  label: string;                // e.g. "High likelihood of chronic pain central sensitization"
  score: number;                // 0–1
  supportingCandidates?: string[]; // candidateIds
}
```

---

### 3.8. Recommended actions

At both candidate and cluster level.

```ts
export interface ActionSuggestion {
  actionId: string;

  type:
    | "order_test"
    | "order_imaging"
    | "change_medication"
    | "refer_specialist"
    | "screening_tool"
    | "lifestyle_or_nonpharm"
    | "monitoring"
    | "documentation";

  label: string;            // "Order MRI pelvis", "Administer HADS", etc.
  description?: string;     // brief rationale

  // Clinical priority
  priority?: "low" | "medium" | "high";

  // Optional coded representation (e.g., for CPOE integration)
  code?: CodeableConcept;

  // Which candidate/cluster it’s tied to
  targetCandidateId?: string;
  targetClusterId?: string;
}
```

---

### 3.9. Debug info (optional, internal)

```ts
export interface DxLandscapeDebugInfo {
  rawModelInputs?: Record<string, unknown>; // per-model feature matrices etc.
  rawModelOutputs?: Record<string, unknown>;
  errors?: string[];
  warnings?: string[];
}
```

---

## 4. Example REST-ish endpoint

If you want to expose Module 50 as a service:

```http
POST /modules/50/dx-landscape

Body: DxLandscapeFromEoHRequest
→ 200 OK
Body: DxLandscapeFromEoHResponse
```

Or gRPC:

```proto
service DxLandscapeService {
  rpc DxLandscapeFromEoH(DxLandscapeFromEoHRequest)
      returns (DxLandscapeFromEoHResponse);
}
```
"""
