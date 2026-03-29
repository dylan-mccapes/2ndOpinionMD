# **EoH V6 — Canonical Module Index (Coverage Scan)**

*(Experimental, non-canonical; does not alter V5.2)*

---

### **V6 M51 — EoH Sentinel**

* **Keywords:** offline watchdog, tool detection, ToolCandidate, ToolRegistry, lifecycle states, extraction, audit events

* **OWNS:** Detection and structured extraction of diagnostic/prognostic tool-like artifacts from MKE ingestion into standardized ToolCandidate objects with lifecycle tracking.

* **DOES NOT OWN:** Tool execution, query-time selection, fusion, clinical truth claims, or integration into EoH reasoning modules.

---

### **V6 M52 — EoH Tool Builder**

* **Keywords:** offline compiler, ToolCandidate intake, ToolDefinition, ToolImplementation, deduplication, harmonization, Tool Library

* **OWNS:** Compilation of ToolCandidates into versioned EoH-native tools (definitions, implementations, library entries) with deduplication, harmonization, routing metadata, and auditability.

* **DOES NOT OWN:** Tool detection, query-time selection/fusion, runtime execution on patient data, or guideline interpretation beyond explicit tool conversion.

---

### **V6 M53 — Probabilistic Terrain Model (PTM)**

* **Keywords:** probability landscape, uncertainty, temporal deltas, codominance, recommendation tiers, signals-only

* **OWNS:** Maintenance of a time-evolving probabilistic terrain over multiple plausible conditions using signals, emitting probability landscapes and uncertainty-preserving summaries when invoked.

* **DOES NOT OWN:** Diagnosis, treatment mandates, direct tool execution, cadence selection, publish gating, or orchestration (owned by M54).

---

### **V6 M54 — Terrain Conductor & Update Scheduler (TCS)**

* **Keywords:** orchestration, confidence gating, cadence policies, UpdatePlan, rate-limit, publish control

* **OWNS:** Scheduling and gating of PTM recomputation and long-horizon narrative deep-passes via UpdatePlan based on evidence sufficiency and stability.

* **DOES NOT OWN:** Probability computation, narrative generation, tool detection/compilation, or any treatment decision logic.

