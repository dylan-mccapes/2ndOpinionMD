# PatientTimelineVision: Design Documentation Suite

**Version:** 1.0  
**Status:** Design Complete, Implementation Pending  
**Date:** December 23, 2025  
**Author:** Systems Architecture Team

---

## Executive Summary

**PatientTimelineVision (PTV)** is a semantically rich, event-based knowledge graph subsystem inspired by RepoVision. It transforms flat patient timelines from the EHR into navigable graph structures that enable:

- ✅ **Causal reasoning** ("Why did this happen?")
- ✅ **Impact analysis** ("What did this cause?")
- ✅ **Explainable AI** (full provenance of every decision)
- ✅ **IDE-like traversal** (agents navigate patient data like code)
- ✅ **Single source of truth** (EoH modules stream into shared graph, no duplication)

### Key Innovation

Unlike flat timeline tables, PTV represents patient data as a **multi-dimensional knowledge graph** where:
- **Nodes** = clinical events (labs, meds, symptoms, decisions, imaging, risk flags)
- **Edges** = typed relationships (temporal, causal, reference, similarity, provenance)
- **Annotations** = semantic enrichment by EoH modules
- **Metadata** = context, confidence, source lineage

---

## Documentation Suite

This design consists of 5 comprehensive documents:

### 1. Architecture Design (Main Document)
**File:** `PatientTimelineVision_Architecture.md`  
**Length:** ~13,000 words  
**Purpose:** Complete technical architecture specification

**Contents:**
- Conceptual architecture (components + data flow)
- Node types (PatientEventVision schema)
- Edge types (EventRelationship schema + taxonomy)
- Comparison to flat timeline tables
- Integration with EoH modules (M1-M50)
- Storage options (PostgreSQL vs. Neo4j)
- API design (core methods)
- Success criteria

**Audience:** Architects, senior engineers, product leaders

---

### 2. Quick Reference Guide
**File:** `PatientTimelineVision_QuickRef.md`  
**Length:** ~3,500 words  
**Purpose:** Practical developer guide for implementing PTV integrations

**Contents:**
- Core concept diagram
- Node and edge schemas (condensed)
- API cheat sheet (code examples)
- Common pitfalls and anti-patterns
- Design patterns (module enrichment, agent queries, composite nodes)
- Performance tips
- Success checklist

**Audience:** Developers implementing EoH module integrations

---

### 3. Use Case Comparisons
**File:** `PatientTimelineVision_UseCaseComparisons.md`  
**Length:** ~5,000 words  
**Purpose:** Show concrete before/after examples for common clinical reasoning tasks

**Contents:**
- Use Case 1: "Why was this medication escalated?"
- Use Case 2: "Does this patient have a seasonal flare pattern?"
- Use Case 3: "Could this liver enzyme spike be from methotrexate?"
- Use Case 4: "Show me the full story of this patient's RA journey"
- Use Case 5: "Compare this patient to similar cases"
- Summary comparison table (flat vs. PTV)

**Audience:** Product managers, clinical stakeholders, engineers

---

### 4. Visual Guide
**File:** `PatientTimelineVision_VisualGuide.md`  
**Length:** ~4,000 words  
**Purpose:** Visual diagrams and ASCII art to explain PTV concepts at a glance

**Contents:**
- Core concept: Timeline as graph (visual)
- Node anatomy (detailed diagram)
- Edge anatomy (detailed diagram)
- Graph traversal operations (visual examples)
- Composite nodes (flare episodes)
- Module integration pattern (visual)
- Flat vs. graph side-by-side
- Data flow (ingestion to reasoning)
- Success metrics visualization
- Decision tree: When to use PTV

**Audience:** All stakeholders (visual learners)

---

### 5. Implementation Roadmap
**File:** `PatientTimelineVision_Roadmap.md`  
**Length:** ~4,500 words  
**Purpose:** Phased implementation plan with milestones, tasks, and success criteria

