# PatientTimelineVision Builder Flow

**Purpose:** Visual guide to graph construction process  
**See Also:** `server/ptv/builder.py` (implementation)

---

## 1. Builder Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                  PatientTimelineVisionBuilder                       │
│                                                                     │
│  Properties:                                                        │
│  - DETERMINISTIC: Same input → same graph (stable IDs)              │
│  - IDEMPOTENT: Re-running does not duplicate nodes                  │
│  - APPEND-ONLY: Updates create new nodes, never modify (INV-001)    │
│  - CLEAR PHASES: Ingestion → Enrichment → Embeddings               │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────────────────┐
                    │  Raw EHR Timeline   │
                    │ ehr.patient_timeline│
                    └──────────┬──────────┘
                               │
                    ╔══════════╧══════════╗
                    ║   PHASE 1: INGEST   ║
                    ║   (PTVBuilder)      ║
                    ╚══════════╤══════════╝
                               │
                    ┌──────────┴──────────┐
                    │  Base Graph         │
                    │  (nodes + temporal  │
                    │   edges)            │
                    └──────────┬──────────┘
                               │
                    ╔══════════╧══════════╗
                    ║  PHASE 2: ENRICH    ║
                    ║  (EoH Modules)      ║
                    ╚══════════╤══════════╝
                               │
                    ┌──────────┴──────────┐
                    │  Enriched Graph     │
                    │  (annotations +     │
                    │   semantic edges)   │
                    └──────────┬──────────┘
                               │
                    ╔══════════╧══════════╗
                    ║ PHASE 3: EMBEDDINGS ║
                    ║ (Embedding Engine)  ║
                    ╚══════════╤══════════╝
                               │
                    ┌──────────┴──────────┐
                    │ Complete PTV Graph  │
                    │ (ready for agents)  │
                    └─────────────────────┘
```

---

## 2. Phase 1: Ingestion (Raw → Base Graph)

### Input: ehr.patient_timeline

```sql
-- Raw timeline table (flat)
SELECT * FROM ehr.patient_timeline WHERE patient_id = 'P001' ORDER BY ts;

-- Example rows:
| id  | patient_id | ts                  | event_type | event_subtype | structured            | text           | source    |
|-----|------------|---------------------|------------|---------------|-----------------------|----------------|-----------|
| 100 | P001       | 2024-01-15 10:00:00 | lab        | CRP           | {"value": 55, ...}    | "CRP=55 mg/L"  | EHR_Epic  |
| 101 | P001       | 2024-01-17 14:30:00 | symptom    | joint_pain    | {"severity": 7}       | "Joint pain"   | PatientApp|
| 102 | P001       | 2024-01-22 09:00:00 | med        | methotrexate  | {"dose": 20, ...}     | "MTX 20mg"     | EHR_Epic  |
```

### Process: Deterministic Transformation

```python
for row in ehr.patient_timeline:
    # 1. Generate STABLE ID (deterministic)
    event_id = generate_stable_event_id(
        patient_id=row.patient_id,
        timestamp=row.ts,
        event_type=row.event_type,
        source_system=row.source,
        source_row_id=str(row.id),  # Use source row ID if available
    )
    # Result: evt_100, evt_101, evt_102 (stable, won't change on re-run)
    
    # 2. Map event_type → NodeType
    node_type = map_event_type_to_node_type(row.event_type)
    # lab → MEASUREMENT
    # symptom → MEASUREMENT
    # med → MEDICATION_CHANGE
    
    # 3. Create PatientEventNode
    node = PatientEventNode(
        event_id=event_id,
        patient_id=row.patient_id,
        node_type=node_type,
        event_subtype=row.event_subtype,
        timestamp=row.ts,
        source_type=SourceType.RAW,
        source_system=row.source,
        discovered_by=["PTVBuilder_Ingestion_v1"],
        structured=row.structured,
        text=row.text,
        meta=row.meta,
    )
    
    # 4. Insert with ON CONFLICT DO NOTHING (idempotency)
    INSERT INTO ptv.event_node (...) VALUES (...)
    ON CONFLICT (event_id) DO NOTHING;
