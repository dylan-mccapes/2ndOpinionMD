# PatientRiskVision Architecture

**Version:** 1.0  
**Status:** Design Specification  
**Companion to:** PatientTimelineVision  
**Principle:** Risk is always graph-derived, never raw

---

## EXECUTIVE SUMMARY

**PatientRiskVision (PRV)** is a companion subsystem to PatientTimelineVision that maintains an **authoritative, temporal view of patient risk**. Unlike traditional risk scores stored in isolated tables, PRV:

- **Derives** all risk from PatientTimelineVision graph (not raw data)
- **Tracks** risk trajectory over time (not just current snapshot)
- **Explains** risk via graph provenance (not black-box scores)
- **Alerts** on risk changes with full context
- **Prevents** silent risk drift through system invariants

---

## CORE PRINCIPLES

```yaml
principles:
  - id: RISK-001
    rule: "All risk MUST be derived from PatientTimelineVision graph"
    rationale: "Graph is source of truth; raw data bypasses provenance"
    enforcement: "FOREIGN KEY constraints on all risk nodes to PTV events"
    
  - id: RISK-002
    rule: "Risk snapshots are immutable; trajectory is append-only"
    rationale: "Preserve history for audit, prevent silent drift"
    enforcement: "Triggers prevent UPDATE/DELETE on risk_snapshot table"
    
  - id: RISK-003
    rule: "Every risk change MUST have explainable cause"
    rationale: "No mysterious risk jumps; always traceable to timeline events"
    enforcement: "TRIGGER_EVENT_IDS field mandatory for all risk updates"
    
  - id: RISK-004
    rule: "Risk staleness MUST be tracked and alerted"
    rationale: "Prevent using outdated risk in clinical decisions"
    enforcement: "computed_at + max_staleness_hours defines validity window"
    
  - id: RISK-005
    rule: "Risk aggregation MUST preserve component provenance"
    rationale: "Composite risk scores show which factors contributed"
    enforcement: "risk_components JSONB stores all contributing factors"
    
  - id: RISK-006
    rule: "Alert suppression MUST be auditable"
    rationale: "Prevent gaming of alerts by silent suppression"
    enforcement: "alert_suppression table tracks all suppression events"
```

---

## ARCHITECTURE OVERVIEW

```
┌──────────────────────────────────────────────────────────────────┐
│                  SYSTEM ARCHITECTURE                             │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│              PatientTimelineVision (PTV)                         │
│  - Source of truth for all clinical events                      │
│  - Nodes: labs, meds, symptoms, decisions                       │
│  - Edges: causal, temporal, derived                             │
└────────────────────┬─────────────────────────────────────────────┘
                     │
                     │ DERIVES FROM (via graph traversal)
                     │
                     ↓
┌──────────────────────────────────────────────────────────────────┐
│              PatientRiskVision (PRV)                             │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Risk Snapshot (Point-in-Time)                             │ │
│  │  - Baseline risk                                           │ │
│  │  - Domain-specific risks (flare, infection, etc.)          │ │
│  │  - Component contributions                                 │ │
│  │  - Valid until timestamp                                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                     ↓                                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Risk Trajectory (Time Series)                             │ │
│  │  - Ordered sequence of snapshots                           │ │
│  │  - Trend detection (increasing, stable, decreasing)        │ │
│  │  - Inflection points flagged                               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                     ↓                                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Risk Alerts (Event-Driven)                                │ │
│  │  - Threshold crossings                                     │ │
│  │  - Trajectory anomalies                                    │ │
│  │  - Staleness warnings                                      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                     ↓                                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Risk Explanation (Provenance)                             │ │
│  │  - Graph paths showing risk derivation                     │ │
│  │  - Component breakdowns                                    │ │
│  │  - Confidence intervals                                    │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────────────────┐
│              Clinical Agents / UI                                │
│  - Query current risk                                            │
│  - Display trajectory charts                                     │
│  - Explain risk changes                                          │
│  - Acknowledge/suppress alerts                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## RISK NODE SCHEMA

### Table: prv.risk_snapshot

```sql
CREATE TABLE prv.risk_snapshot (
    -- IDENTITY
    snapshot_id         TEXT PRIMARY KEY,           -- "risk_{patient_id}_{computed_at_ts}"
    patient_id          TEXT NOT NULL,
    
    -- TEMPORAL
    computed_at         TIMESTAMPTZ NOT NULL,       -- When this snapshot was computed
    valid_until         TIMESTAMPTZ,                -- When this snapshot expires (staleness)
    is_current          BOOLEAN DEFAULT true,       -- Is this the latest snapshot?
    
    -- BASELINE RISK (overall patient risk level)
    baseline_risk_score FLOAT NOT NULL,             -- 0.0-1.0, overall risk
    baseline_risk_level TEXT NOT NULL,              -- "low", "moderate", "high", "critical"
    
    -- DOMAIN-SPECIFIC RISKS (each with score + level)
    flare_risk          JSONB NOT NULL,             -- {"score": 0.85, "level": "high", "horizon_days": 30}
    infection_risk      JSONB NOT NULL,
    hospitalization_risk JSONB NOT NULL,
    adverse_event_risk  JSONB NOT NULL,
    disease_progression_risk JSONB NOT NULL,
    
    -- COMPONENT CONTRIBUTIONS (which factors drove risk)
    risk_components     JSONB NOT NULL,
    -- Example:
    -- {
    --   "flare_risk": {
    --     "crp_elevation": {"contribution": 0.35, "event_id": "evt_100"},
    --     "prior_flares": {"contribution": 0.25, "event_id": "evt_flare_2024Q1"},
    --     "med_adherence": {"contribution": 0.25, "event_id": "evt_med_gap"}
    --   }
    -- }
    
    -- PROVENANCE (RISK-001: Must derive from graph)
    trigger_event_ids   TEXT[] NOT NULL,            -- PTV event IDs that triggered this computation
    source_module       TEXT NOT NULL,              -- "M7A_Prognostics", "M48_Calibration"
    computation_method  TEXT NOT NULL,              -- "ml_model_v2", "rule_based", "guideline"
    model_version       TEXT,                       -- "v2.3.1"
    
    -- CONFIDENCE
    confidence          FLOAT NOT NULL,             -- 0.0-1.0
    confidence_interval JSONB,                      -- {"low": 0.7, "high": 0.9}
    
    -- METADATA
    meta                JSONB DEFAULT '{}'::jsonb,
    
    -- CONSTRAINTS
    CONSTRAINT fk_patient_vision
        FOREIGN KEY (patient_id)
        REFERENCES ptv.patient_vision(patient_id)
        ON DELETE CASCADE,
    
    -- RISK-001: All trigger events must exist in PTV
    CONSTRAINT chk_trigger_events_exist
        CHECK (
            trigger_event_ids <@ (
                SELECT array_agg(event_id) 
                FROM ptv.event_node 
                WHERE patient_id = risk_snapshot.patient_id
            )
        ),
    
    -- RISK-003: Must have at least one trigger event
    CONSTRAINT chk_trigger_events_not_empty
        CHECK (array_length(trigger_event_ids, 1) > 0),
    
    -- Score ranges
    CONSTRAINT chk_baseline_score_range
        CHECK (baseline_risk_score BETWEEN 0.0 AND 1.0),
    
    CONSTRAINT chk_confidence_range
        CHECK (confidence BETWEEN 0.0 AND 1.0)
);

