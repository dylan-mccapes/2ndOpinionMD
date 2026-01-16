# PatientTimelineVision: Implementation Roadmap

**Status:** Design Complete, Implementation Pending  
**Estimated Timeline:** 12-16 weeks (3-4 sprints)  
**Target:** Production-ready PTV with EoH integration

---

## Phase 0: Pre-Implementation (Week 0)

### Objectives
- ✅ Architecture design complete
- ✅ Stakeholder review and sign-off
- ⏸️ Technical spike: PostgreSQL vs. Neo4j performance

### Tasks
- [ ] Present design to clinical + engineering teams
- [ ] Identify 2-3 pilot patients for prototype testing
- [ ] Choose storage backend (PostgreSQL for Phase 1, evaluate graph DB for Phase 2)
- [ ] Set up development environment

### Success Criteria
- [ ] Team consensus on architecture
- [ ] Storage backend chosen
- [ ] Pilot patients identified (diverse cases: RA, SLE, complex multi-system)

---

## Phase 1: Core Infrastructure (Weeks 1-4)

### Objectives
Build the foundational PTV system without EoH integration.

### Milestone 1.1: Core Data Models (Week 1)
```python
# Deliverables
- PatientEventVision dataclass
- EventRelationship dataclass
- PatientTimelineVision class (in-memory graph)
- EventType enum (LAB, MED, SYMPTOM, etc.)
- RelationshipType enum (CAUSAL_LIKELY, TEMPORAL_SEQUENCE, etc.)
```

**Tasks:**
- [ ] Create `server/ptv/models.py` with core dataclasses
- [ ] Write unit tests for node/edge creation
- [ ] Document node/edge schemas

**Acceptance Criteria:**
- [ ] Can create PatientEventVision nodes programmatically
- [ ] Can create EventRelationship edges programmatically
- [ ] 100% unit test coverage for models

### Milestone 1.2: PostgreSQL Storage Backend (Week 2)
```sql
-- Deliverables
CREATE TABLE ptv.patient_vision (...);
CREATE TABLE ptv.event_node (...);
CREATE TABLE ptv.event_edge (...);
-- Indexes for common query patterns
```

**Tasks:**
- [ ] Create `database/schemas/ptv_schema.sql`
- [ ] Implement `PatientTimelineVision.save()` method
- [ ] Implement `PatientTimelineVision.load()` method
- [ ] Add migrations to apply schema

**Acceptance Criteria:**
- [ ] Can persist graph to Postgres
- [ ] Can reload graph from Postgres
- [ ] Schema includes all required indexes
- [ ] Migration tested on dev database

### Milestone 1.3: EHR Timeline Ingestion (Week 3)
```python
# Deliverable
ptv = PatientTimelineVision.build_from_ehr_timeline(
    patient_id="DEMO_RA_001",
    ehr_timeline_source="ehr.patient_timeline"
)
```

**Tasks:**
- [ ] Implement `build_from_ehr_timeline()` method
- [ ] Map `ehr.patient_timeline` rows to PatientEventVision nodes
- [ ] Generate initial TEMPORAL_SEQUENCE edges based on timestamp order
- [ ] Handle edge cases (missing data, duplicate events, etc.)

**Acceptance Criteria:**
- [ ] Can ingest pilot patient timelines (3 patients)
- [ ] All events become nodes with correct event_type
- [ ] Temporal edges created between consecutive events
- [ ] No data loss (verify row count matches)

### Milestone 1.4: Basic Traversal Operations (Week 4)
```python
# Deliverables
ptv.find_events(event_type=EventType.LAB, time_range=(...))
ptv.find_edges(relationship_type=RelationshipType.CAUSAL_LIKELY)
ptv.traverse_forward(start_event_id, edge_types=[...], max_hops=3)
ptv.traverse_backward(start_event_id, edge_types=[...], max_hops=3)
```

**Tasks:**
- [ ] Implement `find_events()` with filtering
- [ ] Implement `find_edges()` with filtering
- [ ] Implement `traverse_forward()` (BFS/DFS)
- [ ] Implement `traverse_backward()` (BFS/DFS)
- [ ] Add query performance tests

**Acceptance Criteria:**
- [ ] Can query events by type, time, annotations
- [ ] Can traverse multi-hop paths forward/backward
- [ ] Traversal completes in <100ms for graphs with <1000 events
- [ ] Edge cases handled (cycles, dead ends, etc.)

### Phase 1 Exit Criteria
- [ ] PTV core models implemented and tested
- [ ] PostgreSQL backend functional
- [ ] EHR ingestion working for pilot patients
- [ ] Basic traversal operations functional
- [ ] No EoH integration yet (manual testing only)

---

## Phase 2: EoH Module Integration (Weeks 5-8)

