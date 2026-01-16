# PatientTimelineVision: Use Case Comparisons

**Purpose:** Show concrete examples of how PTV changes the implementation of common clinical reasoning tasks.

---

## Use Case 1: "Why was this medication escalated?"

### Current Approach (Flat Timeline)

```python
# Query timeline table
timeline_events = db.execute("""
    SELECT * FROM ehr.patient_timeline
    WHERE patient_id = %s
      AND ts BETWEEN %s AND %s
    ORDER BY ts
""", (patient_id, start_date, end_date))

# Manual logic to infer causality
decision_event = next(e for e in timeline_events if "methotrexate" in e["text"])
decision_ts = decision_event["ts"]

# Look backward in time (hope we find the right window)
prior_labs = [e for e in timeline_events 
              if e["event_type"] == "lab" 
              and e["ts"] < decision_ts 
              and e["ts"] > decision_ts - timedelta(days=30)]

# Extract lab values (fragile string parsing)
crp_values = []
for lab in prior_labs:
    if "CRP" in lab["text"]:
        # Parse value from text (brittle!)
        match = re.search(r"CRP.*?(\d+\.?\d*)", lab["text"])
        if match:
            crp_values.append(float(match.group(1)))

# Guess at causality (no confidence measure)
if crp_values and max(crp_values) > 50:
    explanation = f"MTX escalated likely due to elevated CRP (max={max(crp_values)})"
else:
    explanation = "Reason for MTX escalation unclear from timeline"

# Result: Brittle, no provenance, no confidence
```

### PTV Approach (Graph Traversal)

```python
# Load patient's knowledge graph
ptv = PatientTimelineVision.load(patient_id)

# Find decision event
decision_event = ptv.find_event(
    event_type=EventType.DECISION,
    text_contains="methotrexate escalated",
    time_range=(start_date, end_date)
)[0]

# Traverse backward through CAUSAL and PROVENANCE edges
causal_chain = ptv.traverse_backward(
    start_event_id=decision_event.event_id,
    edge_types=[RelationshipType.CAUSAL_LIKELY, RelationshipType.PROVENANCE],
    max_hops=3,
    min_strength=0.5  # Only follow strong relationships
)

# Generate explanation with provenance
explanation = ptv.generate_explanation(
    decision_event_id=decision_event.event_id,
    include_module_provenance=True,
    max_causal_depth=3
)

# Result (example):
# "MTX escalated due to:
#  1. Elevated flare risk (M7A prognostics, conf=0.92, edge_strength=0.88)
#  2. Lab evidence: CRP=65 mg/L (evt_789, causal_likely, M4, conf=0.85)
#  3. Patient-reported joint pain severity=8/10 (evt_791, causal_likely, M1, conf=0.78)
#  4. MTX subtherapeutic response over 12 weeks (M22 care planning, conf=0.90)
#  Supporting edges: 4 CAUSAL_LIKELY, 2 PROVENANCE
#  Modules involved: M1, M4, M7A, M22"
```

**Benefits:**
- ✅ Explicit causal edges (no guessing)
- ✅ Confidence scores from modules
- ✅ Full provenance (which modules contributed)
- ✅ No brittle string parsing
- ✅ Reproducible reasoning

---

## Use Case 2: "Does this patient have a seasonal flare pattern?"

### Current Approach (Flat Timeline)

```python
# Query all labs indicating inflammation
inflammation_events = db.execute("""
    SELECT ts, structured->'test_name' as test, structured->'value' as value
    FROM ehr.patient_timeline
    WHERE patient_id = %s
      AND event_type = 'lab'
      AND (structured->>'test_name' = 'CRP' OR structured->>'test_name' = 'ESR')
    ORDER BY ts
""", (patient_id,))

# Manual clustering logic
flare_timestamps = []
for event in inflammation_events:
    if float(event["value"]) > threshold:
        flare_timestamps.append(event["ts"])

# Group by month
from collections import defaultdict
month_counts = defaultdict(int)
for ts in flare_timestamps:
    month_counts[ts.month] += 1

# Heuristic: if 2+ flares in same month across years, call it a pattern
seasonal_months = [m for m, count in month_counts.items() if count >= 2]

if seasonal_months:
    explanation = f"Possible seasonal pattern in months: {seasonal_months}"
else:
    explanation = "No clear seasonal pattern detected"

# Problems:
# - No concept of "flare episode" (just individual lab values)
# - No similarity comparison between flares
# - No confidence measure
# - Ignores symptoms, meds, other context
```

