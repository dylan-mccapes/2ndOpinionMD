# PatientTimelineVision (PTV) Module

**Authoritative knowledge graph for patient timelines**

## Overview

PatientTimelineVision transforms flat EHR timelines into navigable knowledge graphs with:
- **Nodes:** Clinical events (labs, meds, symptoms, decisions, risk flags)
- **Edges:** Typed relationships (temporal, causal, reference, similarity)
- **Annotations:** Semantic enrichment by EoH modules
- **Provenance:** Full lineage tracked on all elements

## Key Properties

| Property | Description | Mechanism |
|----------|-------------|-----------|
| **DETERMINISTIC** | Same input → same graph | Stable ID generation from source data |
| **IDEMPOTENT** | Re-running does not duplicate | `ON CONFLICT DO NOTHING` |
| **APPEND-ONLY** | Updates create new nodes, never modify | INV-001 enforcement via triggers |
| **CLEAR PHASES** | Ingestion → Enrichment → Embeddings | Orchestrator pattern |

## Files

```
server/ptv/
├── __init__.py              # Module exports
├── models.py                # Data models (PatientEventNode, EventRelationshipEdge)
├── builder.py               # Builder implementation (core logic)
├── example_hooks.py         # Example enrichment hooks (M1, M4, M5, M22 patterns)
└── README.md                # This file
```

## Usage

### 1. Basic Build

```python
from server.ptv import PatientTimelineVisionBuilder
import psycopg2

# Connect to database
db = psycopg2.connect("postgresql://localhost/2opmd_dev")

# Build vision for a patient
builder = PatientTimelineVisionBuilder(db)
result = builder.build_patient_vision(patient_id="DEMO_RA_001")

print(result)
# {
#   "patient_id": "DEMO_RA_001",
#   "node_count": 100,
#   "edge_count": 99,
#   "built_at": "2025-01-15T10:30:00Z",
#   "status": "created"
# }

db.close()
```

### 2. Incremental Update

```python
# New events arrived in ehr.patient_timeline
result = builder.update_patient_vision(
    patient_id="DEMO_RA_001",
    new_events_since=datetime(2025, 1, 15)
)

print(result)
# {
#   "patient_id": "DEMO_RA_001",
#   "new_nodes": 5,
#   "new_edges": 4,
#   "status": "updated"
# }
```

### 3. Full Pipeline with Enrichment

```python
from server.ptv import PatientTimelineVisionOrchestrator
from server.ptv.example_hooks import (
    ExampleTerrainHook,
    ExampleFlareSignalsHook,
    ExampleCarePlanningHook,
)

# Create orchestrator
orchestrator = PatientTimelineVisionOrchestrator(db)

# Register enrichment hooks (EoH modules)
orchestrator.register_hook(ExampleTerrainHook())
orchestrator.register_hook(ExampleFlareSignalsHook())
orchestrator.register_hook(ExampleCarePlanningHook())

# Build + enrich in one call
result = orchestrator.build_and_enrich(patient_id="DEMO_RA_001")

print(result)
# {
#   "patient_id": "DEMO_RA_001",
#   "build": {"node_count": 100, ...},
#   "enrichment": [
#     {"module_id": "M1_Terrain_Example", "stats": {...}},
#     {"module_id": "M4_FlareSignals_Example", "stats": {...}},
#     {"module_id": "M22_CarePlanning_Example", "stats": {...}}
#   ]
# }
```

### 4. Creating a Custom Enrichment Hook

```python
from server.ptv import EnrichmentHook, RelationshipType

class MyCustomHook(EnrichmentHook):
    def __init__(self):
        super().__init__(module_id="MyModule_v1", version="1.0")
    
    def enrich(self, patient_id: str, cur):
        """
        Enrich the graph for a patient.
        """
        # 1. Find relevant events
        cur.execute("""
            SELECT event_id, structured
            FROM ptv.event_node
            WHERE patient_id = %s AND node_type = 'measurement'
        """, (patient_id,))
        
        # 2. Compute insights
        for event_id, structured in cur.fetchall():
            my_score = self._compute_score(structured)
            
            # 3. Annotate node
            self.annotate_node(
                cur=cur,
                event_id=event_id,
                annotations={"my_score": my_score}
            )
            
            # 4. Create edges (optional)
            if my_score > 0.8:
                # Find related events and create CAUSAL edges
                # ...
                self.create_edge(
                    cur=cur,
                    source_event_id=event_id,
                    target_event_id=target_id,
                    relationship_type=RelationshipType.CAUSAL_LIKELY,
                    strength=0.9,
                    confidence=0.85,
                )
        
        return {"nodes_annotated": len(results)}
    
    def _compute_score(self, structured):
        # Your logic here
        return 0.5

# Use it
orchestrator.register_hook(MyCustomHook())
orchestrator.build_and_enrich(patient_id="P001")
```