### Objectives
Integrate 3 pilot EoH modules (M1, M4, M22) to validate annotation pattern.

### Milestone 2.1: Annotation API (Week 5)
```python
# Deliverable
ptv.annotate_event(
    event_id="evt_123",
    module_id="M4_FlareSignals",
    annotations={"flare_signal_strength": 0.85}
)

ptv.add_edge(EventRelationship(...))
```

**Tasks:**
- [ ] Implement `annotate_event()` method
- [ ] Implement `add_edge()` method with validation
- [ ] Add provenance tracking (`discovered_by` field)
- [ ] Create EoHModuleBase class with enrichment template

**Acceptance Criteria:**
- [ ] Modules can annotate existing nodes without duplication
- [ ] Modules can create new edges
- [ ] Provenance automatically tracked
- [ ] Validation prevents invalid edges (e.g., future → past causality)

### Milestone 2.2: M1 (Terrain) Integration (Week 5-6)
```python
# Deliverable
class M1_TerrainAnalysis(EoHModuleBase):
    def enrich_patient_vision(self, patient_id: str):
        # Annotate events with terrain_band, baseline_deviation
        # Create TEMPORAL_WINDOW edges
```

**Tasks:**
- [ ] Refactor M1 to read from PTV (not raw timeline)
- [ ] Annotate all events with `terrain_band`
- [ ] Create TEMPORAL_WINDOW edges for related events
- [ ] Deprecate old M1 output tables (keep for comparison)

**Acceptance Criteria:**
- [ ] M1 reads from PTV, not `ehr.patient_timeline`
- [ ] All events annotated with terrain data
- [ ] TEMPORAL_WINDOW edges created
- [ ] Results match old M1 output (validation)

### Milestone 2.3: M4 (Flare Signals) Integration (Week 6-7)
```python
# Deliverable
class M4_FlareSignals(EoHModuleBase):
    def enrich_patient_vision(self, patient_id: str):
        # Annotate labs/symptoms with flare_signal_strength
        # Create CAUSAL_LIKELY edges
```

**Tasks:**
- [ ] Refactor M4 to read from PTV
- [ ] Annotate labs/symptoms with flare_signal_strength
- [ ] Create CAUSAL_LIKELY edges between signals and outcomes
- [ ] Compare results to old M4 output

**Acceptance Criteria:**
- [ ] M4 annotates flare signals in PTV
- [ ] CAUSAL edges created with confidence scores
- [ ] Results comparable to old M4 (within 10% deviation)

### Milestone 2.4: M22 (Care Planning) Integration (Week 7-8)
```python
# Deliverable
class M22_CarePlanning(EoHModuleBase):
    def enrich_patient_vision(self, patient_id: str):
        # Create DECISION nodes for care plan events
        # Create CARE_PLAN_LINK edges
```

**Tasks:**
- [ ] Refactor M22 to read from PTV
- [ ] Create DECISION nodes for treatment changes
- [ ] Create CARE_PLAN_LINK and PROVENANCE edges
- [ ] Compare results to old M22 output

**Acceptance Criteria:**
- [ ] M22 creates DECISION nodes in PTV
- [ ] Care plan edges link decisions to triggers
- [ ] Results comparable to old M22

### Phase 2 Exit Criteria
- [ ] 3 pilot modules (M1, M4, M22) integrated with PTV
- [ ] All modules use `annotate_event()` and `add_edge()` APIs
- [ ] No new module-specific tables created
- [ ] Results validated against old module outputs
- [ ] Documentation updated with integration examples

---

## Phase 3: Explanation & Reasoning (Weeks 9-10)

### Objectives
Build explanation engine and agent-facing APIs.

### Milestone 3.1: Explanation Generation (Week 9)
```python
# Deliverable
explanation = ptv.generate_explanation(
    decision_event_id="evt_biologic_start",
    include_module_provenance=True,
    max_causal_depth=3
)
```

**Tasks:**
- [ ] Implement `generate_explanation()` method
- [ ] Traverse backward through causal/provenance edges
- [ ] Format explanation with confidence scores and module provenance
- [ ] Add unit tests for various explanation scenarios

**Acceptance Criteria:**
- [ ] Can explain clinical decisions by traversing graph
- [ ] Explanations include confidence scores
- [ ] Explanations cite modules (M1, M4, etc.)
- [ ] Readable by clinicians (not raw JSON)

### Milestone 3.2: Agent Query Patterns (Week 10)
```python
# Deliverables
def answer_why_question(question: str, patient_id: str) -> str:
    # "Why was MTX increased?" → traverse backward

def answer_what_if_question(question: str, patient_id: str) -> str:
    # "What if we stop MTX?" → traverse forward from synthetic node
```

