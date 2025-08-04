
export const ZONES = {
  ZONE_1: { id: 1, name: "Zone 1", description: "Stable Terrain" },
  ZONE_2: { id: 2, name: "Zone 2", description: "Mild Fluctuation" },
  ZONE_3: { id: 3, name: "Zone 3", description: "Moderate Instability" },
  ZONE_4: { id: 4, name: "Zone 4", description: "Flare-Dominant State" },
  ZONE_5: { id: 5, name: "Zone 5", description: "Collapsed Capacity" }
};

export const STAX_LEVELS = {
  STAX_1: { id: 1, name: "STAX 1", description: "Single-diagnosis threshold", score: 2.5 },
  STAX_2: { id: 2, name: "STAX 2", description: "Multi-diagnosis state", score: 4.5 },
  STAX_3: { id: 3, name: "STAX 3", description: "Multisystem failure", score: 6.5 },
  STAX_4: { id: 4, name: "STAX 4", description: "Complex collapse", score: 9.0 }
};

export const CLINICAL_TAGS = {
  CONFIRMED_DX: { prefix: "#ConfirmedDx_", weight: 3.0, zoneImpact: 1.0, staxImpact: 1.0 },
  SUSPECTED_DX: { prefix: "#SuspectedDx_", weight: 2.0, zoneImpact: 0.75, staxImpact: 0.5 },
  STAX_TRIGGER: { prefix: "#STAXTrigger", weight: 2.5, zoneImpact: 1.0, staxImpact: 1.0 },
  EARLY_ZONE_SHIFT: { prefix: "#EarlyZoneShift", weight: 0.5, zoneImpact: 0.25, staxImpact: 0.0 }
};

export const SYMBOLIC_TAGS = {
  SHTR: { prefix: "#SHTR", description: "Somatic Healing Threshold Response", weight: 1.5 },
  OVERSHOOT: { prefix: "#OvershootReaction", description: "Protocol Exceeded", weight: 1.0 },
  RESILIENCE: { prefix: "#Resilience", description: "Terrain Bounceback", weight: -1.5 },
  ANCESTRAL: { prefix: "#SymbolicAncestralImprint", description: "Inherited Terrain", weight: 0.5 }
};

export const MISDIAGNOSIS_PATTERNS = {
  FIBROMYALGIA: { name: "Fibromyalgia", masking: ["MCAS", "Lyme", "Mold", "PTSD"] },
  IBS_GERD: { name: "IBS/GERD", masking: ["SIBO", "vagal dysfunction", "trauma response"] },
  ANXIETY: { name: "Anxiety Disorders", masking: ["POTS", "MCAS", "neuroinflammation"] },
  DEPRESSION: { name: "Depression", masking: ["fatigue syndromes", "trauma stagnation"] },
  ADHD: { name: "ADHD", masking: ["histamine response", "post-viral brain inflammation"] }
};

export const JOURNAL_PROMPT_TYPES = {
  CLINICAL: { name: "Clinical", default: true },
  SOMATIC: { name: "Somatic", triggers: ["SHTR", "Resilience"] },
  SYMBOLIC: { name: "Symbolic", triggers: ["Identity", "Trauma", "Grief"] },
  REMISSION: { name: "Remission Drift", triggers: ["Healing Identity"] }
};

export const getJournalPromptType = (tags) => {
  if (tags.includes("#SHTR") || tags.includes("#Resilience")) {
    return JOURNAL_PROMPT_TYPES.SOMATIC;
  }
  if (tags.includes("#SymbolicAncestralImprint") || tags.includes("#NarrativeOveridentification")) {
    return JOURNAL_PROMPT_TYPES.SYMBOLIC;
  }
  return JOURNAL_PROMPT_TYPES.CLINICAL;
};

export const generateEthosPrompt = () => {
  return `Using the 2OPMD Diagnostic Terrain System:
- Consider Nucleus State of Health and Parallel-Adjusted Nucleus State (PANS)
- Assess STAX levels (Z-Axis progression) for disease complexity
- Evaluate patient stability using Zones 1-5
- Identify Early Zone Shifts, Epigenetic Echoes, and Overshoot patterns
- Detect Somatic Healing Threshold Responses and potential Safe Pause needs
- Consider misdiagnosis patterns and tags`;
};
