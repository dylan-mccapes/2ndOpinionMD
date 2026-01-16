# PatientTimelineVision Quick Reference

**For:** Developers implementing PTV integration  
**See also:** `PatientTimelineVision_Architecture.md` (full design)

---

## 🎯 Core Concept

**PatientTimelineVision (PTV)** = Patient data as a **knowledge graph** (not a flat table)

```
Flat Timeline:           PTV Graph:
┌──────────┐            ┌────────────┐
│ Row 1    │            │  Event 42  │──CAUSAL_LIKELY──→ ┌────────────┐
│ Row 2    │            │  (CRP=55)  │                   │  Event 44  │
│ Row 3    │            └────────────┘                   │  (MTX ↑)   │
│ Row 4    │                  ↓                          └────────────┘
│ ...      │            TEMPORAL_WINDOW                        ↑
└──────────┘                  ↓                          REFERENCE
                        ┌────────────┐                         │
                        │  Event 43  │─────────────────────────┘
                        │(Joint pain)│
                        └────────────┘
```

---

## 📦 What You Get

### Nodes (PatientEventVision)
- **Identity:** `event_id`, `patient_id`, `timestamp`
- **Type:** `LAB`, `MED`, `SYMPTOM`, `NOTE`, `IMAGING`, `DECISION`, `RISK_FLAG`, etc.
- **Data:** `structured` (parsed values), `text` (narrative)
- **Semantics:** `annotations` (EoH module enrichments)
- **Provenance:** `discovered_by` (which modules touched this)

### Edges (EventRelationship)
- **Types:** 
  - `TEMPORAL_SEQUENCE` (A before B)
  - `CAUSAL_LIKELY` (A caused B)
  - `REFERENCE` (A mentions B)
  - `SIMILARITY` (A ≈ B)
  - `PROVENANCE` (A derived from B)
  - `COMPOSITE` (A contains B)
  - `CONTRADICTION` (A conflicts with B)
- **Metadata:** `strength`, `confidence`, `discovered_by`

---

## 🔧 API Cheat Sheet

### Building a Vision

```python
# One-time per patient
ptv = PatientTimelineVision.build_from_ehr_timeline(
    patient_id="DEMO_RA_001",
    ehr_timeline_source="ehr.patient_timeline"
)
```

### Adding Annotations (EoH Module Pattern)

```python
# Load existing vision
ptv = PatientTimelineVision.load(patient_id="DEMO_RA_001")

# Find relevant events
lab_events = ptv.find_events(
    event_type=EventType.LAB,
    time_range=(start_date, end_date)
)

# Annotate with your module's insights
for event in lab_events:
    ptv.annotate_event(
        event_id=event.event_id,
        module_id="M4_FlareSignals",
        annotations={
            "flare_signal_strength": 0.85,
            "signal_components": {"crp_elevation": True, "esr_elevation": True}
        }
    )

# Add causal edges
ptv.add_edge(EventRelationship(
    source_event_id=lab_event.event_id,
    target_event_id=flare_flag_event.event_id,
    relationship_type=RelationshipType.CAUSAL_LIKELY,
    strength=0.9,
    confidence=0.85,
    discovered_by=["M4_FlareSignals"]
))

# Save
ptv.save()
```

### Traversal (Agent/LLM Use)

```python
# "Why was this decision made?"
causal_chain = ptv.traverse_backward(
    start_event_id="evt_decision_biologic_escalation",
    edge_types=[RelationshipType.CAUSAL_LIKELY, RelationshipType.PROVENANCE],
    max_hops=3,
    min_strength=0.5
)

# Result: [Decision] ← [Flare Risk] ← [CRP=65, ESR=82] ← [MTX failure]

# "What happened after this lab spike?"
effects = ptv.traverse_forward(
    start_event_id="evt_crp_55",
    edge_types=[RelationshipType.CAUSAL_LIKELY, RelationshipType.TEMPORAL_WINDOW],
    max_hops=2
)

# Result: [CRP=55] → [Joint pain report] → [MTX dose increase]
```

### Explanation Generation

