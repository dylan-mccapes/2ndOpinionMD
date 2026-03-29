# Patient Timeline Connascence Rubric

**Version:** 0.2  
**Status:** Mechanical + LLM (batched, fixed format)  
**Purpose:** Define explicit, auditable rules for inferring edges between timeline events

---

## Connascence Types

### 1. Temporal Connascence (`temporal`)

**Definition:** Events that occur close in time, suggesting temporal clustering or shared context.

**Rule (v0.2 — two windows):**
```
SHORT WINDOW (≤30 days): any two events → temporal edge
EPISODE WINDOW (31–90 days): only cross-type pairs (e.g. lab + diagnosis, not lab + lab)
```

**Parameters:**
- Short window: 30 days (tight clinical episode, same hospitalization, same flare)
- Episode window: 31–90 days, cross-type only (avoids noise from same-test repetition)
- Bidirectional: Yes (A→B and B→A)

**v0.1 was:** 7 days. Too narrow for multi-decade chronic disease records.

**Examples:**
- Lab test on 2024-01-15 + Diagnosis on 2024-01-18 → temporal (short window)
- Medication start on 2024-02-01 + Symptom note on 2024-02-28 → temporal (short window)
- Diagnosis on 2024-01-01 + Lab on 2024-03-15 → temporal (episode window, cross-type)
- Lab A on 2024-01-01 + Lab B on 2024-02-28 → NO edge (same type, episode window)

**Rationale:**
Events within a month typically reflect the same clinical episode. 30–90 day cross-type
pairs often represent diagnostic workup → result → treatment chains.

---

### 2. Diagnostic Connascence (`diagnostic`)

**Definition:** Events related to the same diagnosis, condition, or clinical problem.

**Rule (Phase 1 - LLM-Based Inference):**
```
GIVEN: All events where event_type IN ("diagnosis", "procedure")
ASK GPT-5.1: "Which of these events describe the same clinical condition?"
PRECISION REQUIREMENT: Only link if LLM confirms semantic equivalence
THEN add_edge(event_a, event_b, type="diagnostic")
```

**Parameters:**
- Inference method: GPT-4o / GPT-5.1 (temperature=0.0 for precision)
- Bidirectional: Yes
- Rubric provided to LLM as context
- Reasoning logged for each edge

**Examples:**
- "Myasthenia Gravis" diagnosis + "MG exacerbation" note → diagnostic edge (LLM confirms: same condition)
- "ICD-10: M35.9" + "Connective tissue disease" → diagnostic edge (LLM confirms: M35.9 is CTD code)
- "Pneumonia" + "Myasthenia Gravis" → NO edge (LLM confirms: different conditions)

**Why LLM vs. Mechanical:**
- Handles abbreviations (MG = Myasthenia Gravis)
- Handles ICD code → condition name mapping
- Avoids false positives from keyword overlap (e.g., "connective" in unrelated contexts)
- Provides reasoning for auditability

**Rationale:**
Events describing the same condition should cluster together for question-driven views.

---

### 3. Lab Trend Connascence (`lab_trend`)

**Definition:** Sequential measurements of the same lab test over time.

**Rule (Phase 1 - LLM-Based Inference):**
```
GIVEN: All events where event_type == "lab"
ASK GPT-5.1: "Which labs measure the same test (e.g., all Creatinine, all Hemoglobin)?"
PRECISION REQUIREMENT: Only link if LLM confirms same test, accounting for abbreviations
THEN add_edge(event_a, event_b, type="lab_trend") for all pairs measuring same test
```

**Parameters:**
- Inference method: GPT-4o / GPT-5.1 (temperature=0.0 for precision)
- Directional: Yes (earlier → later in time)
- Bidirectional for navigation: Yes (but semantically directional)
- Rubric provided to LLM as context
- Reasoning logged for each edge

**Examples:**
- "Creatinine 1.2 mg/dL" (2024-01-15) → "Cr 1.8" (2024-02-20) → lab_trend edge (LLM knows: Cr = Creatinine)
- "Hemoglobin 10.2" (2024-03-01) → "Hgb 9.8" (2024-03-15) → lab_trend edge (LLM knows: Hgb = Hemoglobin)
- "Creatinine" + "Glucose" → NO edge (LLM confirms: different tests)

**Why LLM vs. Mechanical:**
- Handles abbreviations (Cr = Creatinine, Hgb = Hemoglobin, WBC = White Blood Cell)
- Handles synonyms (Hemoglobin = Hb = Hgb)
- Avoids false positives from name collisions
- Provides reasoning for auditability

**Rationale:**
Tracking the same lab over time reveals progression, treatment response, or worsening.

---

### 4. Treatment Connascence (`treatment`)

**Definition:** Events linked by treatment → response (medication → labs, symptoms, outcomes).

**Rule (v0.2):**
```
IF event_a.event_type IN ("medication", "med", "rx", "drug", "prescription")
AND event_b.event_type IN ("lab", "symptom", "note", "imaging")
AND 0 <= (event_b.timestamp - event_a.timestamp).days <= 60
THEN add_edge(event_a, event_b, type="treatment")
```