```

### Output: Base Graph with Temporal Edges

```
┌──────────────┐  TEMPORAL_SEQUENCE  ┌──────────────┐  TEMPORAL_SEQUENCE  ┌──────────────┐
│  evt_100     │────────────────────→│  evt_101     │────────────────────→│  evt_102     │
│  CRP=55      │  (strength=1.0,     │  Joint Pain  │  (strength=1.0,     │  MTX 20mg    │
│  2024-01-15  │   conf=1.0,         │  2024-01-17  │   conf=1.0,         │  2024-01-22  │
│  MEASUREMENT │   delta=2.4 days)   │  MEASUREMENT │   delta=4.6 days)   │  MED_CHANGE  │
└──────────────┘                     └──────────────┘                     └──────────────┘
```

### Idempotency: Re-running Phase 1

```python
# First run
builder.build_patient_vision(patient_id="P001")
# Creates 3 nodes, 2 edges

# Second run (no new data)
builder.build_patient_vision(patient_id="P001")
# Checks: vision exists for P001
# Returns: {"status": "existing", "node_count": 3, ...}
# No duplicates created!

# Third run (with force_rebuild=True)
builder.build_patient_vision(patient_id="P001", force_rebuild=True)
# Deletes existing vision
# Re-creates 3 nodes, 2 edges
# IDs are IDENTICAL (deterministic)
```

---

## 3. Phase 2: Enrichment (EoH Modules)

### Enrichment Hooks: Where EoH Modules Attach

```python
# Example: M4 Flare Signals Hook
class M4FlareSignalsHook(EnrichmentHook):
    def __init__(self):
        super().__init__(module_id="M4_FlareSignals", version="1.0")
    
    def enrich(self, patient_id: str, cur):
        """
        1. Find MEASUREMENT nodes (labs/symptoms)
        2. Compute flare_signal_strength
        3. Annotate nodes
        4. Create CAUSAL edges
        """
        # Step 1: Find candidate events
        cur.execute("""
            SELECT event_id, structured, annotations
            FROM ptv.event_node
            WHERE patient_id = %s
              AND node_type = 'measurement'
              AND (event_subtype = 'CRP' OR event_subtype = 'ESR' OR event_subtype = 'joint_pain')
              AND status = 'included'
        """, (patient_id,))
        
        for row in cur.fetchall():
            event_id, structured, annotations = row
            
            # Step 2: Compute flare signal strength
            signal_strength = self._compute_flare_signal_strength(structured)
            
            if signal_strength > 0.5:
                # Step 3: Annotate node (APPEND to annotations)
                self.annotate_node(
                    cur=cur,
                    event_id=event_id,
                    annotations={
                        "flare_signal_strength": signal_strength,
                        "signal_components": {
                            "crp_elevation": structured.get("value", 0) > 50,
                            "trend": "increasing",
                        }
                    }
                )
                
                # Step 4: Create CAUSAL edge to downstream events
                # (e.g., if MTX dose was changed after this lab)
                cur.execute("""
                    SELECT event_id FROM ptv.event_node
                    WHERE patient_id = %s
                      AND node_type = 'medication_change'
                      AND timestamp > (SELECT timestamp FROM ptv.event_node WHERE event_id = %s)
                      AND timestamp < (SELECT timestamp FROM ptv.event_node WHERE event_id = %s) + INTERVAL '14 days'
                """, (patient_id, event_id, event_id))
                
                for (target_event_id,) in cur.fetchall():
                    self.create_edge(
                        cur=cur,
                        source_event_id=event_id,
                        target_event_id=target_event_id,
                        relationship_type=RelationshipType.CAUSAL_LIKELY,
                        strength=0.85,
                        confidence=0.78,
                        annotations={
                            "causal_mechanism": "inflammatory marker triggered dose adjustment",
                        }
                    )
