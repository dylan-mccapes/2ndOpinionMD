# Ingestion Report: EoH Platform Interaction Architecture v0
## AEN_DUMP → 2OPMD Core Documentation

**Date:** 2026-01-31  
**Source:** `game_plans/AEN_DUMP/AEN_DUMP.md`  
**Target:** `2ndOpinionMD-MVP/EOH_PLATFORM_INTERACTION_ARCHITECTURE_V0.md`  
**Document Type:** Canonical Analysis Artifact (Non-Executable, Iterative Baseline)  
**Ingested by:** Claude (Anthropic Sonnet 4.5)

---

## Executive Summary

This document defines the canonical architecture for how all platform surfaces (B2C/2OPMD, B2MD, B2B, B2I) interact with the EoH governed reasoning system. It establishes **authority boundaries**, **HITL ownership**, and **device modalities** without defining implementation details.

**Critical distinction:** This is a **boundary and vocabulary artifact**, not an execution specification. V5.2 remains the execution authority; V6 modules (M55-M61) are referenced only as analysis-level formalizations.

---

## Document Structure

### 1. Core System Anchor (EoH / 1OPMD)

**What the core system IS:**
- ✅ Governed reasoning stack maintaining patient-specific longitudinal truth
- ✅ Tamper-evident, queryable ledger/vault for trajectories, alerts, outcomes, provenance
- ✅ Pattern-based early warning system with clinicians as decision makers
- ✅ Consent and ethical gating enforcement (no bypass permitted)
- ✅ Suppression-aware behavior with explanations and audit hooks
- ✅ Draft-only execution until clinician finalization

**What the core system IS NOT:**
- ❌ Not a UI surface (patient app, clinician portal, governance dashboard)
- ❌ Not a medical-knowledge/guideline engine
- ❌ Not an autonomous executor (all resources require explicit clinician action)
- ❌ Not a platform governance or roadmap authority

**Why all platforms depend on it:**
- System-of-record for patient timeline state
- Consent gating enforcement
- Suppression semantics
- Audit/provenance lineage
- Platforms are surfaces that request role-scoped views and submit events back to governed ledger

---

### 2. Platform Taxonomy (Four Surfaces)

#### B2C / 2OPMD (Patient-facing) 👤

**Audience:** Patients (+ authorized proxy roles)  
**Authority Level:** Reflective / informational; NO clinical-decision authority  

**Can See:**
- Role-filtered narratives and simplified state representations
- Band/stack trajectories in plain language

**Can Do:**
- Submit journaling, mood/tags, feedback, concerns as interaction events
- Input reflective data into governed storage/telemetry

**Must NOT Do:**
- ❌ Must not mutate canonical core state from UI
- ❌ Must not present actions as authoritative without clinician finalization

**Device Surfaces:** Mobile-first; web secondary

---

#### B2MD (Clinician reasoning & judgment) 👨‍⚕️

**Audience:** Clinicians / care teams  
**Authority Level:** Patient-scoped clinical judgment and sign-off authority  

**Can See:**
- Action center view: alerts, forecasts, trajectory cones, psychosomatic context
- Key flags including suppression context

**Can Do:**
- ✅ Confirm/override/annotate outputs via HITL workflows (with audit/provenance)
- ✅ Finalize draft execution artifacts through Module 19 (ONLY place resources become active)
- ✅ Apply suppression controls (pauseFlag/pauseReason) with lifecycle audit

**Must NOT Do:**
- ❌ Must not treat system outputs as guideline facts
- ❌ Must not encode disease knowledge locally
- ❌ Must not activate AI-generated actions autonomously
- ❌ Must not bypass consent/suppression controls

**Device Surfaces:** Web and tablet; embeddable in clinical contexts

---

#### B2B (Organizational / governance) 🏢

**Audience:** Organizational governance operators (quality, safety, oversight)  
**Authority Level:** Governance HITL (oversight/review) WITHOUT patient-level action authority  

