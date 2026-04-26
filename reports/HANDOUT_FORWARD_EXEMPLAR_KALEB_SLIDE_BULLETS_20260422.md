# HANDOUT — Slide-Ready Bullets, FORWARD Exemplar for Kaleb's RA-Conference / Congressional Talk

**For Kaleb to copy straight into slides.** Every bullet is under 20 words and self-cites.

---

## SLIDE 1 — What the graph is (one bullet each)

- Five-year longitudinal patient graph, ten semi-annual PRO rounds, FORWARD-shaped, HIPAA-safe on-premise.
- Instruments: HAQ-II, VAS Pain, VAS Patient Global, PAS-II, RDCI.
- Every event carries its own provenance, salience score, and canonical ID.
- Uncertainty Carriers (UCs) are first-class graph nodes, not afterthoughts.
- Reference: SSRN 6554940 — *Uncertainty-Carrier Governance for Clinical Decision Support*.

---

## SLIDE 2 — Patient 4: UC anticipates the flare two rounds early

- Rounds 0–2: stable trajectory, narrow UC bands, confidence `high`.
- **Round 3: UC = 0.22 (band 0.20–0.24). HAQ-II drift = 0.50 MCID units — subclinical.**
- **Round 4: UC = 0.37 (band 0.34–0.40). HAQ-II drift = 0.91 MCID units — still subclinical.**
- Round 5: overt PRO-composite flare. UC = 0.87. Therapy escalated.
- The system flagged the signal twelve months before the clinician had to act.

---

## SLIDE 3 — Why that matters (governance)

- UC cites its basis: every estimate lists the PRO events that produced it.
- UC states its confidence: `low` at baseline, `high` once the trajectory is informative.
- UC is deterministic: it is not a language-model opinion.
- The graph carries the anticipation as a typed edge: `kind = "pre_flare_anticipation"`.
- The flare arc authors its own follow-up question: *"Would earlier escalation at rounds 3–4 have prevented this?"*

---

## SLIDE 4 — Patient 5: the system says what it does not know

- Patient misses questionnaires at rounds 4 and 6.
- Graph records the gaps as `administrative` events — no interpolation, no pretending.
- Round 7 UC = 0.67 with a wide band (0.54–0.81).
- Basis line (verbatim): *"UC width widened due to missing recent questionnaire(s)."*
- Round 9 UC = 0.65 with a narrow band (0.56–0.75) — data returned; confidence did too.

---

## SLIDE 5 — What we are building with FORWARD

- **Pilot:** 5 patients × 5 years × PROs. Nothing else. Anonymized. Friday-email send.
- **Deliverable:** 5 production PTV graphs within 48 hours of data receipt.
- **Instruments of record:** HAQ-II, VAS Pain, VAS Global, PAS-II, RDCI. DAS28 not required.
- **Out of scope:** labs, imaging, biosamples, -omics — FORWARD does not collect; we do not ask.
- **Paper 2 intent:** PRO-based flare-risk stratifier with UCs. Michaud senior author.

---

## SLIDE 6 — One-sentence takeaways (pick any)

- *"Our system does not predict; it carries uncertainty."*
- *"A CDS output without an uncertainty carrier is a patient-safety hazard."*
- *"The graph flagged the flare twelve months early — and said out loud how confident it was."*
- *"When the questionnaire is missing, the band widens and the basis line says so."*
- *"Everything the model claims is cited to an event in the patient's own graph."*

---

## SPEAKER NOTES — anticipated audience questions

| question | one-line answer |
|---|---|
| Is this real FORWARD data? | No — synthetic, deterministically generated, clearly labeled. The shape is identical to what the pilot will deliver. |
| Is the UC from the LLM? | No. It is a deterministic MCID-normalized composite with explicit basis. The LLM reviews; it does not emit the carrier. |
| Why 90 % bands specifically? | Convention aligned with the UC paper (SSRN 6554940); the framework supports any α. |
| How does this scale? | The pilot is five. The system is built for hundreds of thousands — same schema, same pipeline, same guarantees. |
| What if the clinician ignores the early signal? | The graph still records it; the open-question arc carries the counterfactual forward. |
| HIPAA? | PortalNode-01: air-gapped inference, 4×4090, no egress. De-identified ingest only for the pilot. |
| IP? | SSRN 6554940 lays the flag; the graph schema and UC detector are proprietary IP of 2ndOpinionMD. |
| Is this just regression? | No. The carrier is graph-native and composes across arcs; the surrounding graph supplies the counterfactuals. |

---

## APPENDIX — Screenshot-ready JSON snippets

### Snippet A — the UC node at anticipation round 3 (P4)

```json
{
  "event_type": "derived_metric",
    "timestamp": "2022-08-01",
  "annotations": {
    "kind": "uncertainty_carrier",
    "metric": "flare_probability_90",
    "point_estimate": 0.22,
    "band_90": [0.20, 0.24],
    "confidence": "high",
    "anticipation": true,
    "basis": [
      "HAQ-II delta since baseline = 0.50 MCID units",
      "VAS pain delta since baseline = 0.47 MCID units",
      "rounds with missing data in last 3 rounds: 0"
    ],
    "governance_ref": "SSRN 6554940 (Uncertainty Carriers)",
    "evidence_event_ids": ["P4_r03_haq2", "P4_r03_vas_pain", "P4_r03_vas_global", "P4_r03_pas2"]
  }
}
```

### Snippet B — the flare arc citing the anticipation round (P4)

```json
{
  "arc_id": "arc_flare_r05",
  "name": "Flare window (round 6)",
  "status": "enriched",
  "summary": "PRO-composite flare detected at round 6. HAQ-II and VAS-pain crossed MCID thresholds against patient baseline; treatment escalation recorded within the same epoch.",
  "open_questions": [
    "Earlier UC-anticipated rounds 3-4 suggest a pre-flare signal; would earlier escalation have prevented this event?"
  ],
  "cross_arc_edges": [
    {"peer_arc_id": "arc_therapy_adalimumab", "kind": "treated_by", "strength": 1.0},
    {"peer_arc_id": "arc_study_epoch_m24", "kind": "pre_flare_anticipation", "strength": 0.8, "evidence_event_id": "P4_uc_r03"},
    {"peer_arc_id": "arc_study_epoch_m30", "kind": "pre_flare_anticipation", "strength": 0.8, "evidence_event_id": "P4_uc_r04"}
  ]
}
```

### Snippet C — the honest-uncertainty UC at round 7 (P5)

```json
{
  "event_type": "derived_metric",
  "annotations": {
    "kind": "uncertainty_carrier",
    "point_estimate": 0.67,
    "band_90": [0.54, 0.81],
    "confidence": "moderate",
    "basis": [
      "HAQ-II delta since baseline = 2.09 MCID units",
      "VAS pain delta since baseline = 1.45 MCID units",
      "rounds with missing data in last 3 rounds: 1",
      "UC width widened due to missing recent questionnaire(s)"
    ],
    "governance_ref": "SSRN 6554940 (Uncertainty Carriers)"
  }
}
```

---

*Companion narrative report: `reports/REPORT_FORWARD_EXEMPLAR_5PT_FOR_KALEB_20260422.md`.
Artifacts: `artifacts/forward_exemplar_5pt/`.
Regenerate: `python server/scripts/gen_forward_exemplar.py`.*