### PTV Approach (Graph Traversal + Similarity Edges)

```python
ptv = PatientTimelineVision.load(patient_id)

# Find all flare episodes (composite nodes created by M5)
flare_episodes = ptv.find_events(
    event_type=EventType.RISK_FLAG,
    event_subtype="flare_episode"
)

# Analyze temporal clustering
timestamps = [flare.timestamp for flare in flare_episodes]
seasonal_analysis = analyze_temporal_pattern(timestamps)

# Find SIMILARITY edges between flare episodes
similar_flare_pairs = []
for flare in flare_episodes:
    similar_edges = ptv.find_edges(
        source_event_id=flare.event_id,
        relationship_type=RelationshipType.SIMILARITY,
        min_strength=0.7
    )
    similar_flare_pairs.extend(similar_edges)

# Extract shared features from similar flares
shared_features = defaultdict(int)
for edge in similar_flare_pairs:
    features = edge.annotations.get("shared_features", {})
    for feature, present in features.items():
        if present:
            shared_features[feature] += 1

# Generate explanation
if len(flare_episodes) >= 3 and seasonal_analysis["seasonal_score"] > 0.7:
    explanation = f"""
    Seasonal flare pattern detected (conf={seasonal_analysis['seasonal_score']:.2f}):
    - {len(flare_episodes)} flare episodes identified (M5)
    - Peak months: {seasonal_analysis['peak_months']}
    - {len(similar_flare_pairs)} high-similarity flare pairs (M13)
    - Shared features across flares:
        * {shared_features.get('crp_elevation', 0)}/{len(flare_episodes)} had CRP elevation
        * {shared_features.get('joint_swelling', 0)}/{len(flare_episodes)} had joint swelling
        * {shared_features.get('weather_change', 0)}/{len(flare_episodes)} coincided with weather changes
    - Provenance: M5 (flare windowing), M13 (diagnostic landscape), M1 (terrain)
    """
else:
    explanation = f"No strong seasonal pattern (only {len(flare_episodes)} episodes, conf={seasonal_analysis['seasonal_score']:.2f})"
```

**Benefits:**
- ✅ Flare episodes are first-class nodes (not re-computed each time)
- ✅ SIMILARITY edges encode relationships between episodes
- ✅ Shared features extracted by modules (M13) and stored in edges
- ✅ Confidence scores based on statistical analysis
- ✅ Reproducible (same query always returns same reasoning)

---

## Use Case 3: "Could this liver enzyme spike be from methotrexate?"

### Current Approach (Flat Timeline)

```python
# Find liver enzyme spike
ast_events = db.execute("""
    SELECT * FROM ehr.patient_timeline
    WHERE patient_id = %s
      AND event_type = 'lab'
      AND structured->>'test_name' = 'AST'
    ORDER BY ts DESC
    LIMIT 1
""", (patient_id,))

ast_event = ast_events[0]
ast_value = float(ast_event["structured"]["value"])
ast_ts = ast_event["ts"]

# Find recent MTX events
mtx_events = db.execute("""
    SELECT * FROM ehr.patient_timeline
    WHERE patient_id = %s
      AND event_type = 'med'
      AND text ILIKE '%methotrexate%'
      AND ts < %s
      AND ts > %s - INTERVAL '8 weeks'
    ORDER BY ts DESC
""", (patient_id, ast_ts, ast_ts))

# Heuristic: if MTX dose changed recently, attribute causality
if mtx_events and mtx_events[0]["ts"] > ast_ts - timedelta(days=30):
    explanation = f"AST spike ({ast_value}) may be related to recent MTX event"
else:
    explanation = "AST spike cause unclear"

# Problems:
# - No confidence measure
# - Ignores other potential causes (other meds, infections, etc.)
# - No consideration of dose-response relationship
# - No guideline/research context
```

### PTV Approach (Multi-Hop Causal Traversal)