-- Indexes
CREATE INDEX idx_risk_snapshot_patient ON prv.risk_snapshot(patient_id);
CREATE INDEX idx_risk_snapshot_computed_at ON prv.risk_snapshot(patient_id, computed_at DESC);
CREATE INDEX idx_risk_snapshot_current ON prv.risk_snapshot(patient_id) WHERE is_current = true;
CREATE INDEX idx_risk_snapshot_valid ON prv.risk_snapshot(valid_until) WHERE valid_until < now();
CREATE INDEX idx_risk_snapshot_trigger_events ON prv.risk_snapshot USING GIN(trigger_event_ids);

-- Partial index for stale risk (RISK-004)
CREATE INDEX idx_risk_snapshot_stale ON prv.risk_snapshot(patient_id, valid_until)
    WHERE is_current = true AND valid_until < now();
```

### Table: prv.risk_component_link

```sql
-- Links risk components back to specific PTV nodes/edges
CREATE TABLE prv.risk_component_link (
    link_id             TEXT PRIMARY KEY,
    snapshot_id         TEXT NOT NULL,
    
    -- Component identity
    risk_domain         TEXT NOT NULL,              -- "flare_risk", "infection_risk"
    component_name      TEXT NOT NULL,              -- "crp_elevation", "prior_flares"
    contribution        FLOAT NOT NULL,             -- 0.0-1.0, how much this contributed
    
    -- Graph reference (RISK-001)
    ptv_event_id        TEXT,                       -- Single event
    ptv_subgraph_root   TEXT,                       -- Root of subgraph (for composite)
    ptv_edge_path       TEXT[],                     -- Edge IDs showing derivation path
    
    -- Explanation
    explanation         TEXT NOT NULL,
    
    -- Constraints
    CONSTRAINT fk_snapshot
        FOREIGN KEY (snapshot_id)
        REFERENCES prv.risk_snapshot(snapshot_id)
        ON DELETE CASCADE,
    
    CONSTRAINT fk_ptv_event
        FOREIGN KEY (ptv_event_id)
        REFERENCES ptv.event_node(event_id)
        ON DELETE CASCADE,
    
    CONSTRAINT chk_contribution_range
        CHECK (contribution BETWEEN 0.0 AND 1.0),
    
    -- Must reference either single event or subgraph
    CONSTRAINT chk_graph_reference
        CHECK (ptv_event_id IS NOT NULL OR ptv_subgraph_root IS NOT NULL)
);

