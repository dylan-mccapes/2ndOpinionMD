# PortalVision Pipeline Receipt — Full Run (GPT-4.1 Baseline)
**Date:** 2026-03-27  
**Run artifact dir:** `timeline_full_20260327_1717`  
**Model:** gpt-4.1 (ingestion + summarization)  
**Extraction mode:** full (4,223/4,223 pages)

---

## Executive Verdict

> **✅ System is operational and meaningful**  
> **⚠️ Two structural issues + one philosophical misalignment remain**

Not a prototype. A working epistemic engine over medical time.

---

## 1. Ingestion → Graph: Structurally Sound

| Metric | Value |
|--------|-------|
| Events extracted | 4,668 |
| Edges after connascence | 57,672 |
| Avg edges per event | ~12.3 |
| Edge types present | temporal, treatment, diagnostic, lab_trend |
| Events reclassified from generic type | 1,944 |

Key observation: ABNL MRI (2016) correctly propagates forward across dozens of events. Chronic conditions persist with longitudinal linkage. This is not extraction — this is **state reconstruction**.

---

## 2. Critical Pipeline Issues (Status)

### ❌ Issue A — JSON Decode Failure (LLM Connascence)
**Error:** `JSONDecodeError: Unterminated string starting at line 295`  
**Root cause:** `max_tokens=4096` too small for 228-event connascence batch (~12K+ tokens of edge JSON)  
**Impact:** Diagnostic connascence batch 1/4 skipped entirely  
**Status: ✅ FIXED** — bumped to `max_tokens=16_384`; added partial JSON recovery via regex to salvage complete edge objects before truncation point

### ❌ Issue B — `gap_analysis` UnboundLocalError
**Error:** `UnboundLocalError: cannot access local variable 'gap_analysis'`  
**Root cause:** Variable never assigned in PDF session mode (no DB pool → gap skipped), but artifact writer still referenced it  
**Impact:** Enrichment artifact write failed; receipt chain broken  
**Status: ✅ FIXED** — initialized `gap_analysis = None` and `enrichment_synthesis = None` at function top; artifact writer now guards with `if gap_analysis is not None`

### ⚠️ Issue C — Silent Skip / Missing Degradation Metadata
**Observation:** `"skipping batch"` logged but not recorded in output artifacts  
**Impact:** Graph is non-deterministically incomplete without a receipt of the incompleteness  
**Status: 🔧 PENDING** — need to add `degradation` block to vision metadata:
```json
{
  "degradation": {
    "connascence_batches_failed": 1,
    "connascence_type": "diagnostic",
    "edges_missing_estimate": "unknown"
  }
}
```

---

## 3. Graph Quality Assessment

### What works
- Dense, connected, longitudinal
- Multi-domain edge typing
- Scale integrity: 4,223 pages → no collapse

### What is missing
- **No prioritization layer** — anemia (2024) has equal weight to eczema; PCI (2025) equal to minor symptom
- This is where the **fragility axis** (backwards embedding) belongs

---

## 4. Clinical Interpretation (System-Level)

The system implicitly discovered three **causal ambiguity clusters**:

| Cluster | Events |
|---------|--------|
| Neuromuscular ambiguity | MG vs spine vs neuropathy |
| Systemic decline | ILD + immunosuppression + infection risk |
| Hematologic unknown | Anemia with no identified source |

This is the theory in action: `entropy = unresolved branching of explanation`. The graph encodes that entropy structurally.

---

## 5. System State Summary

| Layer | Status |
|-------|--------|
| Ingestion | ✅ Strong |
| Graph construction | ✅ Strong |
| Connascence (mechanical) | ✅ Strong |
| Connascence (LLM diagnostic) | ⚠️ Partial — 1/4 batches failed this run |
| Enrichment artifact write | ⚠️ Failed this run (fixed for next) |
| Summarization | ✅ Strong |
| Degradation accounting | ❌ Not yet implemented |
| Decision support / fragility axis | ❌ Not yet |

---

## 6. Limitation (Honest)

Still **forward descriptive, not backward corrective**:
- Graph explains what happened
- Does not yet identify: what to measure next, what would collapse uncertainty

---

## 7. Next Step (Critical Path)

Backwards embedding on this patient:
1. Select outcome nodes: anemia, functional decline, PCI → hospice
2. Monte Carlo: perturb labs, diagnoses, treatments
3. Compute: which inputs most affect outputs
4. Re-embed as `fragility_axis`

Target output:
```json
{
  "fragility_axis": [
    "iron_deficiency_anemia",
    "medication_nonadherence",
    "pulmonary_fibrosis_progression"
  ]
}
```