### 5. Correction Workflow (Append-Only)

```python
from server.ptv import create_corrected_node

with db.cursor() as cur:
    # Correct a lab value (does NOT modify original)
    new_event_id = create_corrected_node(
        cur=cur,
        original_event_id="evt_100",
        corrected_data={
            "structured": {"test_name": "CRP", "value": 45, "unit": "mg/L"}
        },
        correction_reason="Lab value corrected by clinician",
        corrected_by="ClinicalReview_v1"
    )
    
    db.commit()
    
    print(f"Created corrected node: {new_event_id}")
    # Output: evt_100_v2
    
    # Original evt_100 marked as status='corrected'
    # New evt_100_v2 is active (status='included')
    # SUPERSEDES edge links them
```

## CLI Usage

### Build a vision

```bash
cd server/ptv
python builder.py DEMO_RA_001
```

### Build with enrichment hooks

```bash
python example_hooks.py DEMO_RA_001 --hooks terrain flare_signals care_planning
```

### Force rebuild

```bash
python builder.py DEMO_RA_001 --rebuild
```

## Architecture

### Phase 1: Ingestion

```
ehr.patient_timeline (flat rows)
         ↓
   [generate stable IDs]
         ↓
   [map event_type → NodeType]
         ↓
   [bulk insert with ON CONFLICT DO NOTHING]
         ↓
   [create TEMPORAL_SEQUENCE edges]
         ↓
Base graph (nodes + temporal edges)
```

### Phase 2: Enrichment

```
Base graph
    ↓
[Hook 1: M1 Terrain]
    ├─ Annotate: terrain_band
    └─ Edges: TEMPORAL_WINDOW
    ↓
[Hook 2: M4 Flare Signals]
    ├─ Annotate: flare_signal_strength
    └─ Edges: CAUSAL_LIKELY
    ↓
[Hook 3: M5 Flare Windowing]
    ├─ Create: DERIVED_INSIGHT nodes
    └─ Edges: COMPOSITE, DERIVED_FROM
    ↓
[Hook 4: M22 Care Planning]
    ├─ Create: DECISION nodes
    └─ Edges: CARE_PLAN_LINK
    ↓
Enriched graph
```

### Phase 3: Embeddings (TODO)

```
Enriched graph
    ↓
[Generate graph-aware embeddings]
    ↓
[Store in ptv.node_embeddings]
    ↓
Complete PTV (ready for agents)
```

## Data Model

### Node Types

| NodeType | Examples | Used For |
|----------|----------|----------|
| MEASUREMENT | Labs (CRP, ESR), vitals, symptoms | Numeric/categorical observations |
| MEDICATION_CHANGE | MTX start, prednisone taper | Treatment changes |
| RISK_SIGNAL | Flare risk, infection risk | Predictions/flags |
| NOTE | Progress note, imaging report | Clinical documentation |
| DECISION | Start biologic, order MRI | Treatment decisions |
| DERIVED_INSIGHT | Flare episode, remission period | EoH-generated composites |

### Edge Types

| RelationshipType | Meaning | Created By |
|-----------------|---------|------------|
| TEMPORAL_SEQUENCE | A before B (chronological) | Builder (Phase 1) |
| TEMPORAL_WINDOW | A and B in same time window | M1, M5 |
| CAUSAL_LIKELY | A caused B (strong) | M4, M22 |
| CAUSAL_POSSIBLE | A may have caused B (weak) | M4 |
| REFERENCES | A mentions B | NLP modules |
| DERIVED_FROM | A computed from B | M5, M13, M22 |
| COMPOSITE | A contains B | M5 |
| SIMILARITY | A similar to B | M13 |
| CARE_PLAN_LINK | A part of care plan from B | M22 |