**Tasks:**
- [ ] Create `server/ptv/agent_queries.py` with query patterns
- [ ] Implement "why" questions (backward causal traversal)
- [ ] Implement "what happened after" questions (forward traversal)
- [ ] Integrate with existing RAG/LLM pipeline

**Acceptance Criteria:**
- [ ] Agents can answer "why" questions via PTV
- [ ] Agents can answer "what happened" questions via PTV
- [ ] Explanations include provenance
- [ ] Performance: <200ms for typical queries

### Phase 3 Exit Criteria
- [ ] Explanation API functional
- [ ] Agent query patterns implemented
- [ ] Integration with RAG pipeline complete
- [ ] Documentation with example queries

---

## Phase 4: Remaining EoH Modules (Weeks 11-14)

### Objectives
Migrate all remaining EoH modules (M5, M7A, M13, etc.) to PTV.

### Milestone 4.1: M5 (Flare Windowing) + M13 (Diagnostic Landscape) (Week 11-12)
**Tasks:**
- [ ] Refactor M5 to create COMPOSITE nodes for flare episodes
- [ ] Refactor M13 to annotate DIAGNOSIS nodes with landscape data
- [ ] Create SIMILARITY edges between similar episodes

**Acceptance Criteria:**
- [ ] M5 creates flare episode composite nodes
- [ ] M13 annotates diagnostic landscape
- [ ] SIMILARITY edges between related diagnoses

### Milestone 4.2: M7A (Prognostics) + M19 (Calibration) (Week 13)
**Tasks:**
- [ ] Refactor M7A to annotate risk profiles
- [ ] Refactor M19 to add meta-calibration annotations

**Acceptance Criteria:**
- [ ] M7A annotates risk predictions
- [ ] M19 tracks calibration metrics

### Milestone 4.3: Remaining Modules (Week 14)
**Tasks:**
- [ ] Migrate M24, M25, M41, M48, M50, etc.
- [ ] Deprecate old module-specific tables

**Acceptance Criteria:**
- [ ] All EoH modules read from PTV
- [ ] All modules annotate PTV (no parallel stores)
- [ ] Old tables marked deprecated

### Phase 4 Exit Criteria
- [ ] All EoH modules migrated to PTV
- [ ] No module-specific tables in use
- [ ] Module outputs validated
- [ ] Performance acceptable (module enrichment <5 min per patient)

---

## Phase 5: Optimization & Production (Weeks 15-16)

### Objectives
Optimize performance, add monitoring, prepare for production.

### Milestone 5.1: Performance Optimization (Week 15)
**Tasks:**
- [ ] Profile slow queries (traversal, annotation lookups)
- [ ] Add indexes for common patterns
- [ ] Evaluate caching strategy (Redis for hot graphs?)
- [ ] Benchmark against flat timeline queries

**Acceptance Criteria:**
- [ ] Traversal queries <100ms for typical patient graphs
- [ ] Explanation generation <200ms
- [ ] Ingestion <30s per patient
- [ ] Module enrichment <5 min per patient

### Milestone 5.2: Monitoring & Observability (Week 15-16)
**Tasks:**
- [ ] Add logging for PTV operations (build, enrich, query)
- [ ] Create metrics dashboard (graph size, edge counts, query latency)
- [ ] Add alerts for anomalies (missing edges, low confidence scores)

**Acceptance Criteria:**
- [ ] Logs track all PTV operations
- [ ] Metrics visible in monitoring dashboard
- [ ] Alerts configured for critical issues

### Milestone 5.3: Documentation & Training (Week 16)
**Tasks:**
- [ ] Update developer documentation with PTV APIs
- [ ] Create clinician-facing guide to graph concepts
- [ ] Record demo videos (traversal, explanation, agent queries)
- [ ] Conduct team training session

**Acceptance Criteria:**
- [ ] Documentation complete and reviewed
- [ ] Team trained on PTV concepts
- [ ] Demo videos available

### Milestone 5.4: Production Rollout (Week 16)
**Tasks:**
- [ ] Deploy PTV schema to production database
- [ ] Ingest 10 pilot patients
- [ ] Enable PTV for RAG pipeline (feature flag)
- [ ] Monitor for issues

**Acceptance Criteria:**
- [ ] PTV deployed to production
- [ ] 10 patients successfully ingested and enriched
- [ ] No critical issues in first week
- [ ] Performance meets SLAs

### Phase 5 Exit Criteria
- [ ] PTV in production with 10+ patients
- [ ] Performance optimized
- [ ] Monitoring and alerts in place
- [ ] Team trained and documentation complete

---

## Post-Production: Phase 6 (Future)

### Objectives
Evaluate graph database migration and scale to full patient population.