```python
ptv = PatientTimelineVision.load(patient_id)

# Find AST spike event
ast_event = ptv.find_event(
    event_type=EventType.LAB,
    structured_filter={"test_name": "AST", "value": [">", 100]},
    order_by="timestamp DESC",
    limit=1
)[0]

# Traverse backward to find CAUSAL_POSSIBLE/LIKELY edges
causal_sources = ptv.traverse_backward(
    start_event_id=ast_event.event_id,
    edge_types=[RelationshipType.CAUSAL_LIKELY, RelationshipType.CAUSAL_POSSIBLE],
    max_hops=2,
    min_strength=0.3  # Include weaker edges for differential
)

# Sort by edge strength (most likely causes first)
causal_sources_with_scores = []
for path in causal_sources:
    if len(path) >= 2:
        source_event = path[-1]  # Last event in backward path
        edge = ptv.find_edges(
            source_event_id=source_event.event_id,
            target_event_id=ast_event.event_id
        )[0]
        causal_sources_with_scores.append({
            "event": source_event,
            "edge": edge,
            "strength": edge.strength,
            "confidence": edge.confidence
        })

causal_sources_with_scores.sort(key=lambda x: x["strength"], reverse=True)

# Generate differential explanation
explanation = f"AST spike to {ast_event.structured['value']} U/L. Possible causes (ranked):\n"

for i, item in enumerate(causal_sources_with_scores[:5], 1):
    event = item["event"]
    edge = item["edge"]
    
    explanation += f"""
    {i}. {event.event_subtype} (event {event.event_id})
       - Timestamp: {event.timestamp} ({(ast_event.timestamp - event.timestamp).days} days before)
       - Causal strength: {edge.strength:.2f}
       - Confidence: {edge.confidence:.2f}
       - Mechanism: {edge.annotations.get('causal_mechanism', 'unspecified')}
       - Discovered by: {', '.join(edge.discovered_by)}
       """
    
    if event.event_subtype == "Methotrexate":
        # Check for dose-response relationship
        dose_info = event.structured.get("dose")
        prior_ast = ptv.find_closest_prior_event(
            reference_event=event,
            event_type=EventType.LAB,
            structured_filter={"test_name": "AST"}
        )
        if prior_ast and dose_info:
            explanation += f"       - Dose: {dose_info}, Prior AST: {prior_ast.structured['value']} (dose-response evident)\n"

# Add guideline context
if any(item["event"].event_subtype == "Methotrexate" for item in causal_sources_with_scores):
    explanation += "\nGuideline context: ACR 2021 RA guidelines recommend MTX monitoring every 4-12 weeks (doc_handle: acr_ra_2021_monitoring)"

# Result:
# "AST spike to 145 U/L. Possible causes (ranked):
#  1. Methotrexate dose increase (event evt_750)
#     - Timestamp: 2024-03-01 (21 days before)
#     - Causal strength: 0.85
#     - Confidence: 0.78
#     - Mechanism: dose-dependent hepatotoxicity
#     - Discovered by: M22 (care planning), M4 (signal tagging)
#     - Dose: 25mg weekly, Prior AST: 28 U/L (dose-response evident)
#  2. Alcohol consumption event (event evt_762)
#     - Causal strength: 0.42
#     - Confidence: 0.60
#     - Mechanism: additive hepatotoxic effect
#  3. Azathioprine coadministration (event evt_735)
#     - Causal strength: 0.38
#     - Confidence: 0.55
#  
#  Guideline context: ACR 2021 RA guidelines recommend MTX monitoring..."
```

**Benefits:**
- ✅ Multi-causal reasoning (shows all possible causes, ranked)
- ✅ Confidence + strength scores from modules
- ✅ Temporal and dose-response context
- ✅ Guideline integration
- ✅ Explainable provenance (which modules identified causality)

---

## Use Case 4: "Show me the full story of this patient's RA journey"

### Current Approach (Flat Timeline)

```python
# Query everything, sort by time
all_events = db.execute("""
    SELECT * FROM ehr.patient_timeline
    WHERE patient_id = %s
    ORDER BY ts
""", (patient_id,))

# Generate narrative (linear, no structure)
narrative = []
for event in all_events:
    if event["event_type"] == "lab":
        narrative.append(f"{event['ts']}: Lab {event['structured']['test_name']} = {event['structured']['value']}")
    elif event["event_type"] == "med":
        narrative.append(f"{event['ts']}: Medication event: {event['text']}")
    elif event["event_type"] == "note":
        narrative.append(f"{event['ts']}: Clinical note: {event['text'][:100]}...")

# Result: Wall of text, no inflection points, no causal structure
story = "\n".join(narrative)
```

