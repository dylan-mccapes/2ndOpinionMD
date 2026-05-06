EoH Platform Interaction Architecture v0

Document Type: Canonical Analysis Artifact (Non-Executable, Iterative Baseline)
Scope: Defines how platform surfaces (B2C, B2MD, B2B, B2I) interact with the EoH governed reasoning system, including authority boundaries, HITL ownership, and device modalities.
Non-goal: This document does not define implementation, UI workflows, or new system capabilities.

⸻

1. Core System Anchor (EoH / 1OPMD)

What the core system is

The EoH core is the governed reasoning stack that:
	•	Maintains a patient-specific longitudinal truth via a tamper-evident, queryable ledger/vault for trajectories, alerts, outcomes, and provenance.  
	•	Produces pattern-based early warning and trend signals and hands them to downstream surfaces with clinicians remaining decision makers.  
	•	Enforces consent and ethical gating such that no downstream module may act outside current consent state or ethical override regime.  
	•	Enforces suppression-aware behavior and ensures suppressed states are surfaced with explanations and audit hooks (rather than being silently dropped).  
	•	Ensures execution is draft-only until clinician finalization, preventing autonomous activation of actions.

What the core system explicitly is not

The EoH core is not:
	•	A UI surface (it is not the patient app, clinician portal, governance dashboard, or research workspace). The interface layer is explicitly a hub that displays state and routes actions; it “never computes clinical scores itself.”  
	•	A medical-knowledge/guideline engine. Several modules explicitly prohibit embedding disease/guideline facts and treat those as external/neighbor responsibilities.
	•	An autonomous executor. Execution artifacts remain proposals/drafts and “no resource becomes active without explicit clinician action via Module 19.”  
	•	A platform governance or roadmap authority. V6 analysis artifacts explicitly do not back-propagate execution authority into V5.2 (“no backward merge”).  

Why all platforms depend on it but do not replace it

All platforms depend on the core because it is the system-of-record for patient timeline state, consent gating, suppression semantics, and audit/provenance lineage. The platforms are surfaces and roles that:
	•	Request role-scoped views (patient/clinician/auditor) of core state and narratives.
	•	Submit user interaction events (journals, feedback, approvals/overrides) back into the governed ledger and learning/QA pathways.
	•	Never bypass the core’s guardrails for consent, suppression, auditability, or clinician finalization.

Terminology boundary note (locked taxonomy labels)

This document uses “1OPMD” and “2OPMD” only as locked platform taxonomy labels supplied in the prompt (core anchor vs patient-facing surface label). These terms are not defined as canonical module entities in the pinned V5.2 / V6 M55–M61 texts; therefore, this document does not assign them independent execution semantics.

Numbering ambiguity flag (requires canonical clarification)

V5.2 Module 24 references “consent/privacy flags (Module 46)” as an input and enforcement control.
However, the pinned V5.2 module set also uses M46 as “Mitigations” within the CAPA registries chain.  
This document treats the enforceable boundary as: consent gate (M26) + minimization/de-identification engine (M27) + interface-layer RBAC/masking obligations (M24), and flags the module-number reference as a labeling inconsistency to be resolved canonically.

⸻

2. Platform Taxonomy

B2C / 2OPMD (Patient-facing)
	•	Audience: Patient (and, where applicable, patient-authorized proxy roles as governed by consent state).  
	•	Authority level: Reflective / informational; no clinical-decision authority.
	•	Primary purpose:
	•	Present a simplified wellness view of longitudinal state using role-appropriate vocabulary, plus journaling and reflective prompts.
	•	What it can see:
	•	Role-filtered narratives and simplified representations of state (e.g., band/stack trajectories in plain language).
	•	What it can do:
	•	Submit journaling, mood/tags, feedback, and concerns as interaction events into governed storage/telemetry paths.
	•	What it must not do:
	•	Must not mutate canonical core state from the UI surface.
	•	Must not present actions as authoritative or “activated” absent clinician finalization pathways.
	•	Typical device surfaces: Mobile-first; web as secondary (role-level only; no UI prescription).

⸻