**Contents:**
- **Phase 0:** Pre-implementation (stakeholder review)
- **Phase 1:** Core infrastructure (Weeks 1-4)
  - Data models, PostgreSQL backend, EHR ingestion, traversal operations
- **Phase 2:** EoH module integration (Weeks 5-8)
  - Pilot modules: M1, M4, M22
- **Phase 3:** Explanation & reasoning (Weeks 9-10)
  - Explanation API, agent query patterns
- **Phase 4:** Remaining EoH modules (Weeks 11-14)
  - Migrate M5, M7A, M13, M19, M24, M25, etc.
- **Phase 5:** Optimization & production (Weeks 15-16)
  - Performance tuning, monitoring, deployment
- **Phase 6:** Future enhancements
  - Neo4j migration, real-time streaming, visualization UI
- Risk mitigation strategies
- Resource requirements
- Success metrics

**Audience:** Project managers, engineering leads, executives

---

## Key Concepts at a Glance

### Node Types (Events)
| Type | Examples | Typical Sources |
|------|----------|-----------------|
| LAB | CRP, ESR, ANA, Anti-CCP | EHR labs, external results |
| MED | Methotrexate, Prednisone | Medication orders |
| SYMPTOM | Joint pain, fatigue, rash | Patient notes, questionnaires |
| NOTE | Rheum visit note, discharge summary | Clinical documentation |
| IMAGING | X-ray, MRI, HRCT | Radiology reports |
| DECISION | Start biologic, hold MTX | Care plans, orders |
| RISK_FLAG | Infection risk, flare risk | EoH modules, guideline triggers |
| DIAGNOSIS | RA diagnosis, lupus suspicion | Problem list, encounters |

### Edge Types (Relationships)
| Type | Meaning | Example |
|------|---------|---------|
| TEMPORAL_SEQUENCE | A before B | Lab → Symptom (chronological) |
| TEMPORAL_WINDOW | A and B in same arc | Flare window events |
| CAUSAL_LIKELY | A caused B (strong) | MTX increase → AST elevation |
| CAUSAL_POSSIBLE | A may have caused B (weak) | Weather change → flare |
| REFERENCE | A mentions B | Note references prior lab |
| SIMILARITY | A ≈ B (features) | Two similar flare episodes |
| CONTRADICTION | A conflicts with B | RA dx vs. SLE suspicion |
| PROVENANCE | A derived from B | Flare flag from labs |
| CARE_PLAN_LINK | A part of plan from B | Treatment triggered by risk |
| COMPOSITE | A contains B | Flare episode contains labs |

### Traversal Operations
| Operation | Use Case | Edge Types |
|-----------|----------|-----------|
| **traverse_backward** | "Why?" (causality) | CAUSAL_LIKELY, PROVENANCE |
| **traverse_forward** | "What happened after?" | CAUSAL_LIKELY, TEMPORAL_SEQUENCE |
| **find_references** | "What mentions this?" | REFERENCE |
| **find_similar** | "Find similar episodes" | SIMILARITY |

---

## Architecture Comparison

### Before PTV (Flat Timeline)
```
┌────────────────────────────────────────────────────────────┐
│                  ehr.patient_timeline                      │
│  (Flat table with rows of events)                         │
└────────────────────────────────────────────────────────────┘
      ↓
  Implicit relationships (inferred by queries)
  No causality
  No provenance
  Modules create parallel stores
```

### After PTV (Knowledge Graph)
```
┌────────────────────────────────────────────────────────────┐
│               PatientTimelineVision                        │
│  (Knowledge graph with nodes + edges)                      │
│                                                            │
│  Nodes: Events with semantic annotations                  │
│  Edges: Typed relationships with confidence               │
│  Provenance: Full lineage of all transformations          │
└────────────────────────────────────────────────────────────┘
      ↑
  EoH modules stream INTO graph (no duplication)
  Agents traverse for reasoning
```