```

### Before vs After Enrichment

**Before (Phase 1 only):**
```
┌──────────────┐  TEMPORAL_SEQUENCE  ┌──────────────┐  TEMPORAL_SEQUENCE  ┌──────────────┐
│  evt_100     │────────────────────→│  evt_101     │────────────────────→│  evt_102     │
│  CRP=55      │                     │  Joint Pain  │                     │  MTX 20mg    │
│  annotations:│                     │  annotations:│                     │  annotations:│
│    {}        │                     │    {}        │                     │    {}        │
└──────────────┘                     └──────────────┘                     └──────────────┘
```

**After (Phase 2: M4 enrichment):**
```
┌──────────────┐  TEMPORAL_SEQUENCE  ┌──────────────┐  TEMPORAL_SEQUENCE  ┌──────────────┐
│  evt_100     │────────────────────→│  evt_101     │────────────────────→│  evt_102     │
│  CRP=55      │─────────┐           │  Joint Pain  │                     │  MTX 20mg    │
│  annotations:│         │           │  annotations:│                     │  annotations:│
│   M4: {      │         │           │   M4: {      │                     │    {}        │
│     signal:  │         │           │     signal:  │                     │              │
│     0.85     │         │           │     0.72     │                     │              │
│   }          │         │           │   }          │                     │              │
└──────────────┘         │           └──────────────┘                     └──────────────┘
                         │                                                      ↑
                         │            CAUSAL_LIKELY                             │
                         │            (strength=0.85,                           │
                         │             conf=0.78,                               │
                         │             discovered_by=['M4_FlareSignals'])       │
                         └──────────────────────────────────────────────────────┘
```

### Multiple Module Enrichment

```python
# Orchestrator runs multiple hooks in sequence
orchestrator = PatientTimelineVisionOrchestrator(db_pool)
orchestrator.register_hook(M1TerrainHook())      # Adds terrain_band
orchestrator.register_hook(M4FlareSignalsHook())  # Adds flare_signal_strength + CAUSAL edges
orchestrator.register_hook(M22CarePlanningHook()) # Adds DECISION nodes + CARE_PLAN edges

orchestrator.build_and_enrich(patient_id="P001")
```

**Result: Layered Annotations**
```
event_node.annotations = {
    "M1_Terrain": {
        "terrain_band": "elevated_chronic",
        "baseline_deviation": 2.3
    },
    "M4_FlareSignals": {
        "flare_signal_strength": 0.85,
        "signal_components": {...}
    },
    "M13_DiagnosticLandscape": {
        "diagnostic_impact": [...]
    }
}

event_node.discovered_by = [
    "PTVBuilder_Ingestion_v1",
    "M1_Terrain",
    "M4_FlareSignals",
    "M13_DiagnosticLandscape"
]
```

---

## 4. Updates: Append-Only Pattern (INV-001)

### Scenario: New Lab Result Arrives

```
Timeline at T0:
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  evt_100     │  │  evt_101     │  │  evt_102     │
│  CRP=55      │  │  Joint Pain  │  │  MTX 20mg    │
│  2024-01-15  │  │  2024-01-17  │  │  2024-01-22  │
└──────────────┘  └──────────────┘  └──────────────┘

New data arrives: CRP=28 on 2024-02-01
```

### Update Process: Incremental Append

```python
# Incremental update (not full rebuild)
builder.update_patient_vision(
    patient_id="P001",
    new_events_since=datetime(2024, 1, 23)  # After last known event
)

# Process:
# 1. Fetch raw timeline events WHERE ts > '2024-01-23'
# 2. Generate stable ID: evt_103
# 3. Insert new node (ON CONFLICT DO NOTHING)
# 4. Create TEMPORAL_SEQUENCE edge from evt_102 → evt_103
# 5. Update patient_vision.last_enriched_at
```

**Result:**
```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  evt_100     │  │  evt_101     │  │  evt_102     │  │  evt_103     │ ← NEW
│  CRP=55      │  │  Joint Pain  │  │  MTX 20mg    │  │  CRP=28      │
│  2024-01-15  │  │  2024-01-17  │  │  2024-01-22  │  │  2024-02-01  │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
                                                         ↑
                                            TEMPORAL_SEQUENCE edge created