**Parameters:**
- Window: 0-60 days (extended from 30 to catch biologic/immunosuppressant responses)
- Med types: medication, med, rx, drug, prescription (v0.1 missed "drug", "prescription")
- Response types: added "imaging" (post-treatment scans are common)
- Directional: Yes (medication → response)
- Bidirectional for navigation: Yes

**Examples:**
- "Prednisone 60mg started" (2024-01-10) → "CRP decreased to 5" (2024-01-25) → treatment edge
- "Methotrexate initiated" (2024-02-01) → "Symptom improvement noted" (2024-02-28) → treatment edge

**Future Enhancement (Phase 2):**
- Drug-specific windows (e.g., biologics take longer)
- Expected lab changes per medication (e.g., MMF → WBC monitoring)
- Adverse event detection (med → symptom escalation)

**Rationale:**
Linking medications to downstream labs/symptoms enables treatment response analysis.

---

## Implementation Status

### v0.2: Current Implementation
- ✅ Temporal connascence (≤30 days all types; 31–90 days cross-type) - **Mechanical**
- ✅ Diagnostic connascence - **LLM batched (GPT-4.1, 300 events/batch)**
- ✅ Lab trend connascence - **LLM batched (GPT-4.1, 300 events/batch)**
- ✅ Treatment connascence (med → response 0-60 days, extended type sets) - **Mechanical**

**v0.1 bugs fixed in v0.2:**
- Temporal window too narrow (7d → 30d short + 90d episode)
- LLM prompt format conflict: said "return a list" but json_object forces an object → always returned 0 edges
- LLM batching: sampled 200 events evenly across all types → most events never seen; now batched per-type at 300/batch
- Treatment window too narrow (30d → 60d)
- Treatment type set incomplete (added "drug", "prescription", "imaging")

### Phase 1.5: Next (Future)
- [ ] LOINC/ICD code awareness
- [ ] Confidence scores per edge
- [ ] Episode clustering (same hospitalization grouping)

### Phase 2: Advanced Causal Inference (Future)
- [ ] Causal connascence (did medication *cause* lab change?)
- [ ] Symptom → diagnosis linking
- [ ] Procedure → outcome linking
- [ ] Adverse event detection

---

## Reserved Connascence Types (Not Yet Implemented)

### 5. Causal Connascence (`causal`)
**Definition:** Event A directly caused or triggered Event B.
**Status:** Reserved for Phase 2 (requires LLM or explicit causal markers)

### 6. Symptom Cluster Connascence (`symptom_cluster`)
**Definition:** Related symptoms occurring together (e.g., fatigue + fever + weight loss).
**Status:** Reserved for Phase 2

---

## Edge Properties

All connascence edges include:
- `connascence_type`: One of the types defined above
- `inferred_by`: "mechanical_v01" (for Phase 1 rules)
- `confidence`: Not yet implemented (future: 0.0-1.0 score)
- `bidirectional`: True for most types (enables navigation in both directions)

---

## Validation Metrics

For a timeline with N events:

**Expected Edge Counts (Order of Magnitude):**
- Temporal: ~N/5 to N/2 (depends on density of episodes)
- Diagnostic: ~N/10 to N/5 (if multiple mentions of same condition)
- Lab trend: ~N/20 to N/10 (if repeated lab monitoring)
- Treatment: ~N/10 to N/5 (if medications are tracked)

**Sanity Checks:**
- No self-edges (event → itself)
- No duplicate edges (same type between same events)
- Edge counts logged for inspection

---

## Usage in Code

**Location:** `server/eoh/timeline_summarizer.py`

**Function:** `_enrich_timeline_vision_connascence()`

**Integration:**
- Called automatically after PDF import in `summarize_timeline_from_pdf()`
- Operates on `PatientTimelineVision` object
- Updates `TimelineEventVision.connascence` dicts
- Re-saves enriched vision with edges

**Logging:**
```python
logger.info(
    "PatientTimelineVision enriched: %s (events=%d, edges=%d)",
    vision_path,
    len(vision.events),
    vision.count_edges()
)
```

---

## Rubric Updates

**How to update this rubric:**
1. Document the new rule here first
2. Update implementation in `timeline_summarizer.py`
3. Update `PATIENT_TIMELINE_VISION_NOTES.md` with cross-reference
4. Increment version number

**Version History:**
- v0.1 (2026-01-19): Initial implementation (temporal & treatment mechanical, diagnostic & lab_trend LLM-based)
- v0.2 (2026-03-27): Fixed LLM format bug (0 edges → batched), expanded windows, extended type sets, sorted temporal pass

---

## References

- `patient_timeline_vision.py`: Defines `PatientTimelineVision` and `TimelineEventVision`
- `timeline_summarizer.py`: Implements `_enrich_timeline_vision_connascence()`
- `PATIENT_TIMELINE_VISION_NOTES.md`: Architecture notes

**Boring. Legible. Obvious.** 🫡