CREATE INDEX idx_risk_component_link_snapshot ON prv.risk_component_link(snapshot_id);
CREATE INDEX idx_risk_component_link_event ON prv.risk_component_link(ptv_event_id);
```

### Table: prv.risk_trajectory

```sql
-- Materialized view of risk over time for a patient
CREATE TABLE prv.risk_trajectory (
    trajectory_id       TEXT PRIMARY KEY,
    patient_id          TEXT NOT NULL,
    
    -- Time window
    trajectory_start    TIMESTAMPTZ NOT NULL,
    trajectory_end      TIMESTAMPTZ NOT NULL,
    
    -- Snapshot sequence (ordered by computed_at)
    snapshot_ids        TEXT[] NOT NULL,
    snapshot_count      INTEGER NOT NULL,
    
    -- Trend analysis
    trend               TEXT NOT NULL,              -- "increasing", "stable", "decreasing", "volatile"
    trend_confidence    FLOAT NOT NULL,
    inflection_points   JSONB,                      -- Timestamps where trend changed
    
    -- Statistics
    baseline_risk_stats JSONB NOT NULL,
    -- Example:
    -- {
    --   "min": 0.3, "max": 0.9, "mean": 0.6, "std": 0.15,
    --   "first": 0.5, "last": 0.7, "delta": +0.2
    -- }
    
    flare_risk_stats    JSONB NOT NULL,
    infection_risk_stats JSONB NOT NULL,
    
    -- Metadata
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Constraints
    CONSTRAINT fk_patient_vision
        FOREIGN KEY (patient_id)
        REFERENCES ptv.patient_vision(patient_id)
        ON DELETE CASCADE,
    
    CONSTRAINT chk_time_order
        CHECK (trajectory_end >= trajectory_start),
    
    CONSTRAINT chk_snapshot_count_matches
        CHECK (snapshot_count = array_length(snapshot_ids, 1))
);

CREATE INDEX idx_risk_trajectory_patient ON prv.risk_trajectory(patient_id);
CREATE INDEX idx_risk_trajectory_end ON prv.risk_trajectory(patient_id, trajectory_end DESC);
```

---

## RISK DERIVATION FROM TIMELINE GRAPH

### Derivation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                 RISK DERIVATION FLOW                            │
└─────────────────────────────────────────────────────────────────┘

Step 1: TRIGGER EVENT
┌──────────────────────────────────────────────────────────────┐
│  New PTV event arrives: evt_lab_100 (CRP=65)                 │
│  - node_type: MEASUREMENT                                    │
│  - annotations.flare_signal_strength: 0.85 (from M4)         │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ↓
Step 2: GRAPH TRAVERSAL (collect risk factors)
┌──────────────────────────────────────────────────────────────┐
│  Traverse backward from evt_lab_100:                         │
│  - Find prior flare episodes (COMPOSITE nodes)               │
│  - Find medication adherence gaps (MEDICATION_CHANGE)        │
│  - Find recent infection events (NOTE with mentions)         │
│  - Find disease activity trends (TEMPORAL_WINDOW)            │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ↓
Step 3: COMPONENT SCORING
┌──────────────────────────────────────────────────────────────┐
│  Score each risk component:                                  │
│  - CRP elevation: 0.35 (current event)                       │
│  - Prior flares: 0.25 (2 flares in last 6 months)           │
│  - Med adherence: 0.25 (1 gap in last 3 months)             │
│  - Disease activity: 0.15 (trending up)                      │
│  Total contribution: 1.0                                     │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ↓
Step 4: RISK AGGREGATION
┌──────────────────────────────────────────────────────────────┐
│  Aggregate into domain risks:                                │
│  - Flare risk: 0.85 (high) ← primary                         │
│  - Infection risk: 0.30 (low) ← stable                       │
│  - Hospitalization risk: 0.40 (moderate) ← derived           │
│  - Baseline risk: 0.68 (moderate-high) ← overall             │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ↓
Step 5: SNAPSHOT CREATION
┌──────────────────────────────────────────────────────────────┐
│  CREATE prv.risk_snapshot:                                   │
│  - snapshot_id: risk_P001_20250115T103000                    │
│  - computed_at: 2025-01-15 10:30:00                          │
│  - trigger_event_ids: [evt_lab_100, evt_flare_2024Q4, ...]  │
│  - flare_risk: {"score": 0.85, "level": "high"}             │
│  - risk_components: {<full breakdown>}                       │
│  - source_module: M7A_Prognostics                            │
│  - confidence: 0.88                                          │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ↓
Step 6: ALERT EVALUATION
┌──────────────────────────────────────────────────────────────┐
│  Compare to previous snapshot:                               │
│  - Prior flare_risk: 0.45 (moderate)                         │
│  - New flare_risk: 0.85 (high)                               │
│  - Delta: +0.40 (threshold: 0.30)                            │
│  - ALERT: Risk increased significantly                       │
└──────────────────────────────────────────────────────────────┘
```

### Example Implementation

