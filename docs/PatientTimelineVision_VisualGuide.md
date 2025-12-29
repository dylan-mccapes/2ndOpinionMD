# PatientTimelineVision: Visual Architecture Guide

**Purpose:** Visual diagrams to understand PTV concepts at a glance.

---

## 1. Core Concept: Timeline as Graph

### Before PTV (Flat Timeline)
```
┌────────────────────────────────────────────────────────────────┐
│                    ehr.patient_timeline                        │
│                                                                │
│  Row 1  │ 2024-01-15 │ lab      │ CRP=55 mg/L                 │
│  Row 2  │ 2024-01-17 │ symptom  │ Joint pain, severity 7      │
│  Row 3  │ 2024-01-22 │ med      │ Methotrexate 20mg           │
│  Row 4  │ 2024-02-01 │ lab      │ CRP=28 mg/L                 │
│  Row 5  │ 2024-02-15 │ decision │ Continue MTX                │
│  ...                                                           │
└────────────────────────────────────────────────────────────────┘

Relationships? → ❌ Implicit (must infer from timestamps)
Causality?     → ❌ Not represented
Provenance?    → ❌ Just a "source" field
```

### After PTV (Knowledge Graph)
```
┌───────────────────────────────────────────────────────────────────────┐
│                  PatientTimelineVision Graph                          │
│                                                                       │
│      ┌──────────────┐                                                │
│      │  evt_42      │                                                │
│      │  CRP=55      │                                                │
│      │  2024-01-15  │                                                │
│      └──────┬───────┘                                                │
│             │ TEMPORAL_WINDOW                                        │
│             │ (strength=0.7, M5)                                     │
│             ↓                                                        │
│      ┌──────────────┐         REFERENCE                             │
│      │  evt_43      │    (strength=1.0, note)                       │
│      │  Joint Pain  │ ←──────────────────────┐                      │
│      │  2024-01-17  │                        │                      │
│      └──────┬───────┘                        │                      │
│             │                                │                      │
│             │ CAUSAL_LIKELY                  │                      │
│             │ (strength=0.85, M22+M4)        │                      │
│             ↓                                │                      │
│      ┌──────────────┐                  ┌─────────────┐             │
│      │  evt_44      │    PROVENANCE    │  evt_45     │             │
│      │  MTX 20mg    │◄─────────────────│  Decision   │             │
│      │  2024-01-22  │  (M22, conf=0.9) │  2024-02-15 │             │
│      └──────┬───────┘                  └─────────────┘             │
│             │                                ↑                      │
│             │ TEMPORAL_SEQUENCE              │                      │
│             ↓                                │                      │
│      ┌──────────────┐         CAUSAL_LIKELY │                      │
│      │  evt_46      │         (M4, 0.88)    │                      │
│      │  CRP=28      │────────────────────────┘                      │
│      │  2024-02-01  │                                               │
│      └──────────────┘                                               │
└───────────────────────────────────────────────────────────────────────┘

Relationships? → ✅ Explicit typed edges
Causality?     → ✅ CAUSAL_LIKELY/POSSIBLE edges with confidence
Provenance?    → ✅ discovered_by on nodes + edges
```

---

## 2. Node Anatomy