### PTV Approach (Graph-Guided Narrative)

```python
ptv = PatientTimelineVision.load(patient_id)

# Identify inflection points (marked by M1 during terrain analysis)
inflection_points = ptv.find_events(
    annotation_filter={"is_inflection_point": True}
)

# Identify major clinical arcs (composite nodes for episodes)
clinical_arcs = ptv.find_events(
    event_type=EventType.RISK_FLAG,
    event_subtype__in=["flare_episode", "remission_period", "diagnostic_uncertainty"]
)

# Build structured narrative around arcs and inflection points
narrative_sections = []

for arc in sorted(clinical_arcs, key=lambda e: e.timestamp):
    section = {
        "title": f"{arc.event_subtype.replace('_', ' ').title()} ({arc.timestamp.date()})",
        "summary": arc.annotations.get("clinical_summary", ""),
        "key_events": [],
        "outcomes": []
    }
    
    # Find constituent events via COMPOSITE edges
    constituent_edges = ptv.find_edges(
        source_event_id=arc.event_id,
        relationship_type=RelationshipType.COMPOSITE
    )
    
    for edge in constituent_edges:
        constituent_event = ptv.nodes[edge.target_event_id]
        section["key_events"].append({
            "type": constituent_event.event_type,
            "subtype": constituent_event.event_subtype,
            "timestamp": constituent_event.timestamp,
            "summary": constituent_event.text[:200]
        })
    
    # Find outcomes (events caused by this arc)
    outcome_edges = ptv.find_edges(
        source_event_id=arc.event_id,
        relationship_type=RelationshipType.CAUSAL_LIKELY,
        min_strength=0.6
    )
    
    for edge in outcome_edges:
        outcome_event = ptv.nodes[edge.target_event_id]
        section["outcomes"].append({
            "event": outcome_event.event_subtype,
            "timestamp": outcome_event.timestamp,
            "causal_strength": edge.strength
        })
    
    narrative_sections.append(section)

# Generate readable narrative
story = "# Patient RA Journey\n\n"
for i, section in enumerate(narrative_sections, 1):
    story += f"## Arc {i}: {section['title']}\n\n"
    story += f"{section['summary']}\n\n"
    
    story += "### Key Events:\n"
    for event in section["key_events"]:
        story += f"- **{event['timestamp'].date()}**: {event['subtype']} - {event['summary']}\n"
    
    if section["outcomes"]:
        story += "\n### Clinical Impact:\n"
        for outcome in section["outcomes"]:
            story += f"- Led to {outcome['event']} on {outcome['timestamp'].date()} (causal_strength={outcome['causal_strength']:.2f})\n"
    
    story += "\n---\n\n"

# Result: Structured narrative with causal flow and inflection points
```

**Benefits:**
- ✅ Narrative structured around clinical arcs (not flat chronology)
- ✅ Inflection points highlighted
- ✅ Causal relationships embedded in story
- ✅ Outcomes linked to triggers
- ✅ Readable by clinicians and patients

---

## Use Case 5: "Compare this patient to similar cases"

### Current Approach (Flat Timeline)

```python
# Compute embedding for entire timeline (crude)
patient_timeline_text = " ".join([e["text"] for e in all_events])
query_embedding = embed_text(patient_timeline_text)

# Search for similar patients
similar_patients = vector_db.search(query_embedding, k=5)

# Result: Similarity based on crude text concatenation
# - No structure (flare patterns, med sequences, etc.)
# - No explanation of why similar
# - Hard to learn from similar cases
```

### PTV Approach (Graph-Aware Case Retrieval)

