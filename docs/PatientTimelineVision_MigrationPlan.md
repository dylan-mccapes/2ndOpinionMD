# PatientTimelineVision Migration Plan

## Executive Summary

This document outlines the migration strategy from the existing `ehr.patient_timeline` + scattered risk logic to **PatientTimelineVision (PTV)** and **PatientRiskVision (PRV)**.

**Core Principles:**
- ✅ Zero duplicate computation
- ✅ Existing EoH modules continue to function
- ✅ Gradual cutover with feature flags
- ✅ Clear rollback at every phase
- ✅ Continuous validation against current system

**Timeline:** 12-16 weeks across 5 phases

---

## Current System Analysis

### What Exists Today

```
┌─────────────────────────────────────────────────────────────┐
│                     CURRENT SYSTEM                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ehr.patient_timeline (flat table)                          │
│  ├─ event_type, event_subtype, ts, structured, text        │
│  ├─ embedding (BYTEA, monolithic)                           │
│  └─ meta (JSONB, unstructured)                              │
│                                                             │
│  EoH Modules (direct table access)                          │
│  ├─ TerrainAnalysis → reads timeline, writes meta           │
│  ├─ FlareSignals → reads timeline, writes meta              │
│  ├─ FlareWindowing → reads timeline, aggregates             │
│  └─ CarePlanning → reads timeline + meta                    │
│                                                             │
│  Risk Logic (scattered)                                     │
│  ├─ Computed on-the-fly in queries                          │
│  ├─ Cached in application layer                             │
│  └─ No audit trail or trajectory                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Pain Points Being Solved

| Problem | Current State | PTV Solution |
|---------|---------------|--------------|
| **No provenance** | Meta fields with no source tracking | Graph edges with `discovered_by` |
| **No causality** | Temporal ordering only | Explicit CAUSAL edges |
| **Hallucination risk** | Embeddings divorced from data | Embeddings reference graph nodes |
| **Risk drift** | Computed values with no audit | Immutable risk snapshots + trajectory |
| **No traversal** | SQL joins only | IDE-like graph navigation |
| **Duplicate computation** | Modules recompute same insights | Cached derived nodes in graph |

---

## Migration Phases

### Phase 0: Pre-Migration (Week 0)

**Goal:** Set up parallel infrastructure without touching production

**Actions:**
1. Deploy PTV schema alongside existing tables
2. Create feature flag: `PTV_ENABLED` (default: `false`)
3. Add monitoring for PTV builder performance
4. Create validation framework

**Deliverables:**
```sql
-- Feature flag table
CREATE TABLE system.feature_flags (
    flag_name TEXT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT false,
    config JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO system.feature_flags (flag_name, enabled, config)
VALUES 
    ('PTV_ENABLED', false, '{"mode": "shadow"}'),
    ('PTV_WRITES_ENABLED', false, '{}'),
    ('PTV_READS_ENABLED', false, '{}');
```

**Rollback:** Drop PTV schema, no production impact

**Validation:** Schema deployment successful, no existing queries affected

---

### Phase 1: Shadow Mode (Weeks 1-3)

**Goal:** Build PTV graph in parallel, compare outputs, zero production impact

**Actions:**

1. **Deploy PTV Builder in Shadow Mode**
   ```python
   # In existing timeline ingestion pipeline
   from server.ptv.builder import PatientTimelineVisionOrchestrator
   
   async def ingest_timeline_event(event):
       # EXISTING: Write to ehr.patient_timeline
       await insert_timeline_event(event)
       
       # NEW: Shadow write to PTV (async, non-blocking)
       if feature_flags.is_enabled("PTV_ENABLED"):
           asyncio.create_task(
               ptv_orchestrator.build_and_enrich(
                   patient_id=event.patient_id,
                   mode="shadow"
               )
           )
   ```

2. **Run Nightly Validation**
   ```python
   # Compare PTV graph to current system outputs
   async def validate_ptv_completeness(patient_id):
       # Check 1: All timeline events have corresponding nodes
       timeline_events = await fetch_timeline_events(patient_id)
       ptv_nodes = await fetch_ptv_nodes(patient_id)
       assert len(timeline_events) == len(ptv_nodes)
       
       # Check 2: Derived insights match existing meta fields
       existing_insights = extract_insights_from_meta(timeline_events)
       ptv_insights = await fetch_derived_insights(patient_id)
       assert insights_match(existing_insights, ptv_insights)
       
       # Check 3: Temporal ordering preserved
       assert temporal_order_matches(timeline_events, ptv_nodes)
   ```

3. **Deploy EoH Adapter Layer**
   ```python
   # Adapters allow EoH modules to work with EITHER system
   class TimelineAdapter:
       """Abstraction layer for EoH modules during migration"""
       
       def __init__(self):
           self.use_ptv = feature_flags.is_enabled("PTV_READS_ENABLED")
       
       async def get_patient_events(self, patient_id, event_type=None):
           if self.use_ptv:
               return await self._get_from_ptv(patient_id, event_type)
           else:
               return await self._get_from_timeline(patient_id, event_type)
       
       async def _get_from_timeline(self, patient_id, event_type):
           # Existing logic
           return await db.fetch(
               "SELECT * FROM ehr.patient_timeline WHERE patient_id = $1",
               patient_id
           )
       
       async def _get_from_ptv(self, patient_id, event_type):
           # New graph-based logic
           from server.ptv.query import PatientTimelineQuery
           return await PatientTimelineQuery(patient_id).get_events(
               node_type=event_type
           )
   ```

**What Gets Created:**
- ✅ PTV graph (parallel, read-only for validation)
- ✅ Adapter interfaces for all EoH modules
- ✅ Validation reports (nightly)

**What Stays Unchanged:**
- ✅ Production queries still use `ehr.patient_timeline`
- ✅ EoH modules still write to existing tables
- ✅ Risk computation still uses old logic

**Rollback:** Set `PTV_ENABLED=false`, shadow writes stop, zero impact

**Success Criteria:**
- [ ] 100% of timeline events successfully create PTV nodes
- [ ] PTV graph build time < 5s per patient (p95)
- [ ] Zero validation errors for 7 consecutive days
- [ ] No production latency impact

---

### Phase 2: Read Cutover (Weeks 4-7)

**Goal:** Migrate read queries to PTV graph, writes still dual

**Actions:**

1. **Enable PTV Reads for Non-Critical Paths**
   ```python
   # Start with low-risk read queries
   # Example: Patient summary view (non-critical)
   
   # BEFORE:
   timeline = await db.fetch(
       "SELECT * FROM ehr.patient_timeline WHERE patient_id = $1",
       patient_id
   )
   
   # AFTER (with feature flag):
   if feature_flags.is_enabled("PTV_READS_ENABLED"):
       from server.ptv.query import PatientTimelineQuery
       timeline = await PatientTimelineQuery(patient_id).get_all_events()
   else:
       timeline = await db.fetch(...)  # Fallback
   ```

2. **Migrate EoH Modules to Adapter (One at a Time)**
   ```python
   # Week 4: Migrate TerrainAnalysis
   class TerrainAnalysisHook(EnrichmentHook):
       async def enrich(self, patient_id, node):
           if node.node_type == NodeType.LAB_RESULT:
               # NEW: Write directly to PTV graph
               trend = self._compute_trend(node)
               await self.create_derived_node(
                   node_type=NodeType.DERIVED_INSIGHT,
                   content={"insight_type": "terrain_trend", "value": trend},
                   source_node_ids=[node.id]
               )
   
   # Week 5: Migrate FlareSignals
   # Week 6: Migrate FlareWindowing
   # Week 7: Migrate CarePlanning
   ```

3. **Dual Write to Both Systems**
   ```python
   async def ingest_timeline_event(event):
       # Write to BOTH systems (ensuring idempotency)
       async with transaction():
           # Old system
           await insert_timeline_event(event)
           
           # New system
           if feature_flags.is_enabled("PTV_WRITES_ENABLED"):
               await ptv_builder.build_patient_vision(
                   patient_id=event.patient_id,
                   force_rebuild=False  # Only add new events
               )
   ```

**Module Migration Order:**
1. **Week 4:** TerrainAnalysis (lowest risk, well-defined outputs)
2. **Week 5:** FlareSignals (moderate complexity)
3. **Week 6:** FlareWindowing (depends on FlareSignals)
4. **Week 7:** CarePlanning (depends on all others)

**Rollback Strategy:**
- **Per-module rollback:** Disable specific adapter, module reverts to old tables
- **Full rollback:** Set `PTV_READS_ENABLED=false`, all modules revert
- **Data safety:** Dual writes mean no data loss on rollback

**Success Criteria:**
- [ ] All EoH modules migrated to adapter pattern
- [ ] Read latency from PTV ≤ old system (p95)
- [ ] Zero functional regressions (validated by integration tests)
- [ ] 30-day burn-in with no incidents

---

### Phase 3: Risk Migration (Weeks 8-10)

**Goal:** Migrate risk computation to PatientRiskVision (PRV)

**Actions:**

1. **Deploy PRV Schema**
   ```sql
   -- PatientRiskVision tables (from PatientRiskVision_Architecture.md)
   CREATE SCHEMA IF NOT EXISTS prv;
   CREATE TABLE prv.risk_snapshot (...);
   CREATE TABLE prv.risk_trajectory (...);
   CREATE TABLE prv.risk_alert (...);
   ```

2. **Backfill Risk Snapshots**
   ```python
   # One-time backfill: Convert existing risk state to PRV
   async def backfill_risk_snapshots():
       patients = await fetch_all_patients()
       for patient in patients:
           # Compute current risk using PTV graph
           risk_snapshot = await compute_initial_risk_from_ptv(patient.id)
           await insert_risk_snapshot(risk_snapshot)
   ```

3. **Dual Risk Computation**
   ```python
   # Compute risk in BOTH systems, compare outputs
   async def compute_patient_risk(patient_id):
       # Old system
       old_risk = await compute_risk_legacy(patient_id)
       
       # New system (PRV)
       if feature_flags.is_enabled("PRV_ENABLED"):
           new_risk = await compute_risk_from_ptv(patient_id)
           
           # Validate match
           if not risks_match(old_risk, new_risk):
               log_risk_mismatch(patient_id, old_risk, new_risk)
       
       return old_risk  # Still return old risk (safe)
   ```

4. **Cutover Risk Reads**
   ```python
   # After validation, switch to PRV as source of truth
   async def get_patient_risk(patient_id):
       if feature_flags.is_enabled("PRV_READS_ENABLED"):
           return await fetch_latest_risk_snapshot(patient_id)
       else:
           return await compute_risk_legacy(patient_id)
   ```

**Rollback:**
- **Risk reads:** Set `PRV_READS_ENABLED=false`
- **Risk writes:** PRV snapshots are append-only, old system unaffected
- **Worst case:** Recompute risk from old system, PRV ignored

**Success Criteria:**
- [ ] PRV risk snapshots match legacy risk for 95% of patients
- [ ] Mismatch cases documented and explainable
- [ ] Risk trajectory correctly captures historical changes
- [ ] Alert system functional and tested

---

### Phase 4: Write Cutover (Weeks 11-13)

**Goal:** Stop writing to old tables, PTV becomes primary

**Actions:**

1. **Make PTV Primary Write Target**
   ```python
   async def ingest_timeline_event(event):
       # NEW: PTV is primary
       node = await ptv_builder.build_patient_vision(
           patient_id=event.patient_id
       )
       
       # DEPRECATED: Shadow write to old table (for rollback safety)
       if feature_flags.is_enabled("LEGACY_TIMELINE_WRITES"):
           await insert_timeline_event_legacy(event)
   ```

2. **Stop EoH Modules from Writing to Old Tables**
   ```python
   # Remove all direct writes to ehr.patient_timeline.meta
   # All insights now go through PTV graph as derived nodes
   
   # BEFORE:
   await db.execute(
       "UPDATE ehr.patient_timeline SET meta = $1 WHERE id = $2",
       meta, event_id
   )
   
   # AFTER: DELETED (insights are now graph nodes)
   ```

3. **Create Legacy Read Adapter**
   ```python
   # For any remaining code that reads ehr.patient_timeline directly
   class LegacyTimelineReader:
       """Read-only adapter for legacy code"""
       
       async def fetch_timeline(self, patient_id):
           # Redirect to PTV
           from server.ptv.query import PatientTimelineQuery
           nodes = await PatientTimelineQuery(patient_id).get_all_events()
           
           # Transform to legacy format
           return [self._node_to_legacy_row(n) for n in nodes]
       
       def _node_to_legacy_row(self, node):
           """Convert PTV node to old timeline row format"""
           return {
               "id": int(node.id.split("-")[1]),  # Extract sequence
               "patient_id": node.patient_id,
               "ts": node.timestamp,
               "event_type": node.event_type,
               "structured": node.content,
               "text": node.content.get("text", ""),
               "meta": self._extract_meta_from_graph(node)
           }
   ```

**What Gets Deprecated:**
- ❌ Direct writes to `ehr.patient_timeline.meta`
- ❌ Direct writes to `ehr.patient_timeline.embedding`
- ❌ On-the-fly risk computation

**What Becomes Adapters:**
- 🔄 Legacy reads from `ehr.patient_timeline` (redirected to PTV)
- 🔄 Any code expecting flat timeline format

**Rollback:**
- **Full write rollback:** Set `PTV_ENABLED=false`, revert to old ingest pipeline
- **Data recovery:** Old tables still have shadow writes for 30 days
- **Timeline:** Can roll back for up to 30 days post-cutover

**Success Criteria:**
- [ ] Zero writes to `ehr.patient_timeline` for non-rollback purposes
- [ ] All EoH modules exclusively use PTV graph
- [ ] Legacy read adapter handles 100% of edge cases
- [ ] 14-day burn-in with no rollbacks needed

---

### Phase 5: Deprecation & Cleanup (Weeks 14-16)

**Goal:** Remove legacy system, finalize PTV as sole source of truth

**Actions:**

1. **Archive Old Timeline Data**
   ```sql
   -- Move old data to archive schema
   CREATE SCHEMA IF NOT EXISTS archive;
   
   CREATE TABLE archive.patient_timeline_legacy AS
   SELECT * FROM ehr.patient_timeline;
   
   -- Add archive metadata
   ALTER TABLE archive.patient_timeline_legacy
   ADD COLUMN archived_at TIMESTAMPTZ DEFAULT NOW(),
   ADD COLUMN archive_reason TEXT DEFAULT 'Migrated to PTV';
   ```

2. **Drop Legacy Indexes**
   ```sql
   -- Remove indexes from old table (save storage)
   DROP INDEX IF EXISTS ehr.patient_timeline_patient_ts_idx;
   DROP INDEX IF EXISTS ehr.patient_timeline_event_type_idx;
   DROP INDEX IF EXISTS ehr.patient_timeline_embedding_idx;
   ```

3. **Remove Feature Flags**
   ```python
   # Delete feature flags (all behavior now default to PTV)
   DELETE FROM system.feature_flags 
   WHERE flag_name IN ('PTV_ENABLED', 'PTV_READS_ENABLED', 'PTV_WRITES_ENABLED');
   ```

4. **Remove Adapter Code**
   ```python
   # Delete TimelineAdapter, LegacyTimelineReader
   # Update all imports to use PTV directly
   
   # BEFORE:
   from server.adapters import TimelineAdapter
   timeline = await TimelineAdapter().get_patient_events(patient_id)
   
   # AFTER:
   from server.ptv.query import PatientTimelineQuery
   timeline = await PatientTimelineQuery(patient_id).get_all_events()
   ```

5. **Update Documentation**
   - Mark `ehr.patient_timeline` as deprecated in schema docs
   - Update all API docs to reference PTV
   - Create migration guide for any external consumers

**What Gets Deleted:**
- ❌ `TimelineAdapter` and all adapter classes
- ❌ Feature flags for PTV/PRV
- ❌ Legacy risk computation functions
- ❌ Shadow write logic

**What Gets Archived:**
- 📦 `ehr.patient_timeline` → `archive.patient_timeline_legacy`
- 📦 Old risk computation code (tagged in git)
- 📦 Migration scripts (for future reference)

**Rollback:**
- **Not possible beyond this phase**
- **Mitigation:** Keep archive tables for 12 months for emergency data recovery

**Success Criteria:**
- [ ] Zero references to `ehr.patient_timeline` in active code
- [ ] Archive tables validated and accessible
- [ ] All documentation updated
- [ ] System running on PTV for 60+ days with no issues

---

## Risk Analysis & Mitigations

### Risk 1: Performance Regression

**Likelihood:** Medium  
**Impact:** High  

**Concern:** Graph queries slower than flat table queries

**Mitigation:**
- ✅ **Phase 1:** Benchmark PTV queries vs SQL queries (target: ≤ 1.2x latency)
- ✅ **Phase 2:** Implement caching layer for hot paths
- ✅ **Phase 3:** Add database indexes on frequently traversed edges
- ✅ **Monitoring:** Track p50, p95, p99 latencies for all query types

**Rollback Trigger:**
- If p95 latency > 2x old system for 3 consecutive days → rollback to previous phase

---

### Risk 2: Data Loss During Migration

**Likelihood:** Low  
**Impact:** Critical  

**Concern:** Events lost during dual-write cutover

**Mitigation:**
- ✅ **Dual writes:** Both systems updated atomically in transaction
- ✅ **Validation:** Nightly job compares event counts
- ✅ **Idempotency:** PTV builder never duplicates nodes
- ✅ **Audit log:** All PTV writes logged to separate audit table

```python
# Atomic dual write
async def ingest_event_safe(event):
    async with db.transaction():
        old_id = await insert_timeline_event(event)
        new_node = await ptv_builder.ingest_event(event)
        
        # Log for validation
        await audit_log.record_dual_write(
            old_id=old_id,
            new_node_id=new_node.id,
            timestamp=now()
        )
```

**Rollback Trigger:**
- If any validation job detects missing events → halt migration, investigate

---

### Risk 3: EoH Module Breakage

**Likelihood:** Medium  
**Impact:** Medium  

**Concern:** Modules fail after adapter migration

**Mitigation:**
- ✅ **Gradual rollout:** Migrate one module per week
- ✅ **Adapter pattern:** Modules work with EITHER system during transition
- ✅ **Integration tests:** Run full test suite after each module migration
- ✅ **Canary patients:** Test migrated modules on 5% of patients first

```python
# Integration test for migrated module
async def test_terrain_analysis_ptv():
    patient_id = "test_patient_001"
    
    # Compute using OLD system
    old_result = await terrain_analysis_legacy(patient_id)
    
    # Compute using NEW system (PTV)
    new_result = await terrain_analysis_ptv(patient_id)
    
    # Results must match
    assert old_result.trend == new_result.trend
    assert old_result.trajectory == new_result.trajectory
```

**Rollback Trigger:**
- If module integration tests fail → revert module to old adapter

---

### Risk 4: Risk Computation Mismatch

**Likelihood:** Medium  
**Impact:** High  

**Concern:** PRV risk scores differ from legacy risk

**Mitigation:**
- ✅ **Dual computation:** Run both systems in parallel for 2 weeks (Phase 3)
- ✅ **Mismatch analysis:** For every mismatch, determine root cause
- ✅ **Acceptable variance:** Define thresholds (e.g., ±5% is acceptable for risk scores)
- ✅ **Clinical validation:** Medical team reviews sample of mismatches

**Rollback Trigger:**
- If >10% of patients have unexplained risk mismatches → halt PRV migration

---

### Risk 5: Embedding Provenance Loss

**Likelihood:** Low  
**Impact:** Medium  

**Concern:** Old embeddings not linkable to PTV nodes

**Mitigation:**
- ✅ **Embedding migration:** Recompute embeddings from PTV graph
- ✅ **Phased approach:** Backfill embeddings in Phase 2 (non-blocking)
- ✅ **Fallback:** Keep old embeddings for 90 days as reference

```python
# Backfill embeddings from PTV
async def backfill_embeddings(patient_id):
    nodes = await fetch_ptv_nodes(patient_id)
    for node in nodes:
        if node.node_type in EMBEDDABLE_TYPES:
            embedding = await compute_embedding_from_node(node)
            await store_node_embedding(node.id, embedding)
```

---

### Risk 6: Rollback Data Inconsistency

**Likelihood:** Low  
**Impact:** Medium  

**Concern:** Rolling back causes data divergence between systems

**Mitigation:**
- ✅ **Shadow writes:** Old system always up-to-date for 30 days post-cutover
- ✅ **Immutability:** PTV is append-only, old data never changes
- ✅ **Reconciliation script:** Can rebuild PTV from old tables if needed

```python
# Emergency reconciliation
async def reconcile_ptv_from_legacy(patient_id):
    """Rebuild PTV graph from legacy timeline (rollback scenario)"""
    legacy_events = await fetch_legacy_timeline(patient_id)
    
    # Delete PTV nodes (emergency only)
    await delete_ptv_nodes(patient_id)
    
    # Rebuild from scratch
    for event in legacy_events:
        await ptv_builder.ingest_event(event)
```

---

## Validation Strategy

### Continuous Validation (All Phases)

```python
class MigrationValidator:
    """Runs continuously during migration"""
    
    async def validate_completeness(self, patient_id):
        """Ensure no events lost"""
        legacy_count = await count_legacy_events(patient_id)
        ptv_count = await count_ptv_nodes(patient_id, node_type=NodeType.RAW_EVENT)
        
        if legacy_count != ptv_count:
            raise ValidationError(f"Event count mismatch: {legacy_count} vs {ptv_count}")
    
    async def validate_insights(self, patient_id):
        """Ensure derived insights match"""
        legacy_insights = await extract_insights_from_meta(patient_id)
        ptv_insights = await fetch_derived_insights(patient_id)
        
        for key, legacy_value in legacy_insights.items():
            if key not in ptv_insights:
                raise ValidationError(f"Missing insight: {key}")
            
            if not values_match(legacy_value, ptv_insights[key]):
                raise ValidationError(f"Insight mismatch for {key}")
    
    async def validate_risk(self, patient_id):
        """Ensure risk scores match"""
        legacy_risk = await compute_risk_legacy(patient_id)
        prv_risk = await fetch_latest_risk_snapshot(patient_id)
        
        if abs(legacy_risk.score - prv_risk.overall_score) > 0.05:
            raise ValidationError(f"Risk mismatch: {legacy_risk.score} vs {prv_risk.overall_score}")
    
    async def validate_performance(self):
        """Ensure no regressions"""
        ptv_latency = await measure_query_latency("ptv")
        legacy_latency = await measure_query_latency("legacy")
        
        if ptv_latency > legacy_latency * 1.5:
            raise ValidationError(f"Performance regression: {ptv_latency}ms vs {legacy_latency}ms")
```

### Validation Schedule

| Phase | Validation Frequency | Validation Scope |
|-------|---------------------|------------------|
| **Phase 1** (Shadow) | Every 6 hours | All patients, all checks |
| **Phase 2** (Read) | Every 12 hours | Migrated modules only |
| **Phase 3** (Risk) | Daily | Risk snapshots + trajectories |
| **Phase 4** (Write) | Daily | Write consistency |
| **Phase 5** (Cleanup) | Weekly | Archive integrity |

---

## Rollback Decision Tree

```
┌─────────────────────────────────────────────────────────────┐
│                    ISSUE DETECTED                           │
└───────────────┬─────────────────────────────────────────────┘
                │
                ▼
        ┌───────────────┐      Yes
        │ Data Loss?    │──────────► IMMEDIATE ROLLBACK
        └───────┬───────┘            (to previous phase)
                │ No
                ▼
        ┌───────────────┐      Yes
        │ Performance   │──────────► Investigate
        │ >2x slower?   │            ├─ Fixable in 24h? → Continue
        └───────┬───────┘            └─ Not fixable? → ROLLBACK
                │ No
                ▼
        ┌───────────────┐      Yes
        │ Functional    │──────────► Investigate
        │ Regression?   │            ├─ Affects <5% users? → Hot-fix
        └───────┬───────┘            └─ Affects >5%? → ROLLBACK
                │ No
                ▼
        ┌───────────────┐
        │ Continue      │
        │ Migration     │
        └───────────────┘
```

---

## Success Metrics

### Phase 1 Success
- [ ] PTV graph built for 100% of patients
- [ ] Zero validation errors for 7 days
- [ ] Build latency < 5s (p95)

### Phase 2 Success
- [ ] All EoH modules migrated to adapters
- [ ] Query latency ≤ 1.2x legacy (p95)
- [ ] Zero functional regressions

### Phase 3 Success
- [ ] PRV risk matches legacy for 95% of patients
- [ ] Risk trajectories correctly capture history
- [ ] Alert system functional

### Phase 4 Success
- [ ] Zero writes to legacy tables
- [ ] Legacy read adapter handles all edge cases
- [ ] 14-day burn-in with no rollbacks

### Phase 5 Success
- [ ] Legacy system fully archived
- [ ] Zero adapter code remaining
- [ ] Documentation complete

---

## What Becomes Deprecated

### Immediate Deprecation (Phase 4+)

| Component | Status | Replacement |
|-----------|--------|-------------|
| `ehr.patient_timeline.meta` | ❌ Deprecated | `ptv.patient_event_node` + `ptv.derived_insight_node` |
| `ehr.patient_timeline.embedding` | ❌ Deprecated | `ptv.node_embedding` (with provenance) |
| Direct timeline writes | ❌ Deprecated | `PatientTimelineVisionBuilder.ingest_event()` |
| On-the-fly risk computation | ❌ Deprecated | `prv.risk_snapshot` (precomputed) |
| EoH module direct table access | ❌ Deprecated | `EnrichmentHook` interface |

### Soft Deprecation (Phase 2-4)

| Component | Status | Migration Path |
|-----------|--------|----------------|
| `ehr.patient_timeline` (reads) | 🔄 Adapter | `LegacyTimelineReader` → `PatientTimelineQuery` |
| Flat timeline queries | 🔄 Supported | Gradually migrate to graph queries |
| Scattered risk logic | 🔄 Dual-run | Migrate to PRV by Phase 3 |

---

## What Becomes Adapters

### During Migration (Phases 2-4)

```python
# These adapters bridge old and new systems

1. TimelineAdapter
   Purpose: Allow EoH modules to read from either system
   Lifetime: Until Phase 4 complete
   
2. LegacyTimelineReader
   Purpose: Support old code expecting flat timeline format
   Lifetime: Until Phase 5 complete
   
3. RiskComputationAdapter
   Purpose: Return risk from either legacy or PRV
   Lifetime: Until Phase 3 complete
   
4. EmbeddingAdapter
   Purpose: Map old embeddings to PTV node embeddings
   Lifetime: Until Phase 2 complete
```

### Permanent Adapters

```python
# These remain for backward compatibility

1. FlatTimelineView (SQL view)
   Purpose: Provide flat timeline for external consumers
   Implementation: SELECT over PTV graph
   
2. LegacyAPIAdapter
   Purpose: Support old REST API contracts
   Implementation: Transform PTV graph to old JSON format
```

---

## Emergency Procedures

### Scenario 1: Critical Bug in PTV Builder

**Symptoms:** Nodes duplicated, graph corruption, missing edges

**Response:**
1. **Immediate:** Set `PTV_WRITES_ENABLED=false`
2. **Fallback:** All writes go to legacy tables only
3. **Investigation:** Debug PTV builder with test patients
4. **Fix:** Deploy patch, re-enable for 5% of patients (canary)
5. **Resume:** Gradual rollout once validated

---

### Scenario 2: Performance Degradation

**Symptoms:** Query latency >2x, database CPU spiking

**Response:**
1. **Immediate:** Set `PTV_READS_ENABLED=false` for affected queries
2. **Diagnosis:** Identify slow queries with `EXPLAIN ANALYZE`
3. **Mitigation:** Add missing indexes, optimize query plans
4. **Test:** Validate performance on staging with production data
5. **Re-enable:** Gradual rollout once optimized

---

### Scenario 3: Data Loss Detected

**Symptoms:** Validation job reports missing events

**Response:**
1. **HALT MIGRATION** immediately
2. **Assess scope:** How many patients affected? Which events?
3. **Root cause:** Was it lost in legacy → PTV, or PTV bug?
4. **Recover:**
   - If legacy has data: Rebuild PTV from legacy
   - If legacy missing: Restore from backup
5. **Prevent:** Add additional validation checks
6. **Resume:** Only after 7-day validation with no issues

---

## Timeline Summary

```
Week 0:  [Phase 0] Pre-Migration (schema deployment, feature flags)
         
Week 1:  [Phase 1] Shadow Mode (parallel PTV build)
Week 2:  [Phase 1] Shadow Mode (validation)
Week 3:  [Phase 1] Shadow Mode (burn-in)

Week 4:  [Phase 2] Read Cutover (TerrainAnalysis migrated)
Week 5:  [Phase 2] Read Cutover (FlareSignals migrated)
Week 6:  [Phase 2] Read Cutover (FlareWindowing migrated)
Week 7:  [Phase 2] Read Cutover (CarePlanning migrated)

Week 8:  [Phase 3] Risk Migration (PRV schema + backfill)
Week 9:  [Phase 3] Risk Migration (dual computation)
Week 10: [Phase 3] Risk Migration (PRV reads cutover)

Week 11: [Phase 4] Write Cutover (PTV primary writes)
Week 12: [Phase 4] Write Cutover (EoH modules stop legacy writes)
Week 13: [Phase 4] Write Cutover (burn-in)

Week 14: [Phase 5] Deprecation (archive legacy data)
Week 15: [Phase 5] Deprecation (remove adapters)
Week 16: [Phase 5] Deprecation (cleanup + docs)

TOTAL: 16 weeks (12 weeks active migration + 4 weeks cleanup)
```

---

## Post-Migration Monitoring

### Metrics to Track (First 90 Days)

```python
# Dashboard metrics
migration_metrics = {
    "ptv_query_latency_p95": target_ms=500,
    "ptv_build_latency_p95": target_ms=5000,
    "prv_risk_computation_latency": target_ms=100,
    "validation_error_rate": target_percent=0.0,
    "rollback_count": target=0,
    "data_loss_incidents": target=0,
    "eoh_module_errors": target_percent=0.1
}
```

### Alerting Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| PTV query latency | >500ms p95 | >1000ms p95 |
| Validation errors | >0.1% | >1.0% |
| Data loss incidents | 1 | 5 |
| Rollbacks | 1 per week | 2 per week |

---

## Conclusion

This migration plan prioritizes **safety**, **observability**, and **rollback capability** at every phase.

**Key Principles:**
1. ✅ Dual writes ensure no data loss
2. ✅ Adapters allow gradual module migration
3. ✅ Feature flags enable instant rollback
4. ✅ Continuous validation catches issues early
5. ✅ Clear success criteria at each phase

**Expected Outcome:**
- 16-week migration from flat timeline to graph-based PTV/PRV
- Zero data loss
- Minimal production impact
- Full audit trail and provenance for all patient data

**Next Steps:**
1. Review and approve this plan
2. Provision infrastructure for Phase 0
3. Begin implementation starting with schema deployment

---

**Document Version:** 1.0  
**Last Updated:** 2025-12-23  
**Status:** Draft - Awaiting Approval