```python
def compute_risk_snapshot(
    patient_id: str,
    trigger_event_id: str,
    cur,
) -> str:
    """
    Compute new risk snapshot triggered by a PTV event.
    
    RISK-001: All risk derived from graph traversal.
    RISK-003: Trigger event must be specified.
    """
    # Step 1: Load trigger event from PTV
    cur.execute("""
        SELECT event_id, node_type, structured, annotations, timestamp
        FROM ptv.event_node
        WHERE event_id = %s
    """, (trigger_event_id,))
    
    trigger = cur.fetchone()
    if not trigger:
        raise ValueError(f"Trigger event {trigger_event_id} not found in PTV")
    
    # Step 2: Collect risk factors via graph traversal
    risk_factors = collect_risk_factors_from_graph(patient_id, trigger_event_id, cur)
    
    # Step 3: Score components
    components = score_risk_components(risk_factors)
    
    # Step 4: Aggregate into domain risks
    domain_risks = aggregate_domain_risks(components)
    
    # Step 5: Create snapshot
    snapshot_id = f"risk_{patient_id}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
    
    cur.execute("""
        INSERT INTO prv.risk_snapshot (
            snapshot_id,
            patient_id,
            computed_at,
            valid_until,
            is_current,
            baseline_risk_score,
            baseline_risk_level,
            flare_risk,
            infection_risk,
            hospitalization_risk,
            adverse_event_risk,
            disease_progression_risk,
            risk_components,
            trigger_event_ids,
            source_module,
            computation_method,
            model_version,
            confidence
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """, (
        snapshot_id,
        patient_id,
        datetime.now(timezone.utc),
        datetime.now(timezone.utc) + timedelta(hours=24),  # Valid for 24h (RISK-004)
        True,  # is_current
        domain_risks["baseline_risk_score"],
        domain_risks["baseline_risk_level"],
        Json(domain_risks["flare_risk"]),
        Json(domain_risks["infection_risk"]),
        Json(domain_risks["hospitalization_risk"]),
        Json(domain_risks["adverse_event_risk"]),
        Json(domain_risks["disease_progression_risk"]),
        Json(components),
        [trigger_event_id] + risk_factors["related_event_ids"],
        "M7A_Prognostics",
        "ml_model_v2",
        "2.3.1",
        0.88,
    ))
    
    # Mark previous snapshot as not current
    cur.execute("""
        UPDATE prv.risk_snapshot
        SET is_current = false
        WHERE patient_id = %s AND snapshot_id != %s
    """, (patient_id, snapshot_id))
    
    # Create component links (RISK-005)
    create_component_links(snapshot_id, components, cur)
    
    return snapshot_id

def collect_risk_factors_from_graph(
    patient_id: str,
    trigger_event_id: str,
    cur,
) -> Dict[str, Any]:
    """
    Traverse PTV graph to collect all risk factors.
    
    Risk factors:
    - Recent flare episodes (last 6 months)
    - Medication adherence gaps
    - Disease activity trends
    - Comorbidities
    - Lab abnormalities
    """
    factors = {
        "trigger_event": trigger_event_id,
        "related_event_ids": [],
        "flare_history": [],
        "med_adherence": [],
        "lab_trends": [],
        "comorbidities": [],
    }
    
    # Find recent flare episodes (DERIVED_INSIGHT nodes)
    cur.execute("""
        SELECT event_id, structured, timestamp
        FROM ptv.event_node
        WHERE patient_id = %s
          AND node_type = 'derived_insight'
          AND event_subtype = 'flare_episode'
          AND timestamp > %s - INTERVAL '6 months'
        ORDER BY timestamp DESC
    """, (patient_id, datetime.now(timezone.utc)))
    
    for row in cur.fetchall():
        factors["flare_history"].append({
            "event_id": row[0],
            "structured": row[1],
            "timestamp": row[2],
        })
        factors["related_event_ids"].append(row[0])
    
    # Find medication adherence gaps
    cur.execute("""
        SELECT event_id, structured, timestamp
        FROM ptv.event_node
        WHERE patient_id = %s
          AND node_type = 'medication_change'
          AND structured->>'action' = 'hold'
          AND timestamp > %s - INTERVAL '3 months'
    """, (patient_id, datetime.now(timezone.utc)))
    
    for row in cur.fetchall():
        factors["med_adherence"].append({
            "event_id": row[0],
            "structured": row[1],
            "timestamp": row[2],
        })
        factors["related_event_ids"].append(row[0])
    
    # Find lab trends (inflammatory markers)
    cur.execute("""
        SELECT event_id, structured, timestamp, annotations
        FROM ptv.event_node
        WHERE patient_id = %s
          AND node_type = 'measurement'
          AND (event_subtype ILIKE '%CRP%' OR event_subtype ILIKE '%ESR%')
          AND timestamp > %s - INTERVAL '3 months'
        ORDER BY timestamp DESC
        LIMIT 5
    """, (patient_id, datetime.now(timezone.utc)))
    
    for row in cur.fetchall():
        factors["lab_trends"].append({
            "event_id": row[0],
            "structured": row[1],
            "timestamp": row[2],
            "flare_signal": row[3].get("M4_FlareSignals", {}).get("flare_signal_strength", 0),
        })
        factors["related_event_ids"].append(row[0])
    
    return factors
```

---

## TRAJECTORY COMPUTATION

### Computation Strategy