```
┌─────────────────────────────────────────────────────────────────┐
│                    PatientEventVision Node                      │
├─────────────────────────────────────────────────────────────────┤
│ Identity                                                        │
│   event_id:    "evt_12345"                                      │
│   patient_id:  "DEMO_RA_001"                                    │
│   timestamp:   2024-01-15 10:30:00                              │
├─────────────────────────────────────────────────────────────────┤
│ Core Data                                                       │
│   event_type:    LAB                                            │
│   event_subtype: "CRP"                                          │
│   structured:    {"test": "CRP", "value": 55, "unit": "mg/L"}  │
│   text:          "CRP elevated at 55 mg/L"                      │
│   source:        "EHR_LabCorp"                                  │
├─────────────────────────────────────────────────────────────────┤
│ Semantic Enrichment (added by EoH modules)                     │
│   annotations: {                                                │
│     "flare_signal_strength": 0.85,        ← from M4             │
│     "terrain_band": "elevated_chronic",   ← from M1             │
│     "diagnostic_landscape_impact": {...}, ← from M13            │
│     "clinical_significance": "high"       ← from M4             │
│   }                                                             │
├─────────────────────────────────────────────────────────────────┤
│ Provenance                                                      │
│   discovered_by: ["IngestionEngine", "M1", "M4", "M13"]        │
│   status:        "included"                                     │
├─────────────────────────────────────────────────────────────────┤
│ Embeddings                                                      │
│   embedding:        [0.23, -0.15, 0.87, ...]  (768-dim)        │
│   embedding_method: "graph_aware_context"                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Edge Anatomy

```
┌─────────────────────────────────────────────────────────────────┐
│                    EventRelationship Edge                       │
├─────────────────────────────────────────────────────────────────┤
│ Identity                                                        │
│   edge_id:          "edge_5678"                                 │
│   source_event_id:  "evt_42" (CRP=55)                           │
│   target_event_id:  "evt_44" (MTX increase)                     │
├─────────────────────────────────────────────────────────────────┤
│ Relationship Type                                               │
│   relationship_type: CAUSAL_LIKELY                              │
│                                                                 │
│   Other types:                                                  │
│     TEMPORAL_SEQUENCE    A → B in time                          │
│     TEMPORAL_WINDOW      A ≈ B temporally                       │
│     CAUSAL_LIKELY        A caused B (strong)                    │
│     CAUSAL_POSSIBLE      A may have caused B (weak)             │
│     REFERENCE            A mentions B                           │
│     SIMILARITY           A ≈ B (features)                       │
│     CONTRADICTION        A ≠ B (conflict)                       │
│     PROVENANCE           A derived from B                       │
│     CARE_PLAN_LINK       A part of plan from B                  │
│     COMPOSITE            A contains B                           │
├─────────────────────────────────────────────────────────────────┤
│ Strength & Confidence                                           │
│   strength:    0.85   (how strong the relationship)             │
│   confidence:  0.78   (how sure we are)                         │
├─────────────────────────────────────────────────────────────────┤
│ Provenance                                                      │
│   discovered_by: ["M22_CarePlanning", "M4_FlareSignals"]       │
├─────────────────────────────────────────────────────────────────┤
│ Context                                                         │
│   time_delta: 7 days                                            │
│   annotations: {                                                │
│     "causal_mechanism": "inflammatory marker triggered therapy",│
│     "guideline_support": "EULAR 2021 treat-to-target"          │
│   }                                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Graph Traversal Operations

### Go to Cause (Backward Traversal)
```
Question: "Why was biologic started?"

                    ┌──────────────┐
                    │  Biologic    │  ← Start here (decision)
                    │  Started     │
                    └──────┬───────┘
                           │
                  Traverse │ CAUSAL + PROVENANCE edges
                  backward │ (max_hops=3)
                           ↓
         ┌─────────────────┴─────────────────┐
         │                                   │
    ┌────┴────┐                       ┌──────┴─────┐
    │ Flare   │                       │ MTX        │
    │ Risk    │                       │ Failure    │
    │ High    │                       │ 6 months   │
    └────┬────┘                       └──────┬─────┘
         │                                   │
         │ PROVENANCE (M7A)                  │ PROVENANCE (M22)
         ↓                                   ↓
    ┌────────┬──────────┬───────┐      ┌─────────┬──────────┐
    │ CRP=65 │ ESR=82   │ Joint │      │ Lab     │ Symptom  │
    │        │          │ Cnt=14│      │ Trends  │ Persist  │
    └────────┴──────────┴───────┘      └─────────┴──────────┘

Answer: "Biologic started due to:
  1. Elevated flare risk (M7A, conf=0.92)
  2. Lab evidence: CRP=65, ESR=82 (M4, conf=0.85)
  3. MTX failure over 6 months (M22, conf=0.88)"
```

