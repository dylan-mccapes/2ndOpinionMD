# 2OPMD UX Invariants

**Version:** 1.0  
**Date:** 2025-01-02  
**Status:** Normative

---

## Purpose

This document defines the non-negotiable interface constraints for 2ndOpinionMD.

These invariants exist to prevent **interface collapse**: the gradual erosion of system truth through convenience features, implicit state mutation, and mode boundary violations.

Violation of these invariants indicates a design error, not a feature opportunity.

---

## System Principles

1. **UX follows system truth, not user preference.**
2. **State mutation must be explicit, observable, and reversible where possible.**
3. **Demonstration > explanation.**
4. **Convenience is the primary entropy vector and must be resisted.**
5. **Operators are sovereign, competent, and allowed to fail.**
6. **The system must remain honest regardless of operator action.**

---

## Mode Architecture

The system provides exactly **four orthogonal modes**. These are:

1. **ask** — Read-only clinical Q&A
2. **coding** — Medical coding and classification
3. **EoH** — Single Ethos-of-Health reasoning run
4. **EoHD** — Timeline-aware Ethos-of-Health Detective run

### Mode Orthogonality

- Modes do not share state.
- Modes do not auto-transition.
- Modes do not suggest or recommend other modes.
- Mode selection is explicit operator action only.

### Mode Non-Features

The following do **not** exist:

- Mode history or "recently used"
- Mode recommendations based on query content
- Mode shortcuts or aliases
- Composite modes or mode chaining
- Background execution in non-selected modes

---

## Mode Specifications

### Mode: `ask`

**What it does:**
- Accepts a clinical question in natural language
- Returns a structured clinical response
- Cites evidence sources when available
- Surfaces uncertainty explicitly when evidence is weak or contradictory

**What it refuses:**
- State mutation of any kind
- Personalization or "learning" from previous queries
- Medical coding or classification
- Timeline analysis or detective reasoning
- Multi-turn conversation or context retention

**Observable behavior:**
- Query submitted → response rendered → done
- No session ID, no history, no carry-over
- Each query is independent and stateless

**Failure modes:**
- Query cannot be processed → error displayed with reason
- Evidence unavailable → response states "no evidence retrieved"
- Ambiguous query → system asks for clarification (once) or refuses with explanation
- Timeout → operator notified, no partial results shown

**Recovery:**
- Operator may rephrase query
- Operator may select different mode
- Operator may abandon query (no cleanup required)

---

### Mode: `coding`

**What it does:**
- Accepts clinical text (symptom, diagnosis, procedure description)
- Returns structured medical codes: ICD-10-CM, ICD-11, SNOMED CT, LOINC, RxNorm as applicable
- Surfaces confidence scores per code
- Allows explicit rejection of suggested codes
- Allows explicit acceptance of suggested codes
- Exports final code set only after explicit operator confirmation

**What it refuses:**
- Auto-application of codes
- Code suggestion without confidence scores
- Code modification after export
- Timeline integration
- Diagnostic reasoning (beyond code mapping)

**Observable behavior:**
- Clinical text submitted → candidate codes displayed with confidence
- Operator reviews, accepts, or rejects each code explicitly
- Operator confirms export → code set finalized and displayed
- No codes are "applied" or "saved" — only exported for operator use

**Failure modes:**
- No matching codes found → empty result with explanation
- Ambiguous input → multiple code sets offered, operator must choose or refine
- Confidence too low on all candidates → system refuses to suggest, requests more specific input
- Export attempted before confirmation → blocked with explanation

**Recovery:**
- Operator may refine input text
- Operator may reject all codes and restart
- Operator may abandon session (no side effects)

---

### Mode: `EoH`

**What it does:**
- Accepts a clinical scenario (symptoms, history, context)
- Executes a single Ethos-of-Health reasoning cycle
- Returns: hypothesis set, evidence weighting, suggested next steps
- Surfaces reasoning provenance (which modules fired, why)
- Allows operator to export results

**What it refuses:**
- Timeline integration (use EoHD for that)
- Multi-cycle iteration or refinement within the same run
- State mutation or learning
- Auto-escalation to EoHD
- Background execution

**Observable behavior:**
- Scenario submitted → reasoning executes (progress visible) → results displayed
- Operator reviews results
- Operator may export results (explicit action)
- Operator may abandon (no side effects)

**Failure modes:**
- Insufficient input → system refuses with required fields listed
- Reasoning timeout → partial results not shown, operator notified
- Module failure during reasoning → error surfaced with failed module name
- No hypotheses generated → system states this explicitly, no fallback behavior

**Recovery:**
- Operator may add more detail to scenario and resubmit
- Operator may switch to `ask` mode for clarification
- Operator may abandon

---

### Mode: `EoHD`

**What it does:**
- Accepts a clinical scenario + timeline data (journal entries, symptom progression, events over time)
- Executes timeline-aware Ethos-of-Health Detective reasoning
- Returns: temporal hypothesis evolution, inflection points, evidence across time
- Surfaces detective reasoning provenance
- Allows operator to export timeline analysis

**What it refuses:**
- Single-point-in-time analysis (use EoH for that)
- Timeline modification or editing
- State mutation
- Auto-suggestion of additional timeline entries
- Retrospective "learning" from past runs