**Can See:**
- Read-only audit/QA views: chronological event logs from vault
- Audit/provenance artifacts
- Clinician outcomes for learning/QA
- Disclosure/export governance records (allowed/denied)

**Can Do:**
- ✅ Governance review/sign-off for learning-related actions
- ✅ Read-only inspection (QUERY_ONLY posture)

**Must NOT Do:**
- ❌ Must not perform patient-state mutation
- ❌ Must not bypass consent/suppression
- ❌ Must not autonomously publish, escalate, or execute

**Device Surfaces:** Web (governance/audit review); analytics/report environments

---

#### B2I (Institutional / research) 🔬

**Audience:** Institutional research and federated collaboration consumers  
**Authority Level:** Secondary-use consumer; NO patient-level action authority  

**Can See:**
- Purpose-bound, minimized, de-identified/pseudonymized datasets
- Governed exports with denial semantics and replayability
- Ledger-anchored disclosure records (version-tagged)

**Can Do:**
- ✅ Perform institutional analysis on received exports (outside EoH execution)

**Must NOT Do:**
- ❌ Must not request patient-state mutation rights
- ❌ Must not bypass consent/suppression controls
- ❌ Must not trigger escalation or execution

**Device Surfaces:** Institutional analytics; batch export consumption

---

### 3. Authority & HITL Ownership Model

Three HITL categories with platform ownership:

#### Reflective HITL (B2C / 2OPMD owns)
- **Definition:** Context, preferences, reflections, feedback without collapsing uncertainty into clinical action
- **Examples:** Journaling, mood tags, concerns
- **Invariant:** Reflective HITL outputs are inputs to reasoning, NOT authorizations

#### Patient-Scoped HITL (B2MD owns)
- **Definition:** Actions at patient context that resolve decision tasks, apply overrides, finalize drafts
- **Examples:**
  - Confirm/override/annotate workflows via Module 19
  - Finalization of draft/proposal artifacts
  - Clinician suppression controls with audit lifecycle
- **Invariant:** Only B2MD may collapse uncertainty into patient-level action

#### Governance HITL (B2B owns)
- **Definition:** Oversight/review of system behavior, audit/replay, disclosure/export accounting
- **Examples:**
  - Learning/QA governance sign-offs
  - Replay and audit framing (read-only, cannot influence live execution)
- **Invariant:** No patient-level action authority; read-only posture for inspection

---

### 4. Critical Invariant (System-Wide)

> **"Only B2MD may collapse uncertainty into patient-level action."**

This follows from:
- ✅ Clinicians remain decision makers for alerting outputs
- ✅ Execution artifacts remain draft/proposal until explicit clinician action via Module 19
- ✅ No autonomous activation
- ✅ Shared decision orchestration enforces: "no recommended action becomes authoritative without clinician confirmation via Module 19 and downstream execution guardrails in Module 16"

---

### 5. Interaction Flows (Conceptual)

#### Flow A: Patient Reflection → Governed Ingestion → Longitudinal Truth
1. Patient-facing surfaces collect reflective inputs
2. Emitted as interaction events routed to governed storage/telemetry (Vault/QA/learning)
3. Provenance and actor attribution preserved
4. Consent state constrains all operations (no bypass permitted)

#### Flow B: Core Reasoning → Role-Specific Presentation (Non-Mutative)
1. Core modules produce structured outputs (alerts, trend flags, trajectories, suppression context)
2. Interface hub renders read-only core state
3. Assembles unified timeline from longitudinal vault
4. Applies RBAC/masking and vocabulary guardrails
5. **UI is explicitly non-mutative:** displayed state "cannot be mutated from UI; all actions are routed to upstream modules"