### Go to Effect (Forward Traversal)
```
Question: "What happened after CRP spike?"

    ┌──────────────┐
    │  CRP=55      │  ← Start here (lab)
    │  2024-01-15  │
    └──────┬───────┘
           │
  Traverse │ CAUSAL + TEMPORAL_WINDOW edges
  forward  │ (max_hops=2)
           ↓
    ┌──────┴───────┬──────────────┐
    │              │              │
┌───┴────┐   ┌─────┴─────┐  ┌────┴────┐
│ Joint  │   │ Flare     │  │ MTX     │
│ Pain   │   │ Risk      │  │ Increase│
│ Report │   │ Flag      │  │         │
└────────┘   └───────────┘  └─────────┘

Answer: "CRP spike led to:
  1. Patient-reported joint pain (2 days later)
  2. Flare risk flag generated (M5, conf=0.88)
  3. MTX dose increase (7 days later, M22)"
```

### Find References
```
Question: "What events mention this diagnosis?"

             ┌──────────────┐
        ┌────│  RA          │────┐
        │    │  Diagnosis   │    │
        │    │  2020-03-15  │    │
        │    └──────────────┘    │
        │                        │
        │ REFERENCE edges        │ REFERENCE edges
        ↓                        ↓
┌───────────────┐        ┌───────────────┐
│ Rheum Note    │        │ Insurance     │
│ 2020-03-20    │        │ Prior Auth    │
│ "RA confirmed"│        │ 2020-04-01    │
└───────────────┘        └───────────────┘
        ↓                        ↓
┌───────────────┐        ┌───────────────┐
│ MTX Start     │        │ DMARDs        │
│ "for new RA"  │        │ Approved      │
└───────────────┘        └───────────────┘
```

---

## 5. Composite Nodes (Episodes)

### Flare Episode as Composite Node

```
┌─────────────────────────────────────────────────────────────────┐
│           Flare Episode (Composite Node)                        │
│           evt_flare_2024Q1                                      │
│                                                                 │
│  event_type: RISK_FLAG                                          │
│  event_subtype: "flare_episode"                                 │
│  timestamp: 2024-01-15 (window start)                           │
│  structured: {                                                  │
│    "window_start": "2024-01-15",                                │
│    "window_end": "2024-01-28",                                  │
│    "severity": "moderate",                                      │
│    "constituent_count": 7                                       │
│  }                                                              │
│  discovered_by: ["M5_FlareWindowing"]                           │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ COMPOSITE edges (7 constituents)
                 │
     ┌───────────┼───────────┬───────────┬───────────┐
     │           │           │           │           │
     ↓           ↓           ↓           ↓           ↓
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ CRP=55  │ │ ESR=82  │ │ Joint   │ │ Morning │ │ Fatigue │
│ 01-15   │ │ 01-16   │ │ Swelling│ │ Stiff   │ │ 01-20   │
│         │ │         │ │ 01-17   │ │ 01-18   │ │         │
└─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
     ...                                            ...

Benefits:
- Query "find all flares" → returns composite nodes (not hundreds of labs)
- Agents can "zoom in" to constituents via COMPOSITE edges
- Flare-level annotations (severity, duration) stored once
- Can compare flare episodes using SIMILARITY edges
```

---

## 6. Module Integration Pattern

### How EoH Modules Stream into PTV

```
┌──────────────────────────────────────────────────────────────────┐
│                   PatientTimelineVision                          │
│                   (Authoritative Graph)                          │
│                                                                  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │ Event 1 │  │ Event 2 │  │ Event 3 │  │ Event 4 │           │
│  │         │  │         │  │         │  │         │           │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘           │
│       │            │            │            │                 │
│       └────────────┴────────────┴────────────┘                 │
│                    │                                            │
│             Edges stored here                                   │
└──────────────────────────────────────────────────────────────────┘
                     ↑
                     │
            Read, Annotate, Write Back
                     │
        ┌────────────┴────────────┬─────────────┬─────────────┐
        │                         │             │             │
   ┌────┴────┐              ┌─────┴─────┐ ┌────┴────┐  ┌─────┴─────┐
   │   M1    │              │    M4     │ │   M5    │  │   M22     │
   │ Terrain │              │   Flare   │ │  Flare  │  │   Care    │
   │ Analysis│              │  Signals  │ │ Windows │  │ Planning  │
   └─────────┘              └───────────┘ └─────────┘  └───────────┘
        │                         │             │             │
        │ Adds:                   │ Adds:       │ Adds:       │ Adds:
        │ - terrain_band          │ - flare_    │ - Composite │ - DECISION
        │   annotation            │   signal_   │   nodes     │   nodes
        │ - baseline_deviation    │   strength  │ - COMPOSITE │ - CARE_PLAN
        │ - TEMPORAL_WINDOW       │ - CAUSAL_   │   edges     │   edges
        │   edges                 │   LIKELY    │             │
        │                         │   edges     │             │

NO module creates its own separate table!
ALL annotations flow into the shared PTV graph.
```