```

### No Duplicates (Idempotency)

```python
# Running update twice with same data
builder.update_patient_vision(patient_id="P001", new_events_since=datetime(2024, 1, 23))
builder.update_patient_vision(patient_id="P001", new_events_since=datetime(2024, 1, 23))

# Second run:
# - Same stable ID generated: evt_103
# - INSERT ... ON CONFLICT (event_id) DO NOTHING
# - No duplicate created!
```

---

## 5. Corrections: Append-Only with Versioning (INV-001)

### Scenario: Lab Value Was Incorrect

```
Original:
┌──────────────┐
│  evt_100     │
│  CRP=55      │  ← WRONG! Should be 45
│  version: 1  │
│  status:     │
│   included   │
└──────────────┘

Correction needed: CRP should be 45, not 55
```

### Correction Process (Does NOT modify original)

```python
# Create corrected version (APPEND, not UPDATE)
new_event_id = create_corrected_node(
    cur=cur,
    original_event_id="evt_100",
    corrected_data={
        "structured": {"test_name": "CRP", "value": 45, "unit": "mg/L"}
    },
    correction_reason="Lab reported wrong value, corrected by clinician",
    corrected_by="ClinicalReview_v1"
)

# Result: evt_100_v2 created
```

**Graph After Correction:**
```
┌──────────────┐         SUPERSEDES        ┌──────────────┐
│  evt_100_v2  │───────────────────────────│  evt_100     │
│  CRP=45      │  (new corrects old)       │  CRP=55      │
│  version: 2  │                           │  version: 1  │
│  status:     │                           │  status:     │
│   included   │                           │   corrected  │
│  parent:     │                           │  superseded  │
│   evt_100    │                           │   by: v2     │
└──────────────┘                           └──────────────┘

Properties:
- Original evt_100 NOT deleted (immutable history)
- Original marked status=corrected
- New evt_100_v2 created with version=2
- SUPERSEDES edge shows lineage
- Queries filter to status='included' to see latest
```

### Querying: Only Active Nodes

```sql
-- View that filters to latest versions only
CREATE VIEW ptv.v_active_nodes AS
SELECT *
FROM ptv.event_node
WHERE status = 'included'
  AND superseded_by_event_id IS NULL;

-- Agents query this view (never see corrected nodes)
SELECT * FROM ptv.v_active_nodes WHERE patient_id = 'P001';
-- Returns: evt_100_v2 (not evt_100)

-- Full audit trail (if needed)
SELECT * FROM ptv.event_node WHERE event_id LIKE 'evt_100%' ORDER BY version;
-- Returns: evt_100 (v1, corrected), evt_100_v2 (v2, included)
```

---

## 6. Stable ID Generation (Determinism)

### Why Stable IDs Matter

```
Problem: Random IDs break idempotency
┌─────────────────────────────────────────────┐
│ Run 1: evt_abc123 (random UUID)             │
│ Run 2: evt_xyz789 (different random UUID)   │
│ → Same event, different IDs → DUPLICATE!    │
└─────────────────────────────────────────────┘

Solution: Deterministic ID generation
┌─────────────────────────────────────────────┐
│ Run 1: evt_100 (from source row ID)         │
│ Run 2: evt_100 (same source row ID)         │
│ → ON CONFLICT DO NOTHING → NO DUPLICATE     │
└─────────────────────────────────────────────┘
```

### ID Generation Strategy

```python
def generate_stable_event_id(
    patient_id: str,
    timestamp: datetime,
    event_type: str,
    source_system: str,
    source_row_id: Optional[str] = None,
) -> str:
    """
    Priority 1: Use source_row_id if available (most stable)
    Priority 2: Hash deterministic components
    """
    if source_row_id:
        return f"evt_{source_row_id}"
    
    # Fallback: hash patient_id + timestamp + type + source
    timestamp_ms = int(timestamp.timestamp() * 1000)
    patient_hash = hashlib.sha256(patient_id.encode()).hexdigest()[:8]
    type_hash = hashlib.sha256(event_type.encode()).hexdigest()[:4]
    source_hash = hashlib.sha256(source_system.encode()).hexdigest()[:4]
    
    return f"evt_{patient_hash}_{timestamp_ms}_{type_hash}_{source_hash}"