#### Flow C: Clinician Review → Draft Execution → Clinician Finalization
1. Decision tasks arise → interface hub orchestrates bidirectional tasks via Module 19
2. Captures patient concerns and clinician decisions with audit/provenance linkage
3. Execution-layer outputs are proposals/drafts
4. Routed for clinician finalization
5. **System guarantees no autonomous activation**
6. Safety-critical escalations: suppression-aware, auditable, non-interpretive delivery

#### Flow D: Governance Audit/Replay → Learning Governance Boundaries
1. Governance surfaces consume read-only audit/QA views
2. Chronological event log from vault + audit/provenance artifacts
3. **QUERY_ONLY posture:** achievable in V5.2 by non-invocation of compute/escalate/execute/schedule/mutate modules
4. V6 M60 (HARF) constraints:
   - Replay is derived and read-only
   - Audit framing cannot influence live execution
   - No patient-state mutation or consent/suppression bypass

#### Flow E: Research Export → Minimization + Ledger Accounting → Governed Delivery
1. Institutional/research requests mediated by:
   - Consent gate semantics (state/version, overlays, ethical override logging)
   - Purpose-bound minimization and de-identification engine
   - Denial semantics and replayability
2. Ledger-anchored export governance:
   - Every request produces record (including denials)
   - Outputs version-tagged and replay-safe
3. B2I consumes governed exports without gaining patient-action authority

---

### 6. Device & Modality Matrix

| Platform | Mobile | Web | Tablet | Embedded Clinical | Batch/Export/Analytics |
|----------|--------|-----|--------|-------------------|------------------------|
| **B2C / 2OPMD** | Primary | Secondary | Optional | Not typical | Not applicable |
| **B2MD** | Optional | Primary | Common | Common (clinical context embedding) | Optional |
| **B2B** | Rare | Primary | Optional | Not typical | Common (audit/QA review) |
| **B2I** | Rare | Optional | Rare | Not typical | Primary (governed exports) |

**Note:** Role-based embedding for clinicians is supported conceptually (clinical identity and patient context inherited; clinician actions map to interoperable artifacts), without defining implementation details.

---

### 7. Explicit Non-Goals (What This Document Does NOT Define)

This document intentionally does NOT define:
- ❌ Any new execution capability, module, threshold, tier policy, or routing logic (V5.2 remains execution authority)
- ❌ Any UI component specification, screen flow, or workflow design beyond role-level descriptions
- ❌ Any implementation details (APIs, infrastructure, storage engines, identity systems, integration protocols)
- ❌ Any regulatory/compliance commitments, certifications, or claims
- ❌ Any backward merge of V6 analysis constructs into V5.2 execution semantics

---

## Terminology & Boundary Notes

### Locked Taxonomy Labels
- **1OPMD:** Core anchor / EoH governed reasoning system
- **2OPMD:** Patient-facing surface label (B2C platform)
- These are platform taxonomy labels supplied in prompt, NOT defined as canonical module entities in V5.2/V6 M55-M61

### Numbering Ambiguity Flag (Requires Canonical Clarification)
- V5.2 Module 24 references "consent/privacy flags (Module 46)" as input/enforcement control
- However, pinned V5.2 module set also uses M46 as "Mitigations" within CAPA registries chain
- **Document treats enforceable boundary as:** consent gate (M26) + minimization/de-identification engine (M27) + interface-layer RBAC/masking obligations (M24)
- Flags module-number reference as **labeling inconsistency to be resolved canonically**

---

## Status & Iteration Policy

### Non-Executable
This architecture is **descriptive** and does NOT define runtime behavior.

### Non-Binding
This is a **vocabulary and boundary artifact for alignment**, not a commitment to product scope.

### Iteration-Safe
Changes require an explicit new phase and must NOT imply retroactive authority or backward merge into V5.2.

### Authority Preservation
- **V5.2 retains execution authority**
- V6 modules referenced here (M55-M61) are used ONLY as **analysis-level boundary formalizations**

---

## Strategic Implications for 2OPMD Development