---

## 7. Flat vs Graph: Side-by-Side

### Query: "Why was MTX increased?"

#### Flat Timeline Query
```sql
-- Step 1: Find MTX increase event
SELECT * FROM ehr.patient_timeline
WHERE patient_id = 'P001'
  AND event_type = 'med'
  AND text ILIKE '%methotrexate%increase%'
ORDER BY ts DESC LIMIT 1;

-- Result: event at 2024-01-22

-- Step 2: Find prior events (guess 30-day window)
SELECT * FROM ehr.patient_timeline
WHERE patient_id = 'P001'
  AND ts < '2024-01-22'
  AND ts > '2024-01-22'::timestamp - INTERVAL '30 days'
ORDER BY ts DESC;

-- Result: 42 events (labs, notes, symptoms, etc.)

-- Step 3: Manually sift through 42 events to infer causality
-- (brittle, error-prone, no confidence measure)
```

#### PTV Graph Query
```python
# Step 1: Find MTX increase event
ptv = PatientTimelineVision.load('P001')
mtx_event = ptv.find_event(
    event_type=EventType.MED,
    text_contains="methotrexate increase"
)[0]

# Step 2: Traverse backward through CAUSAL edges
causal_chain = ptv.traverse_backward(
    start_event_id=mtx_event.event_id,
    edge_types=[RelationshipType.CAUSAL_LIKELY],
    max_hops=2
)

# Result: [MTX increase] ← [Flare risk] ← [CRP=55, Joint pain]
# (explicit causality, confidence scores, module provenance)
```

---

## 8. Data Flow: Ingestion to Reasoning

```
┌────────────────────────────────────────────────────────────────────┐
│                        DATA FLOW                                   │
└────────────────────────────────────────────────────────────────────┘

1. RAW EHR DATA
   ↓
   ehr.patient_timeline (flat table)
   ├─ Row 1: Lab CRP=55
   ├─ Row 2: Symptom Joint Pain
   ├─ Row 3: Med MTX 20mg
   └─ ...

2. ONE-TIME INGESTION
   ↓
   PatientTimelineVision.build_from_ehr_timeline()
   ↓
   Initial graph created:
   ├─ Nodes: one per raw event
   ├─ Edges: TEMPORAL_SEQUENCE (time order)
   └─ Annotations: empty (to be filled by modules)

3. EoH MODULE ENRICHMENT
   ↓
   ┌─────────────────────────────────────────┐
   │ M1: Terrain Analysis                    │
   │  - Adds terrain_band annotations        │
   │  - Adds TEMPORAL_WINDOW edges           │
   └─────────────────────────────────────────┘
   ↓
   ┌─────────────────────────────────────────┐
   │ M4: Flare Signal Tagging                │
   │  - Adds flare_signal_strength           │
   │  - Adds CAUSAL_LIKELY edges             │
   └─────────────────────────────────────────┘
   ↓
   ┌─────────────────────────────────────────┐
   │ M5: Flare Windowing                     │
   │  - Creates RISK_FLAG composite nodes    │
   │  - Adds COMPOSITE edges                 │
   └─────────────────────────────────────────┘
   ↓
   ... (M7A, M13, M22, etc.)

4. EMBEDDING GENERATION
   ↓
   ptv.generate_graph_aware_embeddings()
   ├─ Node embeddings: include neighbor context
   ├─ Episode embeddings: aggregate constituents
   └─ Patient-level embedding: aggregate all

5. AGENT/LLM REASONING
   ↓
   Question: "Why was biologic started?"
   ↓
   Agent: ptv.traverse_backward(decision, CAUSAL_LIKELY)
   ↓
   Answer: "Biologic started due to:
            1. Flare risk (M7A, 0.92)
            2. CRP=65 (M4, 0.85)
            3. MTX failure (M22, 0.88)"
   ↓
   Provenance traceable to source events + modules
```