# Examples:
# With source_row_id=100 → evt_100
# Without source_row_id → evt_abc12345_1705334400000_lab_epic
#   (same input always produces same hash)
```

---

## 7. Complete Build Flow (All Phases)

```
┌────────────────────────────────────────────────────────────────────┐
│                         INPUT                                      │
│  ehr.patient_timeline (100 rows for patient P001)                 │
└────────────┬───────────────────────────────────────────────────────┘
             │
             ↓
  ╔═══════════════════════════════════════════════════════════╗
  ║  PHASE 1: INGESTION (PTVBuilder)                          ║
  ║                                                            ║
  ║  1. Check if vision exists (idempotency)                  ║
  ║  2. Fetch raw timeline events                             ║
  ║  3. Generate stable IDs (deterministic)                   ║
  ║  4. Map event_type → NodeType                             ║
  ║  5. Create PatientEventNode objects                       ║
  ║  6. Bulk insert nodes (ON CONFLICT DO NOTHING)            ║
  ║  7. Create TEMPORAL_SEQUENCE edges                        ║
  ║  8. Update patient_vision stats                           ║
  ║                                                            ║
  ║  Output: 100 nodes, 99 temporal edges                     ║
  ╚═══════════════════════════════════════════════════════════╝
             │
             ↓
  ╔═══════════════════════════════════════════════════════════╗
  ║  PHASE 2: ENRICHMENT (EoH Modules)                        ║
  ║                                                            ║
  ║  Hook 1: M1_Terrain                                       ║
  ║    - Annotate all nodes with terrain_band                 ║
  ║    - Create TEMPORAL_WINDOW edges                         ║
  ║    Output: 100 nodes annotated, 15 window edges           ║
  ║                                                            ║
  ║  Hook 2: M4_FlareSignals                                  ║
  ║    - Annotate labs/symptoms with flare_signal_strength    ║
  ║    - Create CAUSAL_LIKELY edges                           ║
  ║    Output: 42 nodes annotated, 8 causal edges             ║
  ║                                                            ║
  ║  Hook 3: M5_FlareWindowing                                ║
  ║    - Create DERIVED_INSIGHT nodes (flare episodes)        ║
  ║    - Create COMPOSITE + DERIVED_FROM edges                ║
  ║    Output: 3 derived nodes, 21 edges                      ║
  ║                                                            ║
  ║  Hook 4: M22_CarePlanning                                 ║
  ║    - Create DECISION nodes                                ║
  ║    - Create CARE_PLAN_LINK edges                          ║
  ║    Output: 5 decision nodes, 12 care plan edges           ║
  ║                                                            ║
  ║  Total: 108 nodes, 155 edges                              ║
  ╚═══════════════════════════════════════════════════════════╝
             │
             ↓
  ╔═══════════════════════════════════════════════════════════╗
  ║  PHASE 3: EMBEDDINGS (Embedding Engine)                   ║
  ║                                                            ║
  ║  1. For each node, generate graph-aware embedding         ║
  ║     (include neighbor context via edges)                  ║
  ║  2. Store in ptv.node_embeddings table                    ║
  ║  3. Link via embedding_id (INV-003)                       ║
  ║                                                            ║
  ║  Output: 108 embeddings created                           ║
  ╚═══════════════════════════════════════════════════════════╝
             │
             ↓
┌────────────┴───────────────────────────────────────────────────────┐
│                         OUTPUT                                     │
│  Complete PatientTimelineVision Graph                              │
│  - 108 nodes (100 raw + 8 derived)                                 │
│  - 155 edges (99 temporal + 56 semantic)                           │
│  - All nodes annotated by 4 modules                                │
│  - All embeddings generated                                        │
│  - Ready for agent queries                                         │
└────────────────────────────────────────────────────────────────────┘
```

---

## 8. API Usage Examples

### Example 1: Build from Scratch

```python
from server.ptv.builder import PatientTimelineVisionBuilder
import psycopg2

# Connect to database
db = psycopg2.connect("postgresql://localhost/2opmd_dev")