```python
explanation = ptv.generate_explanation(
    decision_event_id="evt_biologic_start",
    include_module_provenance=True,
    max_causal_depth=3
)

# Output:
# "Biologic started due to:
#  1. Persistent flare risk (M7A, conf=0.92)
#  2. Lab evidence: CRP=65 mg/L (causal_likely, M4, conf=0.85)
#  3. MTX failure over 6 months (M22, conf=0.88)
#  Supporting guideline: EULAR 2021 RA treat-to-target"
```

---

## 🚫 What NOT to Do

### ❌ Don't Create Parallel Stores
```python
# BAD: Module creates its own table
db.execute("INSERT INTO eoh.m4_flare_signals ...")

# GOOD: Module annotates PTV
ptv.annotate_event(event_id, "M4", {"flare_signal": 0.85})
```

### ❌ Don't Duplicate Raw Data
```python
# BAD: Copying data from EHR to PTV with modifications
ptv.add_event(PatientEventVision(
    event_id="evt_123",
    structured={"crp": modified_value}  # Don't modify raw data!
))

# GOOD: Keep raw data, add annotations
ptv.annotate_event(
    event_id="evt_123",
    module_id="M1",
    annotations={"normalized_crp": normalized_value}
)
```

### ❌ Don't Ignore Provenance
```python
# BAD: Anonymous edge
edge = EventRelationship(
    source_event_id=...,
    target_event_id=...,
    relationship_type=RelationshipType.CAUSAL_LIKELY,
    discovered_by=[]  # ❌ Who created this?
)

# GOOD: Always track provenance
edge = EventRelationship(
    ...,
    discovered_by=["M4_FlareSignals", "M22_CarePlanning"]
)
```

---

## 🎓 Design Patterns

### Pattern 1: Module Enrichment
```python
class EoHModuleBase:
    def enrich_patient_vision(self, patient_id: str):
        ptv = PatientTimelineVision.load(patient_id)
        
        # 1. Find relevant events
        events = ptv.find_events(...)
        
        # 2. Compute insights
        for event in events:
            insight = self._compute_insight(event)
            
            # 3. Annotate (don't duplicate)
            ptv.annotate_event(event.event_id, self.module_id, insight)
        
        # 4. Add edges if relationships discovered
        for edge in self._detect_relationships(events):
            ptv.add_edge(edge)
        
        # 5. Save
        ptv.save()
```

### Pattern 2: Agent Query
```python
def answer_clinical_question(question: str, patient_id: str) -> str:
    ptv = PatientTimelineVision.load(patient_id)
    
    # 1. Identify key event(s) from question
    if "why" in question.lower():
        # Causal reasoning: traverse backward
        decision_event = ptv.find_event(...)
        causal_chain = ptv.traverse_backward(
            start_event_id=decision_event.event_id,
            edge_types=[RelationshipType.CAUSAL_LIKELY],
            max_hops=3
        )
        return ptv.generate_explanation(decision_event.event_id)
    
    elif "what happened after" in question.lower():
        # Forward reasoning: traverse forward
        start_event = ptv.find_event(...)
        effects = ptv.traverse_forward(
            start_event_id=start_event.event_id,
            edge_types=[RelationshipType.CAUSAL_LIKELY, RelationshipType.TEMPORAL_SEQUENCE]
        )
        return format_timeline(effects)
```

### Pattern 3: Composite Event Creation
```python
# Example: M5 creates a "Flare Episode" composite node

def create_flare_episode(ptv: PatientTimelineVision, 
                        window_start: datetime, 
                        window_end: datetime):
    # 1. Find all events in window
    constituent_events = ptv.find_events(
        time_range=(window_start, window_end),
        annotation_filter={"flare_signal_strength": [">", 0.5]}
    )
    
    # 2. Create composite node
    flare_episode = PatientEventVision(
        event_id=f"evt_flare_episode_{window_start.date()}",
        patient_id=ptv.patient_id,
        timestamp=window_start,
        event_type=EventType.RISK_FLAG,
        event_subtype="flare_episode",
        source="M5_FlareWindowing",
        status="included",
        discovered_by=["M5_FlareWindowing"],
        structured={
            "window_start": window_start,
            "window_end": window_end,
            "severity": "moderate",
            "constituent_count": len(constituent_events)
        }
    )
    ptv.add_event(flare_episode)
    
    # 3. Link constituents with COMPOSITE edges
    for event in constituent_events:
        ptv.add_edge(EventRelationship(
            source_event_id=flare_episode.event_id,
            target_event_id=event.event_id,
            relationship_type=RelationshipType.COMPOSITE,
            strength=1.0,
            confidence=1.0,
            discovered_by=["M5_FlareWindowing"]
        ))
```