---

## 9. Success Metrics Visualization

### Current State (Flat Timeline)
```
┌────────────────────────────────────────────────────────────────┐
│                      METRICS                                   │
├────────────────────────────────────────────────────────────────┤
│ Explainability:        ████░░░░░░ (4/10)  ← Hard to trace      │
│ Reasoning Speed:       ███████░░░ (7/10)  ← SQL is fast        │
│ Causal Clarity:        ██░░░░░░░░ (2/10)  ← Implicit only      │
│ Module Integration:    ████░░░░░░ (4/10)  ← Parallel stores    │
│ Agent Productivity:    ███░░░░░░░ (3/10)  ← Manual SQL + logic │
│ Auditability:          ███░░░░░░░ (3/10)  ← Minimal provenance │
└────────────────────────────────────────────────────────────────┘
```

### Target State (PTV)
```
┌────────────────────────────────────────────────────────────────┐
│                      METRICS                                   │
├────────────────────────────────────────────────────────────────┤
│ Explainability:        █████████░ (9/10)  ← Graph traversal    │
│ Reasoning Speed:       ████████░░ (8/10)  ← Indexed graph      │
│ Causal Clarity:        █████████░ (9/10)  ← Explicit edges     │
│ Module Integration:    ██████████ (10/10) ← Shared graph       │
│ Agent Productivity:    █████████░ (9/10)  ← IDE-like nav       │
│ Auditability:          ██████████ (10/10) ← Full provenance    │
└────────────────────────────────────────────────────────────────┘
```

---

## 10. Quick Decision Tree: When to Use PTV

```
┌─────────────────────────────────────────────────┐
│ Do you need to answer "WHY" questions?          │
│ (e.g., "Why was this medication changed?")     │
└───────────┬─────────────────────────────────────┘
            │
         YES│
            ↓
┌─────────────────────────────────────────────────┐
│         Use PTV (traverse backward via          │
│         CAUSAL + PROVENANCE edges)              │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Do you need to predict "WHAT WILL HAPPEN"?      │
│ (e.g., "What's the impact of this lab spike?") │
└───────────┬─────────────────────────────────────┘
            │
         YES│
            ↓
┌─────────────────────────────────────────────────┐
│         Use PTV (traverse forward via           │
│         CAUSAL_LIKELY edges)                    │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Do you need to find similar episodes/patients?  │
└───────────┬─────────────────────────────────────┘
            │
         YES│
            ↓
┌─────────────────────────────────────────────────┐
│         Use PTV (graph-aware embeddings +       │
│         SIMILARITY edges)                       │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Do you need to audit/explain AI decisions?      │
└───────────┬─────────────────────────────────────┘
            │
         YES│
            ↓
┌─────────────────────────────────────────────────┐
│         Use PTV (discovered_by provenance       │
│         on all nodes/edges)                     │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Do you just need to list events chronologically?│
└───────────┬─────────────────────────────────────┘
            │
         YES│
            ↓
┌─────────────────────────────────────────────────┐
│         Either works (PTV or flat timeline)     │
│         (PTV is overkill for simple listing)    │
└─────────────────────────────────────────────────┘
```

---

## Summary

**PatientTimelineVision transforms:**

- **Rows** → **Nodes** (semantically enriched events)
- **Implicit relationships** → **Explicit edges** (typed, scored)
- **Manual inference** → **Graph traversal** (IDE-like navigation)
- **Duplicate stores** → **Single source of truth** (EoH modules annotate)
- **Brittle reasoning** → **Provenance-backed explanations** (auditability)

**Result:** Patient data becomes a **knowledge graph** that agents can reason over, not just a flat log.

---

**See also:**
- Full design: `PatientTimelineVision_Architecture.md`
- Quick reference: `PatientTimelineVision_QuickRef.md`
- Use case comparisons: `PatientTimelineVision_UseCaseComparisons.md`

