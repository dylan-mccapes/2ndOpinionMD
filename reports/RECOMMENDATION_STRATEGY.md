# RECOMMENDATION_STRATEGY

**Date:** 2026-02-27  
**Scope:** Audience-safe recommendation policy for EoH / EoHD outputs  
**Context anchor:** Norman Roberts case review (inconsistency detection by family/owner-side reader)

---

## 1) Why This Exists

In real use, people close to the patient (e.g., family, operators, trusted friends) will catch inconsistencies before the system does.  
That is not failure; it is part of safe operation.

This strategy ensures:
- clinicians get actionable recommendations,
- patients get clarity and informed questions,
- the system stays honest about uncertainty and role boundaries.

---

## 2) Audience Policy

### A) Clinician / Care-Team Output

Use a section titled:

**`Recommendations (For Clinical Team Review)`**

Each recommendation should include:
1. **Priority** (High/Med/Low)
2. **Action**
3. **Rationale** (evidence-linked)
4. **Dependencies** (what data must be obtained first)
5. **Safety caveats**
6. **Confidence** (High/Moderate/Low)

Tone: decisive but bounded.  
Rule: decision-support, never definitive treatment directive.

---

### B) Patient / Family Output

Do **not** present direct treatment recommendations as instructions.

Use sections:

1. **What We Know**
2. **What We Do Not Yet Know**
3. **Questions to Ask Your Doctor**
4. **What Different Answers Might Mean** (brief, non-prescriptive)

Tone: clear, calm, non-alarmist.  
Rule: empower understanding and preparation, not self-management directives.

---

## 3) Inconsistency Handling Protocol (Required)

When phase outputs diverge (example: full-timeline synthesis vs sparse-2004 narrative):

1. Emit a **Data Availability Context** note near the start of the packet.
2. Explicitly label which phases are:
   - broad timeline synthesis
   - sparse-input stress tests
3. Add a short **Consistency Check** table:
   - conflicting claim
   - likely cause
   - confidence impact
   - next validation step

If inconsistency is unresolved, recommendations must be downgraded in confidence.

---

## 4) Clinical Safety Guardrails

Never:
- claim diagnostic certainty without supporting evidence,
- provide medication changes as patient-facing instruction,
- hide uncertainty when data are sparse or conflicting.

Always:
- separate **evidence** from **inference**,
- mark uncertainty explicitly,
- indicate who should act (patient vs clinician vs data team).

---

## 5) Suggested Output Blocks (Implementation-Ready)

### For clinicians

- `Recommendations (For Clinical Team Review)`
- `Uncertainty / Data Gaps`
- `Validation Plan (next 1-3 steps)`

### For patients/family

- `Situation Summary`
- `Questions to Ask Your Doctor`
- `If the doctor says X, ask Y` (bounded clarifier prompts)

---

## 6) Policy Position

“Bending rules” is acceptable only when it increases care utility **without crossing role safety**.

Interpretation:
- Yes to clinician-facing recommendations.
- Yes to patient-facing question guidance.
- No to patient-facing prescriptive treatment advice.

This is kindness with boundaries.

---

## 7) Operational Note

Trusted human review (like Nate catching timeline inconsistency) is a core safety feature, not an exception path.  
The system should treat these observations as high-value signals and fold them into receipts, reflections, and subsequent runs.