```python
def compute_risk_trajectory(
    patient_id: str,
    lookback_days: int = 90,
    cur,
) -> str:
    """
    Compute risk trajectory for a patient over time window.
    
    Steps:
    1. Fetch all snapshots in window
    2. Compute trend (increasing/decreasing/stable)
    3. Detect inflection points
    4. Compute statistics
    """
    # Fetch snapshots
    cur.execute("""
        SELECT snapshot_id, computed_at, baseline_risk_score, flare_risk, infection_risk
        FROM prv.risk_snapshot
        WHERE patient_id = %s
          AND computed_at > %s - INTERVAL '%s days'
        ORDER BY computed_at ASC
    """, (patient_id, datetime.now(timezone.utc), lookback_days))
    
    snapshots = cur.fetchall()
    
    if len(snapshots) < 2:
        # Need at least 2 snapshots for trajectory
        return None
    
    # Extract time series
    timestamps = [s[1] for s in snapshots]
    baseline_scores = [s[2] for s in snapshots]
    flare_scores = [s[3]["score"] for s in snapshots]
    
    # Compute trend (simple linear regression)
    trend, trend_confidence = compute_trend(timestamps, baseline_scores)
    
    # Detect inflection points (where trend changes)
    inflection_points = detect_inflection_points(timestamps, baseline_scores)
    
    # Compute statistics
    baseline_stats = {
        "min": min(baseline_scores),
        "max": max(baseline_scores),
        "mean": sum(baseline_scores) / len(baseline_scores),
        "std": compute_std(baseline_scores),
        "first": baseline_scores[0],
        "last": baseline_scores[-1],
        "delta": baseline_scores[-1] - baseline_scores[0],
    }
    
    flare_stats = compute_stats(flare_scores)
    infection_stats = compute_stats([s[4]["score"] for s in snapshots])
    
    # Create trajectory record
    trajectory_id = f"traj_{patient_id}_{lookback_days}d_{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    
    cur.execute("""
        INSERT INTO prv.risk_trajectory (
            trajectory_id,
            patient_id,
            trajectory_start,
            trajectory_end,
            snapshot_ids,
            snapshot_count,
            trend,
            trend_confidence,
            inflection_points,
            baseline_risk_stats,
            flare_risk_stats,
            infection_risk_stats
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (trajectory_id) DO UPDATE SET
            snapshot_ids = EXCLUDED.snapshot_ids,
            snapshot_count = EXCLUDED.snapshot_count,
            trend = EXCLUDED.trend,
            trend_confidence = EXCLUDED.trend_confidence,
            baseline_risk_stats = EXCLUDED.baseline_risk_stats,
            computed_at = now()
    """, (
        trajectory_id,
        patient_id,
        timestamps[0],
        timestamps[-1],
        [s[0] for s in snapshots],
        len(snapshots),
        trend,
        trend_confidence,
        Json(inflection_points),
        Json(baseline_stats),
        Json(flare_stats),
        Json(infection_stats),
    ))
    
    return trajectory_id
```

---

## ALERTING SYSTEM

### Table: prv.risk_alert

```sql
CREATE TABLE prv.risk_alert (
    alert_id            TEXT PRIMARY KEY,
    patient_id          TEXT NOT NULL,
    
    -- Alert trigger
    snapshot_id         TEXT NOT NULL,              -- Snapshot that triggered alert
    alert_type          TEXT NOT NULL,              -- "threshold_crossing", "trend_change", "staleness"
    risk_domain         TEXT NOT NULL,              -- "flare_risk", "infection_risk"
    severity            TEXT NOT NULL,              -- "low", "moderate", "high", "critical"
    
    -- Alert details
    alert_message       TEXT NOT NULL,
    risk_score_old      FLOAT,
    risk_score_new      FLOAT,
    delta               FLOAT,
    
    -- Explanation (RISK-003)
    trigger_event_ids   TEXT[] NOT NULL,
    explanation         TEXT NOT NULL,
    graph_path          TEXT[],                     -- Edge IDs showing provenance
    
    -- Status
    status              TEXT NOT NULL DEFAULT 'active',  -- "active", "acknowledged", "resolved", "suppressed"
    acknowledged_at     TIMESTAMPTZ,
    acknowledged_by     TEXT,
    resolved_at         TIMESTAMPTZ,
    
    -- Metadata
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Constraints
    CONSTRAINT fk_snapshot
        FOREIGN KEY (snapshot_id)
        REFERENCES prv.risk_snapshot(snapshot_id)
        ON DELETE CASCADE,
    
    CONSTRAINT chk_status
        CHECK (status IN ('active', 'acknowledged', 'resolved', 'suppressed'))
);

CREATE INDEX idx_risk_alert_patient ON prv.risk_alert(patient_id);
CREATE INDEX idx_risk_alert_status ON prv.risk_alert(status) WHERE status = 'active';
CREATE INDEX idx_risk_alert_severity ON prv.risk_alert(severity, status);
```

### Table: prv.alert_suppression (RISK-006)

```sql
-- Audit trail for alert suppression
CREATE TABLE prv.alert_suppression (
    suppression_id      TEXT PRIMARY KEY,
    alert_id            TEXT NOT NULL,
    
    -- Suppression details
    suppressed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    suppressed_by       TEXT NOT NULL,              -- User or system that suppressed
    reason              TEXT NOT NULL,              -- Why was alert suppressed?
    duration_hours      INTEGER,                    -- How long to suppress (NULL = permanent)
    unsuppress_at       TIMESTAMPTZ,
    
    -- Audit
    was_justified       BOOLEAN,                    -- Post-hoc review
    review_notes        TEXT,
    
    -- Constraints
    CONSTRAINT fk_alert
        FOREIGN KEY (alert_id)
        REFERENCES prv.risk_alert(alert_id)
        ON DELETE CASCADE
);

CREATE INDEX idx_alert_suppression_alert ON prv.alert_suppression(alert_id);
CREATE INDEX idx_alert_suppression_review ON prv.alert_suppression(suppressed_at) 
    WHERE was_justified IS NULL;
```