---

## How PTV Differs from Flat Timeline

| Aspect | Flat Timeline | PatientTimelineVision |
|--------|--------------|----------------------|
| **Structure** | Rows (chronological list) | Graph (nodes + typed edges) |
| **Relationships** | Implicit (inferred by time) | Explicit (typed edges with confidence) |
| **Causality** | Not represented | First-class CAUSAL edges |
| **Traversal** | Linear scan or time-range query | Multi-hop graph traversal (forward/backward) |
| **Provenance** | Source field only | Full DAG (track all transformations) |
| **Semantic Enrichment** | JSONB blob in meta field | Structured annotations indexed by module |
| **Embeddings** | Per-row (isolated context) | Graph-aware (neighbor context) |
| **Duplication** | Modules create parallel tables | Modules annotate shared graph |
| **Reasoning** | Query → retrieve → manual logic | Navigate → traverse → explain |
| **Auditability** | Minimal | Full (discovered_by on all nodes/edges) |

---

## Integration with Existing EoH System

### Current State (PRE-PTV)
- `ehr.patient_timeline` stores raw events
- EoH modules (M1-M50) compute features and store in:
  - Module-specific tables (`eoh.m1_terrain`, `eoh.m4_flare_signals`)
  - JSONB blobs in `patient_timeline.meta`
  - Separate embedding stores
- **Problem:** Duplication, no single source of truth, hard to trace provenance

### Target State (POST-PTV)
- `ehr.patient_timeline` remains as raw ingestion source
- **PatientTimelineVision is the authoritative graph**
- EoH modules **stream INTO** PTV by:
  1. Annotating existing nodes (add to `annotations` field)
  2. Creating new edges (e.g., M4 creates CAUSAL edges)
  3. Creating synthetic nodes (e.g., M5 creates RISK_FLAG nodes)
- All embeddings derive from PTV graph structure
- **Benefit:** Single source of truth, no duplication, full provenance

---

## Success Criteria

PatientTimelineVision will be successful if:

1. **Single Source of Truth:** All patient timeline data flows through PTV (no parallel stores)
2. **Explainable Decisions:** Every clinical decision can be explained by traversing the graph
3. **Efficient Traversal:** Multi-hop queries execute in <100ms for typical patient graphs
4. **Module Adoption:** All EoH modules (M1-M50) annotate PTV instead of creating separate tables
5. **Embedding Quality:** Graph-aware embeddings outperform flat timeline embeddings
6. **Agent Productivity:** LLM agents can navigate PTV to answer complex "why" questions without custom SQL
7. **Auditability:** Every annotation/edge includes provenance (which module, when, with what confidence)

---

## Implementation Timeline

**Total Duration:** 12-16 weeks (3-4 sprints)

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| **Phase 0: Pre-Implementation** | Week 0 | Stakeholder approval, storage backend choice |
| **Phase 1: Core Infrastructure** | Weeks 1-4 | Data models, PostgreSQL backend, EHR ingestion, traversal |
| **Phase 2: EoH Integration (Pilot)** | Weeks 5-8 | M1, M4, M22 integrated with PTV |
| **Phase 3: Explanation & Reasoning** | Weeks 9-10 | Explanation API, agent query patterns |
| **Phase 4: Remaining Modules** | Weeks 11-14 | All EoH modules migrated to PTV |
| **Phase 5: Production** | Weeks 15-16 | Optimization, monitoring, deployment |

**Target:** Production-ready PTV with 10+ patients by Week 16

---

## Next Steps

1. **Review & Approve Design** (This Week)
   - [ ] Engineering team review
   - [ ] Clinical stakeholder review
   - [ ] Leadership sign-off

2. **Technical Spike** (Next Week)
   - [ ] Benchmark PostgreSQL vs. Neo4j for graph queries
   - [ ] Identify 3 pilot patients (RA, SLE, complex multi-system)
   - [ ] Set up development environment