## System Invariants

| Invariant | Description | Enforcement |
|-----------|-------------|-------------|
| **INV-001** | Graph is append-only; corrections are new nodes | PostgreSQL triggers prevent UPDATE/DELETE |
| **INV-002** | All derived data must reference upstream nodes | DERIVED_FROM edges required for DERIVED_INSIGHT |
| **INV-003** | No embeddings without a backing graph node | FOREIGN KEY constraint on node_embeddings |
| **INV-004** | No agent may reason directly from raw tables | API gateway + code review policy |
| **INV-005** | Temporal causality must be respected | Trigger validates source.timestamp < target.timestamp |
| **INV-006** | All edges must have provenance | CHECK constraint: discovered_by not empty |

## Testing

### Unit Tests (TODO)

```bash
pytest server/ptv/tests/
```

### Integration Test

```bash
# 1. Apply schema
psql 2opmd_dev < docs/PatientTimelineVision_GraphSchema.md

# 2. Insert test patient into ehr.patient_timeline
# (use existing test data)

# 3. Run builder
python server/ptv/builder.py TEST_PATIENT_001

# 4. Run enrichment
python server/ptv/example_hooks.py TEST_PATIENT_001 --hooks terrain flare_signals

# 5. Verify results
psql 2opmd_dev -c "SELECT COUNT(*) FROM ptv.event_node WHERE patient_id = 'TEST_PATIENT_001';"
psql 2opmd_dev -c "SELECT COUNT(*) FROM ptv.event_edge WHERE source_event_id IN (SELECT event_id FROM ptv.event_node WHERE patient_id = 'TEST_PATIENT_001');"
```

## Performance

### Typical Performance (100-event timeline)

| Operation | Time | Notes |
|-----------|------|-------|
| **Ingestion** | 0.5-1.0s | Bulk insert with ON CONFLICT |
| **Enrichment (M1)** | 0.2-0.5s | Annotations only |
| **Enrichment (M4)** | 0.5-1.5s | Annotations + edge creation |
| **Enrichment (M5)** | 1.0-2.0s | Derived node creation |
| **Full Pipeline** | 3-5s | All phases |

### Scalability

- **Small patient (100 events):** <5s full build
- **Medium patient (500 events):** <15s full build
- **Large patient (2000 events):** <60s full build

For larger graphs, consider:
- Neo4j migration (Phase 6 in roadmap)
- Caching layer for hot patients
- Async enrichment pipeline

## Troubleshooting

### Issue: Duplicate nodes created

**Cause:** Non-deterministic ID generation  
**Fix:** Ensure `source_row_id` is passed to `generate_stable_event_id()`

### Issue: Enrichment hook fails silently

**Cause:** Exception in hook.enrich() caught and logged  
**Fix:** Check logs for error details

### Issue: Temporal causality violation (INV-005)

**Cause:** Trying to create CAUSAL edge with source.timestamp > target.timestamp  
**Fix:** Check event timestamps before creating edge

### Issue: DERIVED_INSIGHT node has no DERIVED_FROM edges (INV-002)

**Cause:** `create_derived_node()` not creating upstream edges  
**Fix:** Ensure `contributing_event_ids` is non-empty

## Next Steps

1. **Apply Schema:** Run `docs/PatientTimelineVision_GraphSchema.md` DDL
2. **Test Builder:** Run on pilot patient (`python builder.py PILOT_PATIENT_001`)
3. **Implement EoH Hooks:** Convert existing M1-M50 modules to EnrichmentHook pattern
4. **Add Embeddings:** Implement Phase 3 (graph-aware embeddings)
5. **Agent Integration:** Update agent queries to use PTV API

## References

- **Full Design:** `docs/PatientTimelineVision_Architecture.md`
- **Builder Flow:** `docs/PatientTimelineVision_BuilderFlow.md`
- **Schema Spec:** `docs/PatientTimelineVision_GraphSchema.md`
- **Use Cases:** `docs/PatientTimelineVision_UseCaseComparisons.md`
- **Roadmap:** `docs/PatientTimelineVision_Roadmap.md`

## License

Internal 2ndOpinionMD project. Not for public distribution.