---

## 📊 Key Differences from Flat Timeline

| You Want To... | Flat Timeline | PatientTimelineVision |
|---------------|---------------|----------------------|
| Find an event | `SELECT * WHERE ...` | `ptv.find_event(...)` |
| See what caused X | Complex SQL join + time window guess | `ptv.traverse_backward(X, [CAUSAL])` |
| See what X caused | Complex SQL join + time window guess | `ptv.traverse_forward(X, [CAUSAL])` |
| Add module insight | `UPDATE ... SET meta = meta || {...}` or new table | `ptv.annotate_event(...)` |
| Find similar episodes | Re-compute embeddings + vector search | `ptv.find_edges(type=SIMILARITY)` |
| Explain a decision | Write custom logic to reconstruct reasoning | `ptv.generate_explanation(decision_id)` |
| Track who computed what | Manual audit logs | `discovered_by` field on nodes/edges |

---

## ⚡ Performance Tips

1. **Index annotations:** If querying by specific annotations frequently, add GIN index:
   ```sql
   CREATE INDEX idx_event_annotations_gin ON ptv.event_node USING GIN(annotations);
   ```

2. **Limit traversal depth:** Use `max_hops` to avoid expensive graph traversals:
   ```python
   # Good for most cases
   ptv.traverse_backward(..., max_hops=3)
   
   # Use sparingly (expensive for large graphs)
   ptv.traverse_backward(..., max_hops=10)
   ```

3. **Filter by edge strength:** Skip weak relationships to reduce noise:
   ```python
   ptv.traverse_forward(..., min_strength=0.6)  # Only follow strong edges
   ```

4. **Batch operations:** When enriching multiple events, batch save at the end:
   ```python
   for event in events:
       ptv.annotate_event(...)  # Modifies in-memory graph
   ptv.save()  # Single write to DB
   ```

---

## 🐛 Common Pitfalls

### Pitfall 1: Creating Redundant Nodes
```python
# ❌ BAD: Creating duplicate node for same event
ptv.add_event(PatientEventVision(
    event_id="evt_crp_new",  # Different ID for same CRP result!
    ...
))

# ✅ GOOD: Annotate existing node
existing_event = ptv.find_event(...)
ptv.annotate_event(existing_event.event_id, module_id, annotations)
```

### Pitfall 2: Missing Confidence Scores
```python
# ❌ BAD: Edge without confidence
edge = EventRelationship(
    ...,
    confidence=None  # How confident are we?
)

# ✅ GOOD: Always include confidence
edge = EventRelationship(
    ...,
    confidence=0.85  # Based on statistical/ML model
)
```

### Pitfall 3: Ignoring Temporal Constraints
```python
# ❌ BAD: Creating CAUSAL edge from future to past
ptv.add_edge(EventRelationship(
    source_event_id=event_2024_03_15,
    target_event_id=event_2024_01_10,  # Target is in the past!
    relationship_type=RelationshipType.CAUSAL_LIKELY
))

# ✅ GOOD: Validate temporal ordering for causal edges
if source_event.timestamp < target_event.timestamp:
    ptv.add_edge(...)
```

---

## 🎯 Success Checklist

Before merging your PTV integration:

- [ ] Module reads from PTV (not raw `ehr.patient_timeline`)
- [ ] Module annotates PTV (not creates parallel table)
- [ ] All edges include `discovered_by` provenance
- [ ] Confidence scores are meaningful (0.0-1.0 range)
- [ ] Causal edges respect temporal ordering
- [ ] No duplicate nodes created for same raw event
- [ ] Performance tested on graph with >1000 events
- [ ] Documentation updated with new annotations/edge types

---

## 📚 Further Reading

- **Full Design:** `PatientTimelineVision_Architecture.md`
- **RepoVision Inspiration:** `ai_code_pipelines/ai_probe/repo_vision.py`
- **EoH Module Index:** `server/eoh/module_index.py`
- **Timeline Schema:** `database/schemas/ehr_timeline.sql`

---

**Questions?** This is a new architecture—expect iteration and refinement! 🚀