### Alert Generation Logic

```python
def evaluate_alerts(
    patient_id: str,
    new_snapshot_id: str,
    cur,
) -> List[str]:
    """
    Evaluate if new snapshot triggers any alerts.
    
    Alert types:
    1. Threshold crossing (risk enters high/critical range)
    2. Rapid increase (risk jumps >0.3 in short time)
    3. Trend reversal (risk was decreasing, now increasing)
    4. Staleness (no recent risk update)
    """
    alerts_created = []
    
    # Fetch new snapshot
    cur.execute("""
        SELECT 
            snapshot_id, computed_at, baseline_risk_score, 
            flare_risk, infection_risk, trigger_event_ids
        FROM prv.risk_snapshot
        WHERE snapshot_id = %s
    """, (new_snapshot_id,))
    
    new_snap = cur.fetchone()
    
    # Fetch previous snapshot
    cur.execute("""
        SELECT 
            snapshot_id, computed_at, baseline_risk_score, 
            flare_risk, infection_risk
        FROM prv.risk_snapshot
        WHERE patient_id = %s
          AND snapshot_id != %s
          AND is_current = false
        ORDER BY computed_at DESC
        LIMIT 1
    """, (patient_id, new_snapshot_id))
    
    prev_snap = cur.fetchone()
    
    # Alert 1: Threshold crossing
    if new_snap[3]["score"] >= 0.8 and (not prev_snap or prev_snap[3]["score"] < 0.8):
        alert_id = create_alert(
            patient_id=patient_id,
            snapshot_id=new_snapshot_id,
            alert_type="threshold_crossing",
            risk_domain="flare_risk",
            severity="high",
            message=f"Flare risk entered HIGH range ({new_snap[3]['score']:.2f})",
            old_score=prev_snap[3]["score"] if prev_snap else None,
            new_score=new_snap[3]["score"],
            trigger_event_ids=new_snap[5],
            cur=cur,
        )
        alerts_created.append(alert_id)
    
    # Alert 2: Rapid increase
    if prev_snap:
        delta = new_snap[2] - prev_snap[2]
        time_delta_hours = (new_snap[1] - prev_snap[1]).total_seconds() / 3600
        
        if delta > 0.3 and time_delta_hours < 48:
            alert_id = create_alert(
                patient_id=patient_id,
                snapshot_id=new_snapshot_id,
                alert_type="rapid_increase",
                risk_domain="baseline_risk",
                severity="high",
                message=f"Risk increased rapidly (+{delta:.2f} in {time_delta_hours:.1f}h)",
                old_score=prev_snap[2],
                new_score=new_snap[2],
                trigger_event_ids=new_snap[5],
                cur=cur,
            )
            alerts_created.append(alert_id)
    
    # Alert 3: Staleness (RISK-004)
    # (Handled by separate scheduled job)
    
    return alerts_created
```

---

## SYSTEM INVARIANTS (Anti-Drift)

### Invariant Enforcement

```sql
-- =====================================================================
-- INVARIANT: RISK-002 (Immutable snapshots, append-only trajectory)
-- =====================================================================

CREATE OR REPLACE FUNCTION prv.prevent_snapshot_updates()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        -- Allow updating is_current flag only
        IF (OLD.baseline_risk_score IS DISTINCT FROM NEW.baseline_risk_score OR
            OLD.flare_risk IS DISTINCT FROM NEW.flare_risk OR
            OLD.risk_components IS DISTINCT FROM NEW.risk_components OR
            OLD.trigger_event_ids IS DISTINCT FROM NEW.trigger_event_ids)
        THEN
            RAISE EXCEPTION 'RISK-002 violation: Risk snapshots are immutable. Create new snapshot instead.';
        END IF;
    END IF;
    
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'RISK-002 violation: Risk snapshots cannot be deleted (audit trail).';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_prevent_snapshot_updates
    BEFORE UPDATE OR DELETE ON prv.risk_snapshot
    FOR EACH ROW
    EXECUTE FUNCTION prv.prevent_snapshot_updates();

-- =====================================================================
-- INVARIANT: RISK-004 (Staleness detection)
-- =====================================================================

CREATE OR REPLACE FUNCTION prv.alert_on_stale_risk()
RETURNS void AS $$
DECLARE
    stale_patient RECORD;
BEGIN
    -- Find patients with stale risk (valid_until expired)
    FOR stale_patient IN
        SELECT DISTINCT patient_id, snapshot_id, valid_until
        FROM prv.risk_snapshot
        WHERE is_current = true
          AND valid_until < now()
          AND NOT EXISTS (
              SELECT 1 FROM prv.risk_alert
              WHERE patient_id = risk_snapshot.patient_id
                AND alert_type = 'staleness'
                AND status = 'active'
          )
    LOOP
        -- Create staleness alert
        INSERT INTO prv.risk_alert (
            alert_id,
            patient_id,
            snapshot_id,
            alert_type,
            risk_domain,
            severity,
            alert_message,
            trigger_event_ids,
            explanation
        ) VALUES (
            'alert_stale_' || stale_patient.patient_id || '_' || extract(epoch from now()),
            stale_patient.patient_id,
            stale_patient.snapshot_id,
            'staleness',
            'all',
            'moderate',
            'Risk snapshot expired at ' || stale_patient.valid_until || '. Recompute risk.',
            ARRAY[]::TEXT[],
            'Risk snapshot is outdated and may not reflect current patient state. Trigger risk recomputation.'
        );
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Schedule this to run every hour
-- (In production, use pg_cron or external scheduler)

-- =====================================================================
-- INVARIANT: RISK-006 (Alert suppression audit)
-- =====================================================================

CREATE OR REPLACE FUNCTION prv.audit_alert_suppression()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'suppressed' AND OLD.status != 'suppressed' THEN
        -- Alert was suppressed; ensure audit record exists
        IF NOT EXISTS (
            SELECT 1 FROM prv.alert_suppression
            WHERE alert_id = NEW.alert_id
              AND suppressed_at >= now() - INTERVAL '1 minute'
        ) THEN
            RAISE EXCEPTION 'RISK-006 violation: Alert suppression requires audit record in prv.alert_suppression';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_audit_alert_suppression
    BEFORE UPDATE ON prv.risk_alert
    FOR EACH ROW
    WHEN (NEW.status = 'suppressed')
    EXECUTE FUNCTION prv.audit_alert_suppression();
```