B2MD (Clinician reasoning & judgment)
	•	Audience: Clinicians / care teams.
	•	Authority level: Patient-scoped clinical judgment and sign-off authority (within governance and execution guardrails).
	•	Primary purpose:
	•	Provide clinician-facing visibility into alerts, forecasts, context, and key flags; enable confirm/override workflows and shared decision tasks.
	•	What it can see:
	•	Clinician-facing action center view of alerts, trajectory cones, psychosomatic context, and key flags (including suppression context).
	•	What it can do:
	•	Confirm/override/annotate outputs via HITL workflows, with audit/provenance logging.
	•	Finalize draft execution artifacts through the clinician-decision locus (Module 19), which is the only place resources become active.  
	•	Apply suppression controls (pauseFlag/pauseReason) as governed, with lifecycle audit.
	•	What it must not do:
	•	Must not treat system outputs as guideline facts or encode disease knowledge locally; clinical meaning remains clinician-responsibility with governance-bound guardrails.  
	•	Must not activate AI-generated actions autonomously or bypass consent/suppression controls.
	•	Typical device surfaces: Web and tablet; may be embedded in clinical contexts where identity and patient context are inherited (no implementation detail beyond role-level embedding).  

⸻

B2B (Organizational / governance)
	•	Audience: Organizational governance operators (quality, safety, oversight roles), operating at system/governance scope rather than patient-action scope.
	•	Authority level: Governance HITL (oversight, review, sign-off) without patient-level action authority.
	•	Primary purpose:
	•	Audit and oversight over system outputs and human decisions; review QA/learning telemetry; ensure ledger-anchored traceability and replayability of disclosures/exports and related denials.
	•	What it can see:
	•	Read-only audit/QA views: chronological event logs derived from vault + audit/provenance artifacts, including clinician outcomes used for learning/QA.
	•	Disclosure/export governance records including allowed/denied outcomes and version tags.
	•	What it can do:
	•	Perform governance review/sign-off for learning-related actions where required (e.g., dual sign-off requirements in QA governance flows).  
	•	Operate in a read-only posture for inspection where appropriate (see QUERY_ONLY concept).  
	•	What it must not do:
	•	Must not perform patient-state mutation, bypass consent/suppression, autonomously publish, autonomously escalate, or autonomously execute.
	•	Typical device surfaces: Web (governance and audit review); analytics/report review environments (role-level only).

⸻

B2I (Institutional / research)
	•	Audience: Institutional research and federated collaboration consumers of governed exports.
	•	Authority level: Secondary-use consumer (no patient-level action authority).
	•	Primary purpose:
	•	Consume purpose-bound, minimized, and de-identified/pseudonymized secondary-use datasets and collaboration exports, with denial semantics and replayability.
	•	What it can see:
	•	Exported, governed artifacts/datasets shaped by minimization and consent state/version; disclosure records are ledger-anchored and version-tagged.
	•	What it can do:
	•	Perform institutional analysis on received exports (outside EoH execution semantics).
	•	What it must not do:
	•	Must not request or obtain patient-state mutation rights through this surface; must not bypass consent/suppression controls; must not trigger escalation or execution.
	•	Typical device surfaces: Institutional analytics environments; batch export consumption surfaces (role-level only).

⸻

3. Authority & HITL Ownership Model

This section defines three HITL categories and assigns platform ownership. These definitions are vocabulary for interaction architecture; they do not add execution semantics.

Reflective HITL

Definition: Human interactions that supply context, preferences, reflections, and feedback, without collapsing uncertainty into clinical action (e.g., journaling, mood tags, concerns).
Owning platform: B2C / 2OPMD
Core invariant: Reflective HITL outputs are inputs to governed reasoning and narrative framing, not authorizations.

Patient-Scoped HITL

Definition: Human-in-the-loop actions at a patient context that can resolve a decision task, apply overrides, or finalize draft execution artifacts. This includes:
	•	Confirm/override/annotate workflows and shared decision tasks routed through Module 19.
	•	Finalization of draft/proposal artifacts (no autonomous activation).
	•	Clinician suppression controls with audit lifecycle.  
Owning platform: B2MD

Governance HITL

Definition: Oversight and review of system behavior, audit/replay, disclosure/export accounting, and learning/QA governance sign-offs—without patient-level action authority. This includes governance guarantees that replay and audit framing remain read-only and cannot influence live execution.
Owning platform: B2B (with B2I as a governed export consumer rather than an authority owner).

Required invariant

Invariant: “Only B2MD may collapse uncertainty into patient-level action.”
This follows the combined boundaries that:
	•	Clinicians remain decision makers for alerting outputs.  
	•	Execution artifacts remain draft/proposal until explicit clinician action via Module 19 (no autonomous activation).
	•	Shared decision orchestration explicitly enforces that “no recommended action becomes authoritative without clinician confirmation via Module 19 and downstream execution guardrails in Module 16.”  