### Potential Enhancements
- [ ] Migrate to Neo4j/ArangoDB for native graph queries
- [ ] Implement real-time streaming (events flow into PTV on ingestion)
- [ ] Build clinician-facing graph visualization UI
- [ ] Add graph diffing (compare patient graphs over time)
- [ ] Implement federated learning over patient graphs

---

## Risk Mitigation

### Risk 1: Performance Degradation (Postgres not optimized for graphs)
**Mitigation:**
- Start with Postgres (familiar, low risk)
- Profile early and often
- Keep Neo4j evaluation parallel (can migrate later)
- Implement caching for hot graphs

### Risk 2: Module Integration Complexity (EoH modules tightly coupled to old schema)
**Mitigation:**
- Start with 3 pilot modules (M1, M4, M22)
- Create EoHModuleBase template to standardize integration
- Migrate modules incrementally (1-2 per week)
- Keep old tables during transition for validation

### Risk 3: Data Loss or Corruption During Migration
**Mitigation:**
- Run ingestion in parallel (don't delete old data)
- Validate results against old outputs
- Use feature flags to enable PTV gradually
- Keep rollback plan (revert to flat timeline if critical issue)

### Risk 4: Clinician Adoption (Graph concepts unfamiliar)
**Mitigation:**
- Create visual guides (see `PatientTimelineVision_VisualGuide.md`)
- Frame as "IDE for patient data" (familiar to developers)
- Show concrete use cases (explanation, causal reasoning)
- Provide training and demos

---

## Success Metrics (Phase 1-5)

| Metric | Baseline (Flat) | Target (PTV) | Measurement |
|--------|----------------|--------------|-------------|
| **Explanation Quality** | Manual reasoning, no provenance | Automatic with provenance | Clinician survey (1-10 scale) |
| **Query Latency** | 50-200ms (SQL) | <100ms (graph traversal) | Benchmark suite |
| **Module Integration** | 12 module-specific tables | 0 (all annotate PTV) | Table count |
| **Agent Productivity** | 5 min per "why" question | <30 sec per question | Time tracking |
| **Causal Clarity** | Implicit (guessing) | Explicit edges with confidence | Edge coverage metric |
| **Auditability** | Minimal provenance | Full discovered_by tracking | Audit log completeness |

---

## Resource Requirements

### Engineering
- **Backend Engineer (Lead):** 100% for Weeks 1-16
- **Backend Engineer (Support):** 50% for Weeks 5-14 (module integration)
- **Data Engineer:** 25% for Weeks 1-4 (schema design, ingestion)

### Clinical
- **Clinical Informaticist:** 10% for Weeks 0-16 (review, validation)
- **Rheumatologist (SME):** 5% for Weeks 0, 8, 16 (design review, validation, training)

### Infrastructure
- **DevOps:** 10% for Weeks 2, 15, 16 (schema deployment, monitoring)

---

## Decision Points

### End of Phase 1 (Week 4)
**Question:** Is PostgreSQL performance acceptable for pilot patients?
- **Yes:** Continue to Phase 2
- **No:** Evaluate Neo4j migration (adds 2-3 weeks)

### End of Phase 2 (Week 8)
**Question:** Do pilot modules (M1, M4, M22) integrate smoothly?
- **Yes:** Continue to Phase 4 (migrate all modules)
- **No:** Refine annotation API, re-test pilot modules

### End of Phase 4 (Week 14)
**Question:** Are all modules migrated and validated?
- **Yes:** Proceed to production rollout
- **No:** Extend timeline, prioritize critical modules

---

## Communication Plan

### Weekly Updates
- **Audience:** Engineering team
- **Format:** Slack + weekly standup
- **Content:** Progress, blockers, next steps

### Bi-Weekly Demos
- **Audience:** Product + Clinical stakeholders
- **Format:** Live demo + slides
- **Content:** New capabilities, use cases, validation results

### Milestone Reviews
- **Audience:** Leadership (CTO, CMO, CEO)
- **Format:** Presentation + written report
- **Timing:** End of Phases 1, 2, 4, 5

---

## Conclusion

PatientTimelineVision is a **12-16 week journey** from design to production. By following this phased approach:

1. **Phase 1:** Build core infrastructure (4 weeks)
2. **Phase 2:** Validate with pilot modules (4 weeks)
3. **Phase 3:** Add explanation/reasoning (2 weeks)
4. **Phase 4:** Migrate all modules (4 weeks)
5. **Phase 5:** Optimize and deploy (2 weeks)

We'll transform 2ndOpinionMD's patient data from a **flat timeline** into a **semantically rich knowledge graph** that enables IDE-like traversal, causal reasoning, and explainable AI decisions.

**Next Step:** Present this roadmap to stakeholders for approval and resource allocation.

---

**Document Status:** ✅ Roadmap Complete | ⏸️ Pending Approval

