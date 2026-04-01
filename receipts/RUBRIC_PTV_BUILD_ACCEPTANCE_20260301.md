# PatientTimelineVision (PTV) Build — Concrete Acceptance Rubric

**Filed:** 2026-03-01  
**Purpose:** Determine when a PTV graph is fit for downstream reasoning (probe/gap/report, connascence, clinical summaries) vs candidate-only.

---

## 0. PASS LEVELS (GO/NO-GO)

| Level | Status | Meaning |
|---|---|---|
| ❌ Reject | Not usable | Graph too noisy; do not run reasoning |
| 🟡 Candidate | Exploratory only | OK for discovery, not for decisions |
| 🟢 Accepted (v1.0) | Reasoning-safe | OK for probe/gap/report + enrichment |
| 🔵 Production (v1.1+) | Decision-grade | Stable, auditable, low-entropy graph |

---

## 1. CORE METRICS (HARD GATES)

### 1.1 Timestamp Integrity (CRITICAL)

- **Coverage:** ≥ 95% of clinical events have non-unknown timestamps
- **Confidence:** ≥ 85% are `explicit_on_line` or `section_anchored` (not `header_guess`)
- **Plausibility:**
  - ≤ 0.5% future/implausible dates
  - No mass clustering of identical dates from problem-list "as of" artifacts

**Gate:**

| Coverage | Result |
|---|---|
| < 90% | ❌ Reject |
| 90–95% | 🟡 Candidate |
| ≥ 95% | 🟢 Accept |

---

### 1.2 Event-Type Accuracy

- Mis-typed events (e.g., vaccine as `lab`, diagnosis as `lab`) ≤ 5%
- Section-consistent typing (Problem List→`diagnosis`, Immunizations→`immunization`/`procedure`) ≥ 95%

**Gate:**

| Mis-typed Rate | Result |
|---|---|
| > 10% | ❌ Reject |
| 5–10% | 🟡 Candidate |
| ≤ 5% | 🟢 Accept |

---

### 1.3 Deduplication

- Duplicate rate (same normalized event repeated across pages) ≤ 10%
- High-value duplicates (med lists, vaccines) collapsed to canonical nodes

**Gate:**

| Duplicate Rate | Result |
|---|---|
| > 20% | ❌ Reject |
| 10–20% | 🟡 Candidate |
| ≤ 10% | 🟢 Accept |

---

### 1.4 Medication Normalization

- `drug_name` present on ≥ 60% of medication events
- Structured fields (dose/route) on ≥ 40%
- RxNorm (or equivalent) high-confidence matches on ≥ 50% of meds

**Gate:**

| drug_name Coverage | Result |
|---|---|
| < 40% | ❌ Reject |
| 40–60% | 🟡 Candidate |
| ≥ 60% | 🟢 Accept |

---

### 1.5 Graph Connectivity

- Orphan nodes ≤ 30% of total events
- Avg edges per clinical node ≥ 3
- Key relations present: `temporal`, `treatment`, `diagnostic` across major clusters

**Gate:**

| Orphan Rate | Result |
|---|---|
| > 50% | ❌ Reject |
| 30–50% | 🟡 Candidate |
| ≤ 30% | 🟢 Accept |

---

## 2. STRUCTURAL QUALITY (SOFT GATES)

### 2.1 Section Awareness

Events respect source sections:
- **Problem List** → `diagnosis` (chronic, no single date)
- **Immunizations** → `immunization`/`procedure` with date
- **Current Medications** → `medication` (often no single start date)

| Score | Result |
|---|---|
| Poor | ❌ |
| Mixed | 🟡 |
| Consistent | 🟢 |

---

### 2.2 Timestamp Attribution Quality

Each event must carry:

```json
"timestamp_source": "explicit_on_line | section_anchored | header_guess | unknown"
```

Targets:
- `explicit_on_line` + `section_anchored` ≥ 85%
- `header_guess` ≤ 10%

---

### 2.3 Clinical Plausibility Checks

- No impossible sequences (e.g., treatment before diagnosis without explanation)
- No "future cascades" (many diagnoses on same future date)
- Chronic conditions not stamped with identical single-day timestamps unless justified

---

### 2.4 Vocabulary / Ontology Hygiene

- Reduce "Other" bucket over time
- Map common diagnoses to controlled terms where possible
- Avoid mixing narrative text into structured fields

---

## 3. BEHAVIORAL VALIDATION (REQUIRED)

### 3.1 Probe Quality

- Top-k results contain relevant clinical nodes, not page boilerplate
- Mixed retrieval (semantic + TS) yields overlapping signal, not divergence

---

### 3.2 Gap Detection Quality

Enrichment targets are meaningful:
- Missing timestamps
- Missing drug names
- Zero-edge clinical nodes
- Not dominated by page artifacts

---

### 3.3 Enrichment Impact (MANDATORY)

Run 1-cycle mutation: **Before → After**

Required:
- ≥ 3 meaningful nodes improved (not page nodes)
- Edges added are clinically relevant (`temporal`/`treatment`/`diagnostic`)

---

### 3.4 Answer Delta (MANDATORY FOR v1.0)

Same query: **PRE** (no enrichment) vs **POST** (enrichment enabled)

Targets:
- POST wins ≥ 80% of steps
- Improvement score ≥ +5/10 average
- Temporal references increase
- Specific diagnoses/therapies increase

---

## 4. AUTOMATED CHECKS (IMPLEMENTABLE)

### 4.1 Duplicate Hash

```python
hash = (normalized_preview, normalized_drug, normalized_date)
```

Collapse clusters with same hash.

---

### 4.2 Date Validator

Reject:
- `current_date + 30 days`
- Identical date across > 10 diagnoses in same section

Flag as `header_guess` or `problem_list_as_of`.

---

### 4.3 Type Repair Rules

```
Contains "vaccination", "vaccine"  →  immunization/procedure
Contains known diagnoses list      →  diagnosis
Contains drug pattern              →  medication
```

---

### 4.4 Section Parser (lightweight)

Detect headers:
- `"Current Medications"`
- `"Problem List"`
- `"Immunizations"`

Use to constrain extraction event typing and date semantics per section.

---

## 5. ACCEPTANCE CHECKLIST (OPERATOR)

Before promoting a PTV build:

- [ ] Timestamp coverage ≥ 95%
- [ ] Mis-typed events ≤ 5%
- [ ] Duplicate rate ≤ 10%
- [ ] Medication normalization ≥ 60%
- [ ] Orphan nodes ≤ 30%
- [ ] Section-aware extraction present
- [ ] Enrichment adds meaningful nodes
- [ ] Answer delta shows improvement

---

## 6. INTERPRETATION TIERS

### ❌ Reject
- "Unknown" timestamps dominate
- Graph mostly page artifacts
- Temporal reasoning impossible

### 🟡 Candidate
- Useful for exploration
- Needs repair passes
- Do NOT trust chronology

### 🟢 Accepted (v1.0)
- Reliable temporal backbone
- Moderate semantic quality
- Safe for reasoning + enrichment

### 🔵 Production (v1.1+)
- Low duplication
- High ontology coverage
- Causal reasoning begins to stabilize

---

## FINAL LINE

A PTV build is not accepted when it "extracts a lot."  
It is accepted when **time, type, and structure are reliable enough that reasoning improves when the graph changes.**

---

## NEXT STEPS

- [ ] Turn into a script that auto-scores every build against these gates
- [ ] Integrate into PortalVision Coverage Guard / invariant system