# Build vision
builder = PatientTimelineVisionBuilder(db)
result = builder.build_patient_vision(patient_id="DEMO_RA_001")

print(result)
# Output:
# {
#   "patient_id": "DEMO_RA_001",
#   "node_count": 100,
#   "edge_count": 99,
#   "built_at": "2025-01-15T10:30:00Z",
#   "status": "created"
# }
```

### Example 2: Incremental Update

```python
# New events arrive
result = builder.update_patient_vision(
    patient_id="DEMO_RA_001",
    new_events_since=datetime(2025, 1, 15)
)

print(result)
# Output:
# {
#   "patient_id": "DEMO_RA_001",
#   "new_nodes": 5,
#   "new_edges": 4,
#   "status": "updated"
# }
```

### Example 3: Full Enrichment Pipeline

```python
from server.ptv.builder import PatientTimelineVisionOrchestrator
from server.eoh.hooks import M1TerrainHook, M4FlareSignalsHook, M22CarePlanningHook

# Create orchestrator
orchestrator = PatientTimelineVisionOrchestrator(db)

# Register EoH module hooks
orchestrator.register_hook(M1TerrainHook())
orchestrator.register_hook(M4FlareSignalsHook())
orchestrator.register_hook(M22CarePlanningHook())

# Build + enrich in one call
result = orchestrator.build_and_enrich(patient_id="DEMO_RA_001")

print(result)
# Output:
# {
#   "patient_id": "DEMO_RA_001",
#   "build": {"node_count": 100, "edge_count": 99, ...},
#   "enrichment": [
#     {"module_id": "M1_Terrain", "stats": {"nodes_annotated": 100, ...}},
#     {"module_id": "M4_FlareSignals", "stats": {"nodes_annotated": 42, ...}},
#     {"module_id": "M22_CarePlanning", "stats": {"decision_nodes_created": 5, ...}}
#   ]
# }
```

### Example 4: Correction Workflow

```python
from server.ptv.builder import create_corrected_node

with db.cursor() as cur:
    # Correct a lab value
    new_event_id = create_corrected_node(
        cur=cur,
        original_event_id="evt_100",
        corrected_data={
            "structured": {"test_name": "CRP", "value": 45, "unit": "mg/L"}
        },
        correction_reason="Lab reported wrong value, corrected by clinician on 2025-01-16",
        corrected_by="ClinicalReview_v1"
    )
    
    db.commit()
    
    print(f"Created corrected node: {new_event_id}")
    # Output: Created corrected node: evt_100_v2
```

---

## 9. Key Takeaways

### ✅ Builder Properties

1. **DETERMINISTIC:** Same input → same graph (stable IDs from source data)
2. **IDEMPOTENT:** Re-running does not duplicate (ON CONFLICT DO NOTHING)
3. **APPEND-ONLY:** Updates create new nodes, never modify (INV-001)
4. **CLEAR PHASES:** Ingestion → Enrichment → Embeddings (separation of concerns)
5. **ADDRESSABLE:** Every event has stable ID (evt_{source_row_id} or hash)

### ✅ Enrichment Hooks

- EoH modules implement `EnrichmentHook` interface
- Hooks attach AFTER ingestion (read base graph, add annotations/edges)
- Multiple modules can enrich same nodes (layered annotations)
- Each module tracked in `discovered_by` array (provenance)

### ✅ Updates vs Corrections

| Operation | Use Case | Mechanism |
|-----------|----------|-----------|
| **Update** | New events arrive | Append new nodes with new IDs |
| **Correction** | Fix wrong data | Create versioned node (evt_100_v2), mark old as corrected |
| **Enrichment** | Add annotations | Update annotations JSONB (safe, append-only semantics) |

### ✅ Graph is Source of Truth (INV-004)

- All agent queries go through PTV API (no direct SQL to ehr.patient_timeline)
- Raw timeline is ingestion source, but graph is authoritative for reasoning
- Embeddings derive from graph structure (INV-003)
- All derived data references upstream nodes (INV-002)

---

**Next:** See `server/ptv/builder.py` for complete implementation.