**Observable behavior:**
- Scenario + timeline submitted → detective reasoning executes (progress visible) → timeline analysis displayed
- Operator reviews temporal analysis
- Operator may export results (explicit action)
- Operator may abandon (no side effects)

**Failure modes:**
- Insufficient timeline data → system refuses with minimum data requirements stated
- Timeline data contradictory or malformed → error surfaced, operator must fix
- Reasoning timeout → no partial results, operator notified
- No temporal patterns detected → system states this explicitly

**Recovery:**
- Operator may refine timeline data and resubmit
- Operator may switch to simpler `EoH` mode
- Operator may abandon

---

## State Mutation Rules

### What Constitutes State Mutation

State mutation occurs when:

1. Data is written to persistent storage (database, file system, external service)
2. Operator identity or session is recorded
3. Query history is retained
4. Preferences or settings are changed
5. Results influence future queries or suggestions
6. Any side effect occurs outside the immediate request/response cycle

### Permitted State Mutations

**None** within the four modes.

All modes are **read-only** with respect to system state. Results may be **exported** by the operator, but export is a one-way transmission with no feedback loop.

### Prohibited Behaviors

- "Saving for later"
- "Remembering your preferences"
- "Based on your previous queries..."
- Session restoration
- Auto-complete based on history
- Recommended actions based on prior use
- Analytics or telemetry tied to operator identity

### Observability Requirement

If, in the future, state mutation becomes necessary (e.g., for compliance, audit, or billing):

- It must be **explicit** (operator initiates with clear action)
- It must be **observable** (operator sees what was mutated, when, and why)
- It must be **reversible** where technically possible (operator can undo or delete)
- It must be **documented** in this file with rationale and implementation bounds

---

## Operator Actions

Operators may perform **only** the following actions:

1. **Select a mode** (ask, coding, EoH, EoHD)
2. **Submit a query or scenario** (via form or input field)
3. **Review results** (read-only)
4. **Export results** (explicit download or copy action)
5. **Abandon current operation** (close, navigate away, cancel)

### Non-Actions

The following do **not** exist:

- "Save this query"
- "Share with colleague"
- "Email results"
- "Create account" (unless required for billing/compliance, see State Mutation Rules)
- "Compare with previous result"
- "Set as default mode"
- "Customize interface"

---

## Failure and Recovery

### Failure Surfacing

When a failure occurs:

1. **Stop immediately.** No partial results. No fallback behavior.
2. **State the failure plainly.** No softening language. No apologies.
3. **State the cause if known.** "Insufficient input." "Module timeout." "No evidence found."
4. **State available recovery paths.** "Refine query." "Try different mode." "Abandon."

### No Optimistic UI

- Do not show loading spinners for > 2 seconds without progress indication
- Do not show partial results
- Do not grey out or disable controls without explanation
- Do not auto-retry failed requests

### Recovery Paths

Every failure state must offer:

1. **Explicit retry** (if applicable)
2. **Mode switching** (to a potentially more appropriate mode)
3. **Abandonment** (operator regains control, no side effects)

---

## Aesthetic Constraints

### Not This

- Consumer app
- Chat interface
- Marketing surface
- Gamified experience
- Personalized dashboard

### This

- Clinical terminal
- ER / ICU aesthetic
- Life-support system
- Operator console
- Instrument panel

### Visual Language

- High contrast
- Monospaced fonts for data
- No animations except loading indicators
- No gradients or decorative elements
- No color as sole information channel (accessibility requirement)

---

## Enforcement

### How Violations Are Detected

A UX invariant is violated if:

1. A mode performs an action outside its specification
2. State is mutated without explicit operator action
3. Mode boundaries are crossed implicitly
4. Failure is hidden or softened
5. Convenience features introduce implicit behavior

### Resolution Path

When a violation is detected:

1. **Stop.** Do not ship the feature.
2. **Assess.** Is the invariant wrong, or is the feature wrong?
3. **If the invariant is wrong:** Update this document with rationale and review.
4. **If the feature is wrong:** Remove or redesign the feature.

---

## Changelog

### 2025-01-02 — v1.0
- Initial specification
- Four modes defined
- State mutation rules established
- Aesthetic constraints documented

---

## Appendix: Why These Invariants Exist

### The Problem

Clinical software suffers from **interface collapse**: the gradual accumulation of convenience features that obscure system truth, introduce hidden state, and make failure modes unpredictable.

Operators (clinicians, patients, care coordinators) are placed in a position where they cannot trust the interface because:

- It "helps" in ways they did not request
- It "remembers" in ways they cannot audit
- It "suggests" based on logic they cannot inspect
- It fails silently or misleadingly

### The Solution

**Radical simplicity enforced by invariants.**

By constraining the interface to four orthogonal, stateless modes with explicit failure surfacing and no implicit behavior, we ensure:

- Operators always know what the system is doing
- Operators always control what happens next
- Failures are honest and actionable
- The system cannot surprise or mislead

### The Cost

These invariants make the system **less convenient**. That is intentional.

Convenience in clinical software is dangerous when it comes at the cost of observability, control, and honesty.

Operators are competent. They can tolerate inconvenience. They cannot tolerate dishonesty.

---

**End of Specification**