```python
ptv = PatientTimelineVision.load(patient_id)

# Extract signature features from graph structure
patient_signature = {
    "flare_pattern": {
        "frequency": len(ptv.find_events(event_subtype="flare_episode")) / patient_years,
        "typical_severity": np.mean([e.structured["severity"] for e in flare_episodes]),
        "seasonal": ptv.metadata.get("seasonal_pattern_detected", False)
    },
    "medication_trajectory": {
        "dmard_sequence": extract_med_sequence(ptv, drug_class="DMARD"),
        "biologic_use": any(is_biologic(e.event_subtype) for e in med_events),
        "steroid_dependence": compute_steroid_dependence(ptv)
    },
    "diagnostic_landscape": {
        "primary_diagnosis": ptv.find_events(event_type=EventType.DIAGNOSIS)[0].event_subtype,
        "uncertainty_score": ptv.metadata.get("diagnostic_landscape_entropy", 0),
        "overlapping_syndromes": [...]
    },
    "terrain_profile": {
        "chronic_baseline": ptv.metadata.get("terrain_chronic_baseline", ""),
        "flare_stack_depth": ptv.metadata.get("max_flare_stack_depth", 0),
        "organ_involvement": [...]
    }
}

# Generate graph-aware embedding (includes structure, not just text)
graph_embedding = ptv.generate_graph_aware_embedding(
    include_node_types=[EventType.LAB, EventType.MED, EventType.SYMPTOM],
    include_edge_types=[RelationshipType.CAUSAL_LIKELY, RelationshipType.TEMPORAL_WINDOW],
    weight_by_annotations={"flare_signal_strength": 2.0, "terrain_band": 1.5}
)

# Search for similar cases
similar_cases = case_analog_db.search(
    query_embedding=graph_embedding,
    query_signature=patient_signature,
    k=5,
    require_structural_similarity=True  # Not just text similarity
)

# Explain similarity for each match
for case in similar_cases:
    similarity_report = ptv.compare_to_case(
        other_patient_id=case["patient_id"],
        comparison_dimensions=["flare_pattern", "med_trajectory", "terrain"]
    )
    
    print(f"""
    Case {case['patient_id']} (similarity={case['score']:.2f}):
    
    Flare Pattern:
      - Your patient: {patient_signature['flare_pattern']['frequency']:.1f} flares/year
      - This case: {similarity_report['flare_pattern']['other_frequency']:.1f} flares/year
      - Similarity: {similarity_report['flare_pattern']['similarity']:.2f}
    
    Medication Trajectory:
      - Shared DMARD sequence: {similarity_report['med_trajectory']['shared_sequence']}
      - Both used biologics: {similarity_report['med_trajectory']['both_biologics']}
      - Similarity: {similarity_report['med_trajectory']['similarity']:.2f}
    
    Terrain Profile:
      - Similar chronic baseline: {similarity_report['terrain']['baseline_match']}
      - Max flare stack depth: your={patient_signature['terrain_profile']['flare_stack_depth']}, theirs={similarity_report['terrain']['other_stack_depth']}
      - Similarity: {similarity_report['terrain']['similarity']:.2f}
    
    Key Learnings:
      - This case's outcome: {similarity_report['outcome']}
      - Treatment that worked: {similarity_report['successful_treatment']}
      - Time to remission: {similarity_report['time_to_remission']} months
    """)
```

**Benefits:**
- ✅ Structural similarity (not just text matching)
- ✅ Explainable similarity (shows why cases match)
- ✅ Graph-aware embeddings capture clinical patterns
- ✅ Actionable learnings from similar cases
- ✅ Can compare specific dimensions (flare, meds, terrain)

---

## Summary: Why PTV Wins

| Clinical Task | Flat Timeline | PatientTimelineVision |
|--------------|---------------|----------------------|
| **Explain decisions** | Manual inference, brittle | Graph traversal, provenance |
| **Detect patterns** | Re-compute each time | First-class SIMILARITY edges |
| **Causal attribution** | Heuristics, no confidence | Explicit CAUSAL edges + scores |
| **Generate narratives** | Linear chronology | Arc-based, structured |
| **Find similar cases** | Text similarity only | Graph structure + semantics |
| **Module integration** | Duplicate data stores | Annotate shared graph |
| **Auditability** | Minimal | Full provenance on nodes/edges |
| **Reasoning complexity** | O(n) scans, manual logic | O(log n) traversal, explicit |

**Bottom line:** PTV transforms patient timelines from **passive data** into **active knowledge** that agents can reason over like an IDE navigates code.