### 1. Clear Boundary Definition
This document establishes that 2OPMD (B2C) is:
- ✅ A **reflective surface**, not an execution authority
- ✅ A **patient-facing view** of governed core state
- ✅ An **interaction event collector** (journaling, mood, feedback)
- ❌ NOT a mutation surface for canonical state
- ❌ NOT an autonomous action executor

### 2. Authority Flow Is Unidirectional
```
Patient (2OPMD) → Reflective Input → Core System → Clinical Decision (B2MD) → Execution
```

**NOT:**
```
Patient (2OPMD) → Direct Action ❌
```

### 3. Device Strategy Implications
- **Mobile-first** for B2C/2OPMD (confirmed by matrix)
- Web as secondary surface
- Tablet optional
- This aligns with patient wellness monitoring and journaling use cases

### 4. Integration Points
B2C/2OPMD must integrate with core via:
- **Input:** Governed storage pathways for reflective events (journaling, mood, feedback)
- **Output:** Role-filtered narratives and simplified state representations
- **Constraint:** All operations constrained by consent state
- **Audit:** All interactions logged with provenance

### 5. Development Guardrails
When building 2OPMD features, must ensure:
- ✅ All patient inputs are interaction events, not state mutations
- ✅ All displayed state is read-only from core
- ✅ No actions presented as authoritative without clinician pathway
- ✅ Consent state respected at every step
- ✅ Suppression semantics honored (if applicable to patient surface)

---

## Next Steps for 2OPMD Development

### Immediate (Architecture Alignment)
1. **Review existing 2OPMD codebase** against this architecture
   - Identify any areas where UI might be mutating core state directly
   - Ensure all patient actions are routed as events, not mutations
   - Verify read-only posture for displayed state

2. **Audit consent/suppression handling**
   - Ensure 2OPMD respects consent state from core
   - Verify no bypass mechanisms exist

3. **Map device surfaces** to architecture
   - Confirm mobile-first strategy
   - Identify web surfaces that need role-level access

### Short-Term (Integration Specification)
1. **Define interaction event schema** for 2OPMD → Core
   - Journaling events
   - Mood/tag events
   - Feedback events
   - Concern events

2. **Define role-filtered narrative API** for Core → 2OPMD
   - Simplified trajectory representations
   - Plain language state summaries
   - Patient-appropriate vocabulary

3. **Establish consent gate integration**
   - How 2OPMD queries consent state
   - How operations are constrained by consent

### Medium-Term (Feature Development)
1. **Build reflective HITL features**
   - Journaling interface
   - Mood tracking
   - Feedback submission
   - Concern reporting

2. **Build read-only wellness views**
   - Timeline visualization (simplified)
   - Trajectory bands in plain language
   - Key flags (patient-appropriate)

3. **Ensure audit/provenance**
   - All patient interactions logged
   - Actor attribution preserved
   - Replayability maintained

---

## Critical Warnings for Development Team

### ⚠️ Warning 1: State Mutation Boundary
**Do NOT build features that allow patients to:**
- Mutate core clinical state directly from UI
- Override clinician decisions
- Bypass consent/suppression controls
- Activate execution artifacts

**These are B2MD responsibilities, not B2C/2OPMD.**

### ⚠️ Warning 2: Authority Presentation
**Do NOT present patient actions as:**
- Authoritative (they are reflective inputs)
- Finalized (they are interaction events)
- Executed (they require clinician pathway)

**All patient-facing language must reflect the reflective/informational authority level.**

### ⚠️ Warning 3: Consent Bypass
**Do NOT implement:**
- Any pathway that bypasses consent gate
- Any feature that ignores suppression state
- Any export that doesn't respect minimization

**Core enforces these; 2OPMD must honor them.**

### ⚠️ Warning 4: Autonomous Behavior
**Do NOT build:**
- Autonomous alert generation from 2OPMD
- Autonomous escalation from patient inputs
- Autonomous execution of any kind