⸻

4. Interaction Flows (Conceptual)

Flow A: Patient reflection → governed ingestion → longitudinal truth

Patient-facing surfaces collect reflective inputs (journal entries, mood/tags, feedback, concerns). These are emitted as interaction events routed into governed storage and telemetry pathways (Vault / QA / learning), preserving provenance and actor attribution.
Consent state constrains what operations are permitted at every step; no downstream module may act outside consent/ethical override regime.  

Flow B: Core reasoning outputs → role-specific presentation without state mutation

Core modules produce structured outputs (alerts, trend flags, trajectories, suppression context). The interface hub renders read-only core state and assembles a unified timeline from the longitudinal vault, applying RBAC/masking and vocabulary guardrails. The UI is explicitly non-mutative: displayed state “cannot be mutated from the UI; all actions are routed to upstream modules.”
Narrative outputs for patient, clinician, and governance audiences are synthesized from structured signals and remain non-originating with respect to metrics/decisions.

Flow C: Clinician review and shared decision → draft execution → clinician finalization

When decision tasks arise, the interface hub orchestrates bidirectional tasks across patient and clinician surfaces via Module 19, capturing patient concerns and clinician decisions with audit/provenance linkage.  
Execution-layer outputs are proposals/drafts and are routed for clinician finalization; the system guarantees no autonomous activation.
Safety-critical escalations are routed in a suppression-aware and auditable manner, with escalation delivery explicitly non-interpretive.  

Flow D: Governance audit/replay and QA → learning governance boundaries

Governance surfaces consume read-only audit/QA views (chronological event log from vault and audit/provenance artifacts) for oversight and learning signal review.
Where governance needs read-only inspection, V6 M55 names an already-possible safe posture (“QUERY_ONLY”) achievable in V5.2 by non-invocation of modules that compute, escalate, execute, schedule, or mutate state.  
V6 M60 (HARF) further constrains governance framing: replay is derived and read-only, audit framing cannot influence live execution, and no patient-state mutation or bypass of consent/suppression is permitted.

Flow E: Research/institutional export requests → minimization + ledger accounting → governed delivery

Institutional/research requests are mediated by:
	•	Consent gate semantics (consent state/version, overlays, and ethical override logging).
	•	Purpose-bound minimization and de-identification engine with denial semantics and replayability.  
	•	Ledger-anchored export governance where every request produces a record (including denials) and outputs remain version-tagged and replay-safe.  
B2I consumes the resulting governed exports; it does not gain patient-action authority through the export pathway.

⸻

5. Device & Modality Matrix

This matrix is a high-level mapping of platform roles to device contexts. It is not UI design.

Platform	Mobile	Web	Tablet	Embedded clinical context	Batch/export / analytics context
B2C / 2OPMD	Primary	Secondary	Optional	Not typical	Not applicable
B2MD	Optional	Primary	Common	Common (clinical context embedding)	Optional
B2B	Rare	Primary	Optional	Not typical	Common (audit/QA review)
B2I	Rare	Optional	Rare	Not typical	Primary (governed exports consumption)

Role-based embedding for clinicians is explicitly supported conceptually (clinical identity and patient context are inherited; clinician actions map to interoperable artifacts), without defining implementation details.  

⸻

6. Explicit Non-Goals

This document intentionally does not define:
	•	Any new execution capability, module, threshold, tier policy, or routing logic (V5.2 remains the execution authority).  
	•	Any UI component specification, screen flow, or workflow design beyond role-level descriptions.
	•	Any implementation details (APIs, infrastructure, storage engines, identity systems, or integration protocols).
	•	Any regulatory/compliance commitments, certifications, or claims (only governed consent/minimization/audit semantics already present in canonical modules are referenced).
	•	Any backward merge of V6 analysis constructs into V5.2 execution semantics.

⸻

7. Status & Iteration Policy
	•	Non-executable: This architecture is descriptive and does not define runtime behavior.
	•	Non-binding: It is a vocabulary and boundary artifact for alignment, not a commitment to product scope.
	•	Iteration-safe: Changes require an explicit new phase and must not imply retroactive authority or backward merge into V5.2.
	•	Authority preservation: V5.2 retains execution authority; V6 modules referenced here (M55–M61) are used only as analysis-only boundary formalizations.