3. **Begin Phase 1** (Week 1)
   - [ ] Create core data models (`PatientEventVision`, `EventRelationship`)
   - [ ] Implement PostgreSQL schema
   - [ ] Start EHR ingestion pipeline

---

## References

### Design Documents (This Suite)
1. `PatientTimelineVision_Architecture.md` - Full technical specification
2. `PatientTimelineVision_QuickRef.md` - Developer quick reference
3. `PatientTimelineVision_UseCaseComparisons.md` - Before/after examples
4. `PatientTimelineVision_VisualGuide.md` - Visual diagrams and concepts
5. `PatientTimelineVision_Roadmap.md` - Implementation plan

### Related Systems
- **RepoVision:** `ai_code_pipelines/ai_probe/repo_vision.py` (inspiration)
- **EoH Router:** `server/eoh/router.py` (integration point)
- **EoH Modules:** `server/eoh/module_*.py` (will stream into PTV)
- **Timeline Schema:** `database/schemas/ehr_timeline.sql` (raw source)

### Key Architecture Principles
- **Inspired by:** RepoVision's approach to code understanding
- **Analogies:**
  - PTV:Patients :: RepoVision:Code
  - Clinical events :: Files in repo
  - Causal edges :: Import/reference edges
  - EoH modules :: Semantic enrichment agents
- **Novel contributions:**
  - Temporal relationships as first-class edges
  - Composite nodes (flare episodes, care arcs)
  - Multi-dimensional causality (likely, possible, provenance)

---

## FAQ

### Q1: Why not just use a generic knowledge graph (RDF, Neo4j)?
**A:** Generic KGs are overkill for this domain. PTV is purpose-built for patient timelines with:
- Native temporal support (timestamps, windows, sequences)
- Clinical event taxonomy (LAB, MED, SYMPTOM, etc.)
- EoH module integration (seamless annotation API)
- Python-first API (no need to learn SPARQL)

### Q2: How does PTV handle graph evolution (e.g., diagnosis changed)?
**A:** Future enhancement (Phase 6):
- Temporal versioning of nodes/edges
- Graph diffs to compare patient state over time
- Immutable history (never delete, only deprecate)

### Q3: What if two modules create contradictory edges?
**A:** CONTRADICTION edge type explicitly models conflicts:
- Both edges coexist (no deletion)
- Confidence scores help resolution
- Meta-calibration modules (M19, M48) flag inconsistencies

### Q4: Can PTV scale to 10,000 events per patient?
**A:** PostgreSQL will handle Phase 1-4 (up to ~5,000 events). For larger graphs:
- Phase 6 evaluates Neo4j migration (native graph DB)
- Caching layer for hot patients
- Graph partitioning strategies

### Q5: How do we ensure data privacy/security?
**A:** PTV inherits access controls from `ehr.patient_timeline`:
- Row-level security in PostgreSQL
- Graph traversal respects permissions (can't traverse to restricted events)
- Audit logs track all access

---

## Conclusion

PatientTimelineVision represents a **paradigm shift** from **passive data storage** to **active knowledge representation**. By treating clinical events as a traversable graph with explicit relationships, PTV enables:

- **Causal reasoning** that flat tables cannot support
- **Explainable AI** with full provenance
- **Agent productivity** through IDE-like navigation
- **Data integrity** via single source of truth

**This is not just a schema change—it's a new way of thinking about patient data.**

---

**Document Status:** ✅ Design Complete | ⏸️ Implementation Pending  
**Next Action:** Present to stakeholders for approval  
**Questions?** Contact the Systems Architecture Team

---

## Document Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-23 | Initial design suite complete (5 documents) |

**Total Documentation:** ~30,000 words, 5 comprehensive documents, 0 lines of code (design only)

**Ready for:** Stakeholder review → Technical spike → Phase 1 implementation