---

## AGENT QUERY PATTERNS

### Pattern 1: Get Current Risk

```python
def get_current_risk(patient_id: str, cur) -> Dict[str, Any]:
    """
    Get current risk snapshot for a patient.
    
    Returns latest snapshot with full provenance.
    """
    cur.execute("""
        SELECT 
            snapshot_id,
            computed_at,
            valid_until,
            baseline_risk_score,
            baseline_risk_level,
            flare_risk,
            infection_risk,
            hospitalization_risk,
            risk_components,
            trigger_event_ids,
            source_module,
            confidence,
            confidence_interval
        FROM prv.risk_snapshot
        WHERE patient_id = %s AND is_current = true
    """, (patient_id,))
    
    row = cur.fetchone()
    if not row:
        return {"error": "No risk snapshot found", "patient_id": patient_id}
    
    # Check staleness (RISK-004)
    is_stale = row[2] < datetime.now(timezone.utc)
    
    return {
        "patient_id": patient_id,
        "snapshot_id": row[0],
        "computed_at": row[1].isoformat(),
        "valid_until": row[2].isoformat(),
        "is_stale": is_stale,
        "baseline_risk": {
            "score": row[3],
            "level": row[4],
        },
        "domain_risks": {
            "flare": row[5],
            "infection": row[6],
            "hospitalization": row[7],
        },
        "components": row[8],
        "provenance": {
            "trigger_events": row[9],
            "source_module": row[10],
            "confidence": row[11],
            "confidence_interval": row[12],
        }
    }
```

### Pattern 2: Explain Risk Change

```python
def explain_risk_change(
    patient_id: str,
    snapshot_id_old: str,
    snapshot_id_new: str,
    cur,
) -> Dict[str, Any]:
    """
    Explain why risk changed between two snapshots.
    
    Traverses PTV graph to show causal path.
    """
    # Fetch both snapshots
    cur.execute("""
        SELECT snapshot_id, computed_at, baseline_risk_score, risk_components, trigger_event_ids
        FROM prv.risk_snapshot
        WHERE snapshot_id IN (%s, %s)
        ORDER BY computed_at
    """, (snapshot_id_old, snapshot_id_new))
    
    old_snap, new_snap = cur.fetchall()
    
    # Compute delta
    delta = new_snap[2] - old_snap[2]
    
    # Find new trigger events (not in old snapshot)
    new_triggers = set(new_snap[4]) - set(old_snap[4])
    
    # Explain each new trigger via PTV graph
    explanations = []
    for trigger_event_id in new_triggers:
        # Load event from PTV
        cur.execute("""
            SELECT event_id, node_type, event_subtype, structured, text, annotations
            FROM ptv.event_node
            WHERE event_id = %s
        """, (trigger_event_id,))
        
        event = cur.fetchone()
        
        # Find component contribution
        component_contrib = 0.0
        for domain, components in new_snap[3].items():
            for comp_name, comp_data in components.items():
                if comp_data.get("event_id") == trigger_event_id:
                    component_contrib = comp_data.get("contribution", 0)
                    break
        
        explanations.append({
            "event_id": event[0],
            "event_type": event[1],
            "event_subtype": event[2],
            "summary": event[4] or str(event[3]),
            "contribution_to_risk": component_contrib,
            "timestamp": event[5],
        })
    
    return {
        "patient_id": patient_id,
        "delta": delta,
        "old_score": old_snap[2],
        "new_score": new_snap[2],
        "change_description": f"Risk {'increased' if delta > 0 else 'decreased'} by {abs(delta):.2f}",
        "new_trigger_events": explanations,
        "computed_between": (old_snap[1].isoformat(), new_snap[1].isoformat()),
    }
```

### Pattern 3: Get Risk Trajectory

