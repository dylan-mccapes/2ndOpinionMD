# PatientTimelineVision Architecture Design

**Version:** 1.0 (Conceptual)  
**Inspired by:** RepoVision (ai_probe/repo_vision.py)  
**Date:** 2025-12-23  
**Status:** Design Phase - No Implementation Yet

---

## 1. Executive Summary

PatientTimelineVision (PTV) is a **semantically rich, event-based knowledge graph** that serves as the authoritative provenance source for all patient timeline data in 2ndOpinionMD. Inspired by RepoVision's approach to code understanding, PTV transforms flat EHR timelines into a navigable graph structure that enables IDE-like traversal, causal reasoning, and explainable AI decisions.

### Core Innovation
Unlike flat timeline tables, PTV represents patient data as a **multi-dimensional knowledge graph** where:
- **Nodes** = discrete clinical events (labs, meds, symptoms, decisions, imaging, risk flags)
- **Edges** = typed relationships (temporal, causal, reference, similarity, provenance)
- **Annotations** = semantic enrichment by EoH modules
- **Metadata** = context, confidence, source lineage

### Key Principles
1. **One-time ingestion per patient** (1:1 timeline → vision)
2. **Graph is source of truth** (all embeddings and reasoning derive from it)
3. **No duplication** (EoH modules stream into PTV, don't create parallel stores)
4. **IDE-like traversal** (agents can navigate forward/backward through causal chains)
5. **Temporal + semantic indexing** (efficient queries by time, type, or relationship)

---

## 2. Conceptual Architecture

### 2.1 High-Level Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PatientTimelineVision (PTV)                      │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Vision Graph Store                         │  │
│  │  - Nodes: PatientEventVision (enriched events)                │  │
│  │  - Edges: EventRelationship (typed edges)                     │  │
│  │  - Metadata: provenance, confidence, annotations              │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐                 |
│  │  Ingestion  │  │  Enrichment │  │  Query/      │                 │
│  │  Engine     │→ │  Pipeline   │→ │  Traversal   │                 │
│  │  (1:1 EHR)  │  │  (EoH mods) │  │  Engine      │                 │
│  └─────────────┘  └─────────────┘  └──────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
         ↑                    ↑                    ↓
         │                    │                    │
    ┌────────┐          ┌──────────┐         ┌──────────┐
    │  EHR/  │          │   EoH    │         │  Agents/ │
    │ ehr.   │          │ Modules  │         │  LLMs    │
    │patient │          │ (M1-M50) │         │          │
    │timeline│          └──────────┘         └──────────┘
    └────────┘
```

### 2.2 Data Flow

```
EHR Timeline (flat)
   │
   ├─→ [Ingestion Engine] ─→ PatientTimelineVision Graph
   │                              │
   │                              ├─→ [Semantic Enrichment] 
   │                              │   (EoH modules annotate)
   │                              │
   │                              ├─→ [Edge Detection]
   │                              │   (temporal, causal, reference)
   │                              │
   │                              ├─→ [Embedding Generation]
   │                              │   (derive from graph structure)
   │                              │
   │                              └─→ [Provenance Index]
   │                                  (track all transformations)
   │
   └─→ [EoH Modules] stream results INTO graph (no duplication)
```

---

## 3. Node Types (PatientEventVision)

Each node represents a **discrete clinical event** with semantic enrichment.

### 3.1 Core Node Schema

```python
@dataclass
class PatientEventVision:
    """
    A single node in the PatientTimelineVision graph.
    Analogous to RepoFileVision, but for clinical events.
    """
    # === Identity ===
    event_id: str              # Unique ID (e.g., "evt_12345")
    patient_id: str            # Patient ID
    
    # === Core Event Data ===
    timestamp: datetime        # When the event occurred
    event_type: EventType      # Enum: LAB, MED, SYMPTOM, NOTE, IMAGING, 
                               #       DECISION, RISK_FLAG, DIAGNOSIS, 
                               #       PROCEDURE, VITAL, ENCOUNTER
    event_subtype: str         # e.g., "CBC", "Methotrexate", "Joint Pain"
    
    # === Raw Data ===
    structured: Dict[str, Any] # Parsed structured data (lab values, doses, etc.)
    text: str                  # Narrative text (if any)
    source: str                # EHR system, manual entry, guideline, etc.
    
    # === Status & Provenance ===
    status: str                # included | excluded | uncertain | synthetic
    discovered_by: List[str]   # Which modules/agents discovered/enriched this
    ingestion_timestamp: datetime
    
    # === Semantic Annotations (enriched by EoH modules) ===
    annotations: Dict[str, Any]
    # Examples:
    #   - "flare_signal_strength": 0.85  (from M4)
    #   - "terrain_band": "elevated_chronic"  (from M1)
    #   - "diagnostic_landscape_impact": {...}  (from M13)
    #   - "causal_attribution": "likely medication effect"  (from M22)
    #   - "risk_profile": {"infection": 0.3, "flare": 0.7}
    #   - "clinical_significance": "high" | "moderate" | "low" | "noise"
    
    # === Embeddings (derived from graph context) ===
    embedding: Optional[np.ndarray]  # Dense vector representation
    embedding_method: str            # "local_context" | "global_timeline" | "hybrid"
    
    # === Metadata ===
    meta: Dict[str, Any]
    # Examples:
    #   - "confidence": 0.95
    #   - "data_quality": "high" | "moderate" | "low"
    #   - "is_inflection_point": True
    #   - "clinical_arc_id": "arc_ra_flare_2024Q2"
```

### 3.2 Event Type Taxonomy

| Event Type | Examples | Typical Sources |
|-----------|----------|-----------------|
| **LAB** | CBC, CRP, ESR, ANA, Anti-CCP, Creatinine | EHR labs, external results |
| **MED** | Methotrexate start/change/stop, Prednisone taper | Medication orders, admin records |
| **SYMPTOM** | Joint pain, fatigue, rash, fever | Patient notes, questionnaires |
| **NOTE** | Rheumatology visit note, ED note, discharge summary | Clinical documentation |
| **IMAGING** | X-ray, MRI, HRCT, ultrasound | Radiology reports, PACS |
| **DECISION** | Start biologic, hold MTX, escalate care | Care plans, orders, clinician notes |
| **RISK_FLAG** | Infection risk, flare risk, pregnancy planning | EoH modules, guideline triggers |
| **DIAGNOSIS** | RA diagnosis, lupus suspicion, comorbidity add | Problem list, encounter diagnoses |
| **PROCEDURE** | Joint injection, biopsy, surgery | Procedure notes, billing codes |
| **VITAL** | BP, HR, temp, weight | Vital signs flowsheets |
| **ENCOUNTER** | Office visit, hospitalization, telehealth | Encounter records |

---

## 4. Edge Types (EventRelationship)

Edges represent **typed relationships** between events, enabling graph traversal and causal reasoning.

### 4.1 Core Edge Schema

```python
@dataclass
class EventRelationship:
    """
    A directed edge between two PatientEventVision nodes.
    Analogous to RepoVision's import/reference edges.
    """
    # === Identity ===
    edge_id: str
    
    # === Nodes ===
    source_event_id: str       # "from" node
    target_event_id: str       # "to" node
    
    # === Edge Type ===
    relationship_type: RelationshipType
    # Enum values:
    #   TEMPORAL_SEQUENCE    # A happened before B (weak causality)
    #   TEMPORAL_WINDOW      # A and B in same flare/arc window
    #   CAUSAL_LIKELY        # A likely caused B (e.g., med → side effect)
    #   CAUSAL_POSSIBLE      # A may have caused B (weaker)
    #   REFERENCE            # A refers to B (e.g., note mentions prior lab)
    #   SIMILARITY           # A and B are similar events (e.g., two CBC results)
    #   CONTRADICTION        # A contradicts B (e.g., conflicting diagnoses)
    #   PROVENANCE           # A derived from B (e.g., flare flag from labs)
    #   CARE_PLAN_LINK       # A is part of care plan triggered by B
    #   COMPOSITE            # A is composed of B (e.g., flare episode contains labs)
    
    # === Strength & Confidence ===
    strength: float            # 0.0-1.0, how strong the relationship is
    confidence: float          # 0.0-1.0, how confident we are in this edge
    
    # === Provenance ===
    discovered_by: List[str]   # Which modules/agents created this edge
    
    # === Temporal Context ===
    time_delta: Optional[timedelta]  # Time gap between events (if temporal)
    
    # === Annotations ===
    annotations: Dict[str, Any]
    # Examples:
    #   - "causal_mechanism": "medication side effect"
    #   - "clinical_interpretation": "dose-response relationship"
    #   - "guideline_support": "EULAR 2021 RA guideline"
    #   - "statistical_evidence": {"effect_size": 0.8, "p_value": 0.02}
```

### 4.2 Edge Type Examples

| From Event | To Event | Relationship Type | Strength | Discovered By |
|-----------|----------|------------------|----------|---------------|
| Methotrexate dose increase | Liver enzyme elevation | CAUSAL_LIKELY | 0.85 | M22 (care planning), M4 (signal tagging) |
| Joint pain report | CRP lab order | REFERENCE | 1.0 | Ingestion Engine (clinical note reference) |
| CRP=45 mg/L | Flare risk flag | PROVENANCE | 0.9 | M4 (flare detection) |
| Morning stiffness | Joint swelling | TEMPORAL_WINDOW | 0.75 | M1 (terrain analysis) |
| Flare episode (composite) | 5 constituent labs | COMPOSITE | 1.0 | M5 (flare windowing) |
| RA diagnosis 2020 | SLE suspicion 2024 | CONTRADICTION | 0.6 | M13 (diagnostic landscape) |

---

## 5. How PTV Differs from Flat Timeline Table

### 5.1 Comparison Table

| Aspect | Flat `patient_timeline` Table | PatientTimelineVision Graph |
|--------|------------------------------|----------------------------|
| **Structure** | Rows of events, sorted by timestamp | Graph with nodes (events) and edges (relationships) |
| **Relationships** | Implicit (inferred by queries) | Explicit (typed edges with confidence) |
| **Traversal** | Linear scan or time-range queries | Multi-hop graph traversal (forward/backward causality) |
| **Causality** | Not represented | First-class edges (CAUSAL_LIKELY, CAUSAL_POSSIBLE) |
| **Provenance** | Source field only | Full provenance DAG (track all transformations) |
| **Semantic Enrichment** | JSONB blob in `structured` or `meta` | Structured annotations indexed by module |
| **Embeddings** | Stored per-row (isolated) | Derived from graph context (neighbors, edges) |
| **Duplication** | EoH modules create parallel stores | EoH modules annotate shared graph |
| **Reasoning** | Query → retrieve → reason | Navigate → traverse → explain |
| **Version Control** | Hard (must snapshot entire table) | Easy (track graph evolution, diffs) |

### 5.2 Example: Flat vs Graph

**Scenario:** Patient has elevated CRP (55 mg/L), then reports joint pain 2 days later, then gets methotrexate dose increase 1 week later.

**Flat Table Representation:**
```sql
-- Three disconnected rows
id | timestamp | event_type | structured
---+-----------+------------+------------
42 | 2024-01-15 10:00 | lab | {"test": "CRP", "value": 55}
43 | 2024-01-17 14:30 | symptom | {"type": "joint_pain", "severity": 7}
44 | 2024-01-22 09:00 | med | {"drug": "methotrexate", "dose": 20}

-- Relationships must be inferred by:
-- 1. Writing complex SQL joins with time windows
-- 2. Running separate NLP to detect references
-- 3. Using ML models to guess causality
-- 4. Re-computing for every query
```

**PTV Graph Representation:**
```python
# Three nodes with explicit edges
Node evt_42: CRP=55 (timestamp=2024-01-15 10:00)
Node evt_43: Joint pain (timestamp=2024-01-17 14:30)
Node evt_44: MTX dose=20 (timestamp=2024-01-22 09:00)

# Edges encode relationships
Edge e1: evt_42 → evt_43 [TEMPORAL_WINDOW, strength=0.7, time_delta=2.4days]
  annotations: {"flare_window": "2024-W03", "discovered_by": ["M5"]}

Edge e2: evt_42 → evt_44 [CAUSAL_LIKELY, strength=0.85, time_delta=7days]
  annotations: {"interpretation": "CRP elevation triggered dose increase",
                "discovered_by": ["M22", "M4"]}

Edge e3: evt_43 → evt_44 [REFERENCE, strength=1.0]
  annotations: {"note_text": "Patient reports persistent joint pain; 
                              increasing MTX to 20mg weekly",
                "discovered_by": ["IngestionEngine"]}

# Agents can now:
# - Traverse forward: "What happened after CRP spike?" → evt_43, evt_44
# - Traverse backward: "Why was MTX increased?" → evt_42 (via causal edge)
# - Explain: "CRP=55 likely triggered MTX increase (conf=0.85, M22+M4)"
```

---

## 6. IDE-Like Traversal for Agents

### 6.1 Core Traversal Operations

Inspired by IDE "go to definition" and "find references":

| Operation | Description | Graph Query |
|-----------|-------------|-------------|
| **Go to Cause** | "Why did this event happen?" | Traverse incoming CAUSAL_LIKELY/POSSIBLE edges |
| **Go to Effect** | "What did this event cause?" | Traverse outgoing CAUSAL_LIKELY/POSSIBLE edges |
| **Find References** | "What other events mention this?" | Traverse REFERENCE edges (bidirectional) |
| **Show Timeline Window** | "What else happened around this time?" | Find all nodes within TEMPORAL_WINDOW edges |
| **Explain Decision** | "Why was this clinical decision made?" | Traverse PROVENANCE edges backward to source events |
| **Find Contradictions** | "Are there conflicting diagnoses/data?" | Find CONTRADICTION edges |
| **Compose Episode** | "What events make up this flare?" | Traverse COMPOSITE edges to constituent events |
| **Similarity Search** | "Find similar past episodes" | Traverse SIMILARITY edges + embedding neighbors |

### 6.2 Example Agent Workflow

**Query:** "Why was the patient's biologic escalated in March 2024?"

```python
# 1. Agent finds decision event
decision_node = ptv.find_event(
    event_type=EventType.DECISION,
    text_contains="biologic escalated",
    time_range=("2024-03-01", "2024-03-31")
)

# 2. Traverse backward through CAUSAL and PROVENANCE edges
causal_chain = ptv.traverse_backward(
    start=decision_node,
    edge_types=[RelationshipType.CAUSAL_LIKELY, RelationshipType.PROVENANCE],
    max_hops=3
)

# Result: Graph path showing:
# Decision ← Flare Risk Flag ← (CRP=65, ESR=82, Joint Count=14) ← MTX failure

# 3. Agent can now explain with confidence scores:
explanation = ptv.generate_explanation(
    decision=decision_node,
    causal_chain=causal_chain,
    include_module_provenance=True
)
# Output:
# "Biologic escalated due to:
#  1. Elevated flare risk (M7A, conf=0.92)
#  2. Lab evidence: CRP=65, ESR=82 (both causal_likely, conf=0.85)
#  3. Clinical evidence: Joint count=14 (causal_likely, conf=0.78)
#  4. MTX failure over 6 months (M22 care planning, conf=0.88)"
```

### 6.3 Multi-Hop Reasoning Examples

**Example 1: Medication Side Effect Attribution**
```
Query: "Could this liver enzyme spike be from methotrexate?"

Graph Traversal:
AST=145 (event_evt_789) 
  ← [CAUSAL_POSSIBLE, 0.75, M22]
    ← MTX dose=25mg (event_evt_750)
      ← [CARE_PLAN_LINK, 0.9, M22]
        ← Flare risk increase (event_evt_720)

Answer: "Likely. MTX dose was increased 3 weeks before AST spike, 
         and M22 flagged causal_possible relationship (conf=0.75).
         Consider dose reduction per EULAR guidelines."
```

**Example 2: Flare Pattern Detection**
```
Query: "Does this patient have a seasonal flare pattern?"

Graph Traversal:
1. Find all COMPOSITE edges to flare episodes
2. Extract timestamps of flare nodes
3. Traverse SIMILARITY edges between flare episodes
4. Identify temporal clustering

Result: "Yes. 3 major flares detected:
         - March 2023 (spring)
         - March 2024 (spring)
         - October 2024 (fall)
         All share SIMILARITY edges (conf=0.82-0.88) with
         common features: CRP spikes, joint swelling, weather changes.
         Pattern suggests seasonal trigger (M13 diagnostic landscape)."
```

---

## 7. Integration with Existing EoH Modules

### 7.1 No Duplication Principle

**Current State (PRE-PTV):**
- `ehr.patient_timeline` table stores raw events
- EoH modules (M1-M50) compute features and store results in:
  - Module-specific tables (`eoh.m1_terrain`, `eoh.m4_flare_signals`, etc.)
  - JSONB blobs in `patient_timeline.meta`
  - Separate embedding stores
- **Problem:** Duplication, no single source of truth, hard to trace provenance

**Target State (POST-PTV):**
- `ehr.patient_timeline` remains as raw ingestion source
- **PatientTimelineVision is the authoritative graph**
- EoH modules **stream INTO** PTV by:
  1. Annotating existing nodes (add to `annotations` field)
  2. Creating new edges (e.g., M4 creates CAUSAL edges for flare signals)
  3. Creating synthetic nodes (e.g., M5 creates RISK_FLAG nodes for flare windows)
- All embeddings derive from PTV graph structure

### 7.2 Module Integration Pattern

```python
# Example: M4 (Flare Signal Tagging) integration

class Module4_FlareSignals:
    def process_patient(self, patient_id: str):
        # 1. Load PatientTimelineVision graph for patient
        ptv_graph = PatientTimelineVision.load(patient_id)
        
        # 2. Identify candidate flare signals (labs, symptoms)
        candidate_events = ptv_graph.find_events(
            event_types=[EventType.LAB, EventType.SYMPTOM],
            annotation_filter={"clinical_significance": ["high", "moderate"]}
        )
        
        # 3. Compute flare signal strength for each
        for event in candidate_events:
            flare_strength = self._compute_flare_signal_strength(event)
            
            # 4. Annotate the existing node (NO duplication)
            event.annotations["flare_signal_strength"] = flare_strength
            event.annotations["flare_signal_components"] = {...}
            event.discovered_by.append("M4_FlareSignals")
        
        # 5. Create causal edges to connect signals
        for signal_event in high_strength_signals:
            for related_event in self._find_related_events(signal_event):
                ptv_graph.add_edge(EventRelationship(
                    source_event_id=signal_event.event_id,
                    target_event_id=related_event.event_id,
                    relationship_type=RelationshipType.CAUSAL_LIKELY,
                    strength=0.85,
                    confidence=0.9,
                    discovered_by=["M4_FlareSignals"],
                    annotations={"mechanism": "lab-symptom correlation"}
                ))
        
        # 6. Save updated graph
        ptv_graph.save()
```

### 7.3 Module-to-PTV Mapping

| EoH Module | PTV Actions | Node Types | Edge Types |
|-----------|-------------|-----------|-----------|
| **M1 (Terrain)** | Annotate all events with terrain_band, baseline_deviation | All | TEMPORAL_WINDOW |
| **M4 (Flare Signals)** | Annotate labs/symptoms with flare_signal_strength | LAB, SYMPTOM | CAUSAL_LIKELY |
| **M5 (Flare Windowing)** | Create RISK_FLAG nodes for flare windows, COMPOSITE edges | RISK_FLAG | COMPOSITE, TEMPORAL_WINDOW |
| **M7A (Prognostics)** | Annotate events with risk_profile | DECISION, MED | PROVENANCE |
| **M13 (Diagnostic Landscape)** | Annotate DIAGNOSIS nodes with landscape probabilities | DIAGNOSIS | CONTRADICTION, SIMILARITY |
| **M22 (Care Planning)** | Create DECISION nodes, annotate with care_plan_rationale | DECISION | CARE_PLAN_LINK, CAUSAL_LIKELY |

---

## 8. Technical Implementation Considerations (NOT YET IMPLEMENTED)

### 8.1 Storage Options

| Option | Pros | Cons | Recommendation |
|--------|------|------|---------------|
| **PostgreSQL + JSONB** | Familiar, transactional, good for small-medium graphs | Poor multi-hop query performance | ✅ Phase 1: Prototype |
| **Neo4j / ArangoDB** | Native graph DB, excellent traversal performance | New dependency, deployment complexity | 🟡 Phase 2: Production |
| **Hybrid (Postgres + Graph)** | Best of both: relational integrity + graph queries | Sync complexity | 🟡 Phase 3: Scale |

### 8.2 Schema Design (PostgreSQL Prototype)

```sql
-- Core tables (Phase 1)

CREATE TABLE ptv.patient_vision (
    patient_id TEXT PRIMARY KEY,
    built_at TIMESTAMPTZ NOT NULL,
    metadata JSONB DEFAULT '{}',
    version INT DEFAULT 1
);

CREATE TABLE ptv.event_node (
    event_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL REFERENCES ptv.patient_vision(patient_id),
    timestamp TIMESTAMPTZ NOT NULL,
    event_type TEXT NOT NULL,
    event_subtype TEXT,
    structured JSONB DEFAULT '{}',
    text TEXT,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    discovered_by TEXT[] DEFAULT '{}',
    annotations JSONB DEFAULT '{}',
    embedding BYTEA,
    embedding_method TEXT,
    meta JSONB DEFAULT '{}'
);

CREATE TABLE ptv.event_edge (
    edge_id TEXT PRIMARY KEY,
    source_event_id TEXT NOT NULL REFERENCES ptv.event_node(event_id),
    target_event_id TEXT NOT NULL REFERENCES ptv.event_node(event_id),
    relationship_type TEXT NOT NULL,
    strength FLOAT NOT NULL CHECK (strength BETWEEN 0 AND 1),
    confidence FLOAT NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    discovered_by TEXT[] DEFAULT '{}',
    time_delta INTERVAL,
    annotations JSONB DEFAULT '{}'
);

-- Indexes for common traversal patterns
CREATE INDEX idx_event_node_patient_ts ON ptv.event_node(patient_id, timestamp);
CREATE INDEX idx_event_node_type ON ptv.event_node(event_type);
CREATE INDEX idx_event_edge_source ON ptv.event_edge(source_event_id);
CREATE INDEX idx_event_edge_target ON ptv.event_edge(target_event_id);
CREATE INDEX idx_event_edge_type ON ptv.event_edge(relationship_type);
CREATE INDEX idx_event_annotations_gin ON ptv.event_node USING GIN(annotations);
```

### 8.3 API Design

```python
# Core PTV API (conceptual)

class PatientTimelineVision:
    """
    Authoritative provenance graph for a single patient's timeline.
    """
    
    def __init__(self, patient_id: str):
        self.patient_id = patient_id
        self.nodes: Dict[str, PatientEventVision] = {}
        self.edges: Dict[str, EventRelationship] = {}
        self.metadata: Dict[str, Any] = {}
    
    # === Ingestion ===
    
    @classmethod
    def build_from_ehr_timeline(
        cls, 
        patient_id: str,
        ehr_timeline_source: str = "ehr.patient_timeline"
    ) -> "PatientTimelineVision":
        """
        One-time 1:1 ingestion from flat EHR timeline.
        """
        pass
    
    # === Node Operations ===
    
    def add_event(self, event: PatientEventVision) -> None:
        """Add or update an event node."""
        pass
    
    def find_event(
        self, 
        event_type: Optional[EventType] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        annotation_filter: Optional[Dict[str, Any]] = None
    ) -> List[PatientEventVision]:
        """Find events matching criteria."""
        pass
    
    def annotate_event(
        self,
        event_id: str,
        module_id: str,
        annotations: Dict[str, Any]
    ) -> None:
        """Add module annotations to existing event."""
        pass
    
    # === Edge Operations ===
    
    def add_edge(self, edge: EventRelationship) -> None:
        """Add a relationship edge."""
        pass
    
    def find_edges(
        self,
        source_event_id: Optional[str] = None,
        target_event_id: Optional[str] = None,
        relationship_type: Optional[RelationshipType] = None,
        min_strength: float = 0.0
    ) -> List[EventRelationship]:
        """Find edges matching criteria."""
        pass
    
    # === Traversal ===
    
    def traverse_forward(
        self,
        start_event_id: str,
        edge_types: List[RelationshipType],
        max_hops: int = 3,
        min_strength: float = 0.5
    ) -> List[List[PatientEventVision]]:
        """
        Multi-hop forward traversal (follow outgoing edges).
        Returns list of paths from start to reachable nodes.
        """
        pass
    
    def traverse_backward(
        self,
        start_event_id: str,
        edge_types: List[RelationshipType],
        max_hops: int = 3,
        min_strength: float = 0.5
    ) -> List[List[PatientEventVision]]:
        """
        Multi-hop backward traversal (follow incoming edges).
        Returns list of causal chains leading to start node.
        """
        pass
    
    def find_shortest_path(
        self,
        source_event_id: str,
        target_event_id: str,
        edge_types: Optional[List[RelationshipType]] = None
    ) -> Optional[List[PatientEventVision]]:
        """Find shortest path between two events."""
        pass
    
    # === Explanation ===
    
    def generate_explanation(
        self,
        decision_event_id: str,
        include_module_provenance: bool = True,
        max_causal_depth: int = 3
    ) -> str:
        """
        Generate human-readable explanation for a decision/diagnosis.
        Traverses backward through causal/provenance edges.
        """
        pass
    
    # === Persistence ===
    
    def save(self, path: Optional[str] = None) -> None:
        """Save vision graph to storage."""
        pass
    
    @classmethod
    def load(cls, patient_id: str) -> "PatientTimelineVision":
        """Load vision graph from storage."""
        pass
```

---

## 9. Comparison to Alternatives

### 9.1 Why Not Just Use Event Sourcing?

| Feature | Event Sourcing | PatientTimelineVision |
|---------|---------------|----------------------|
| **Events** | Append-only log | Graph with bidirectional traversal |
| **Relationships** | None (must replay to infer) | First-class typed edges |
| **Queries** | Replay + project | Direct graph traversal |
| **Semantics** | Raw events only | Semantically enriched nodes |
| **Provenance** | Implicit (event order) | Explicit (provenance edges) |
| **Use Case** | System state reconstruction | Clinical reasoning + explanation |

**Verdict:** Event sourcing is complementary (use for audit trail), but PTV adds semantic layer.

### 9.2 Why Not Just Use Knowledge Graphs (Generic)?

| Feature | Generic KG (e.g., RDF) | PatientTimelineVision |
|---------|----------------------|----------------------|
| **Domain** | General-purpose | Clinical timelines only |
| **Temporal** | Poor native support | First-class (timestamps, windows) |
| **Tooling** | SPARQL, complex setup | Python API, SQL fallback |
| **EoH Integration** | Manual | Native (modules stream in) |
| **Embedding Generation** | Manual | Automatic (graph-aware) |

**Verdict:** Generic KGs are overkill; PTV is purpose-built for patient timelines.

---

## 10. Success Criteria

PatientTimelineVision will be successful if:

1. **Single Source of Truth:** All patient timeline data flows through PTV (no parallel stores).
2. **Explainable Decisions:** Every clinical decision can be explained by traversing the graph.
3. **Efficient Traversal:** Multi-hop queries execute in <100ms for typical patient graphs.
4. **Module Adoption:** All EoH modules (M1-M50) annotate PTV instead of creating separate tables.
5. **Embedding Quality:** Graph-aware embeddings outperform flat timeline embeddings in retrieval tasks.
6. **Agent Productivity:** LLM agents can navigate PTV to answer complex "why" questions without custom SQL.
7. **Auditability:** Every annotation/edge includes provenance (which module, when, with what confidence).

---

## 11. Migration Path (Phase Rollout)

### Phase 1: Prototype (Postgres + Python)
- Implement core PatientTimelineVision class
- PostgreSQL storage backend
- Ingestion from `ehr.patient_timeline`
- Basic traversal operations
- Integrate 2-3 pilot modules (M1, M4, M22)

### Phase 2: EoH Integration
- Migrate all M1-M50 modules to stream into PTV
- Deprecate module-specific tables
- Implement graph-aware embedding generation
- Add explanation API

### Phase 3: Scale & Optimize
- Evaluate Neo4j/ArangoDB for production
- Implement caching layer
- Add real-time streaming (events flow into PTV on ingestion)
- Build IDE-like traversal UI for clinicians

---

## 12. Open Questions

1. **Temporal Versioning:** How do we handle graph evolution over time? (e.g., diagnosis changed, edge strength updated)
2. **Conflict Resolution:** What happens when two modules create contradictory edges?
3. **Embedding Strategy:** Should embeddings be pre-computed (node-level) or dynamic (query-time, context-aware)?
4. **Performance at Scale:** Can Postgres handle 10K+ events per patient with multi-hop traversal?
5. **Privacy & Security:** How do we ensure PTV respects data access controls (e.g., can't traverse to restricted events)?

---

## 13. Conclusion

PatientTimelineVision transforms 2ndOpinionMD's patient data from a flat timeline into a **semantically rich, traversable knowledge graph**. By treating clinical events as nodes and relationships as first-class edges, PTV enables:

- **Causal reasoning:** "Why did this happen?" → traverse backward
- **Impact analysis:** "What did this cause?" → traverse forward
- **Explainability:** Every decision backed by provenance paths
- **Agent productivity:** IDE-like navigation for LLMs
- **Data integrity:** Single source of truth, no duplication

This is not just a schema change—it's a **paradigm shift** from **passive data storage** to **active knowledge representation**.

---

**Next Steps:**
1. Review this design with clinical + engineering teams
2. Prototype Phase 1 (Postgres backend)
3. Pilot with 1-2 real patient timelines
4. Iterate based on EoH module integration feedback

**Document Status:** ✅ Design Complete | ⏸️ Implementation Pending