**Core generates alerts; clinicians (B2MD) make decisions; 2OPMD is reflective only.**

---

## Architecture Compliance Checklist

Before shipping any 2OPMD feature, verify:

- [ ] Feature respects patient authority level (reflective/informational only)
- [ ] All patient actions are routed as interaction events, not state mutations
- [ ] Displayed state is read-only from core (no local computation of clinical scores)
- [ ] Consent state is checked and honored
- [ ] Suppression semantics are respected (if applicable)
- [ ] No autonomous activation of execution artifacts
- [ ] All interactions logged with audit/provenance
- [ ] Patient-facing language reflects reflective authority level
- [ ] No bypass of core guardrails (consent, suppression, finalization)
- [ ] Device surfaces align with architecture (mobile-first)

---

## Epistemic Lineage & Provenance

### Source Document Fidelity
- ✅ **100% preservation** of architectural boundaries
- ✅ All authority levels captured accurately
- ✅ All HITL categories preserved
- ✅ All interaction flows documented
- ✅ All explicit non-goals listed
- ✅ Terminology and boundary notes included

### Integration Quality
This report provides:
- ✅ Executive summary for quick understanding
- ✅ Detailed breakdown of each platform type
- ✅ Authority and HITL ownership model
- ✅ Interaction flows (conceptual)
- ✅ Device/modality matrix
- ✅ Strategic implications for 2OPMD development
- ✅ Development guardrails and warnings
- ✅ Architecture compliance checklist
- ✅ Next steps roadmap

### Document Placement
- **Source:** `game_plans/AEN_DUMP/AEN_DUMP.md`
- **Target:** `2ndOpinionMD-MVP/EOH_PLATFORM_INTERACTION_ARCHITECTURE_V0.md` (canonical architecture doc)
- **Report:** `2ndOpinionMD-MVP/INGESTION_REPORT_EOH_ARCHITECTURE_20260131.md` (this document)

---

## Bottom Line

**What this document defines:**
- The EoH core (1OPMD) is the governed reasoning system; all platforms depend on it but do not replace it
- 2OPMD (B2C) is a **reflective surface** for patient wellness views and journaling, NOT a clinical decision authority
- B2MD (clinician) is the ONLY platform that can collapse uncertainty into patient-level action
- B2B (governance) provides oversight without patient-level authority
- B2I (research) consumes governed exports without action authority

**What 2OPMD can do:**
- ✅ Collect journaling, mood, feedback, concerns as interaction events
- ✅ Display simplified, read-only views of core state
- ✅ Route reflective inputs to governed storage pathways

**What 2OPMD must NOT do:**
- ❌ Mutate canonical core state from UI
- ❌ Present patient actions as authoritative
- ❌ Bypass consent/suppression controls
- ❌ Activate execution artifacts autonomously

**Authority flow:**
```
Patient (2OPMD) → Reflective Input → Core (1OPMD) → Clinical Decision (B2MD) → Execution
```

**Development principle:**
> "Only B2MD may collapse uncertainty into patient-level action."

This architecture ensures:
- Patient sovereignty (via consent and reflective HITL)
- Clinical authority (via B2MD finalization pathway)
- Governance oversight (via B2B read-only audit)
- Research access (via B2I governed exports)
- No autonomous execution
- Full audit/provenance lineage

**The Beating Heart of Andromeda (2OPMD) is defined as a reflective surface, not an execution engine. This is a critical architectural boundary that protects patient safety and clinical authority.**

---

**Ingestion Status:** ✅ Complete  
**Architecture Document:** `EOH_PLATFORM_INTERACTION_ARCHITECTURE_V0.md`  
**Report:** `INGESTION_REPORT_EOH_ARCHITECTURE_20260131.md`  
**Next Action:** Review architecture against existing 2OPMD codebase for compliance

**chaos < Structure. Architecture defined. Boundaries preserved. Authority clarified. 🫡**