```python
def get_risk_trajectory(
    patient_id: str,
    lookback_days: int = 90,
    cur,
) -> Dict[str, Any]:
    """
    Get risk trajectory over time.
    
    Returns time series data for visualization.
    """
    # Fetch trajectory record
    cur.execute("""
        SELECT 
            trajectory_id,
            trajectory_start,
            trajectory_end,
            snapshot_ids,
            trend,
            trend_confidence,
            inflection_points,
            baseline_risk_stats,
            flare_risk_stats
        FROM prv.risk_trajectory
        WHERE patient_id = %s
          AND trajectory_end >= %s - INTERVAL '%s days'
        ORDER BY trajectory_end DESC
        LIMIT 1
    """, (patient_id, datetime.now(timezone.utc), lookback_days))
    
    traj = cur.fetchone()
    if not traj:
        # Compute trajectory if not exists
        compute_risk_trajectory(patient_id, lookback_days, cur)
        cur.execute(query_above)  # Retry
        traj = cur.fetchone()
    
    # Fetch individual snapshots for time series
    cur.execute("""
        SELECT 
            snapshot_id,
            computed_at,
            baseline_risk_score,
            flare_risk->>'score',
            infection_risk->>'score'
        FROM prv.risk_snapshot
        WHERE snapshot_id = ANY(%s)
        ORDER BY computed_at
    """, (traj[3],))
    
    snapshots = cur.fetchall()
    
    return {
        "patient_id": patient_id,
        "trajectory_id": traj[0],
        "period": {
            "start": traj[1].isoformat(),
            "end": traj[2].isoformat(),
        },
        "trend": traj[4],
        "trend_confidence": traj[5],
        "inflection_points": traj[6],
        "statistics": {
            "baseline_risk": traj[7],
            "flare_risk": traj[8],
        },
        "time_series": [
            {
                "timestamp": s[1].isoformat(),
                "baseline_risk": s[2],
                "flare_risk": float(s[3]),
                "infection_risk": float(s[4]),
            }
            for s in snapshots
        ]
    }
```

### Pattern 4: Get Active Alerts

```python
def get_active_alerts(patient_id: str, cur) -> List[Dict[str, Any]]:
    """
    Get all active alerts for a patient.
    """
    cur.execute("""
        SELECT 
            alert_id,
            alert_type,
            risk_domain,
            severity,
            alert_message,
            risk_score_old,
            risk_score_new,
            delta,
            trigger_event_ids,
            explanation,
            created_at
        FROM prv.risk_alert
        WHERE patient_id = %s
          AND status = 'active'
        ORDER BY severity DESC, created_at DESC
    """, (patient_id,))
    
    alerts = []
    for row in cur.fetchall():
        alerts.append({
            "alert_id": row[0],
            "type": row[1],
            "risk_domain": row[2],
            "severity": row[3],
            "message": row[4],
            "score_change": {
                "old": row[5],
                "new": row[6],
                "delta": row[7],
            },
            "trigger_events": row[8],
            "explanation": row[9],
            "created_at": row[10].isoformat(),
        })
    
    return alerts
```

---

## INTEGRATION WITH PATIENTTIMELINEVISION

```
┌──────────────────────────────────────────────────────────────────┐
│                    INTEGRATION POINTS                            │
└──────────────────────────────────────────────────────────────────┘

1. EVENT TRIGGER
   PTV: New event added (evt_lab_100)
   PRV: Compute new risk snapshot

2. GRAPH TRAVERSAL
   PTV: Provides graph structure (nodes + edges)
   PRV: Traverses graph to collect risk factors

3. PROVENANCE
   PTV: Event has discovered_by = ["M4_FlareSignals"]
   PRV: Risk component cites event_id + discovered_by

4. COMPOSITE NODES
   PTV: DERIVED_INSIGHT nodes (flare episodes)
   PRV: Uses as risk factors (prior flares)

5. EMBEDDINGS
   PTV: Node embeddings for semantic search
   PRV: Uses to find similar risk profiles

6. AGENT QUERIES
   PTV: Provides event details
   PRV: Provides risk context
   Together: "Patient has high flare risk (0.85) because CRP=65 (evt_100)"
```

---

## SUMMARY: KEY INNOVATIONS

```yaml
innovations:
  - name: "Graph-Derived Risk"
    description: "All risk computed from PTV graph, never raw data (RISK-001)"
    benefit: "Provenance preserved, explainable"
    
  - name: "Immutable Snapshots"
    description: "Risk snapshots are append-only, no silent updates (RISK-002)"
    benefit: "Full audit trail, prevents drift"
    
  - name: "Explainable Components"
    description: "Every risk score breaks down into graph-backed factors (RISK-005)"
    benefit: "Clinicians see WHY risk is high"
    
  - name: "Staleness Tracking"
    description: "Risk validity window enforced, stale risk triggers alerts (RISK-004)"
    benefit: "Prevents outdated risk in clinical decisions"
    
  - name: "Alert Audit Trail"
    description: "Alert suppression requires justification (RISK-006)"
    benefit: "Prevents gaming of alert system"
    
  - name: "Trajectory Analysis"
    description: "Risk over time with trend detection"
    benefit: "Identify early deterioration"
```

---

**END OF SPECIFICATION**

**Next:** Implement PRV builder module (server/prv/builder.py)

