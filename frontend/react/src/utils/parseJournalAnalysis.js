export function parseJournalAnalysis(raw) {
  if (!raw) return null;

  let data = raw;
  if (typeof raw === "string") {
    try { 
      data = JSON.parse(raw); 
    } catch { 
      return null;
    }
  }
  if (!data || typeof data !== "object") return null;

  const {
    analysis = "",
    symptoms = [],
    environmental_factors = [],
    life_stressors = [],
    diagnoses = [],
    journalingRecommendation = {},
    followUpQuestions = [],
    trackingSuggestions = [],
    patternObservations = "",
    timestamp = null
  } = data;

  const normDiagnoses = Array.isArray(diagnoses) ? diagnoses.map(d => ({
    name: d?.name ?? "",
    confidence: typeof d?.confidence === "number" ? d.confidence : (Number(d?.confidence) || null),
    status: d?.status ?? null,
    staxLevel: d?.staxLevel ?? null,
    zone: d?.zone ?? null,
    tags: Array.isArray(d?.tags) ? d.tags : []
  })) : [];

  return {
    analysis,
    symptoms: Array.isArray(symptoms) ? symptoms : [],
    environmental_factors: Array.isArray(environmental_factors) ? environmental_factors : [],
    life_stressors: Array.isArray(life_stressors) ? life_stressors : [],
    diagnoses: normDiagnoses,
    journalingRecommendation: {
      promptType: journalingRecommendation?.promptType ?? null,
      suggestedPrompt: journalingRecommendation?.suggestedPrompt ?? null
    },
    followUpQuestions: Array.isArray(followUpQuestions) ? followUpQuestions : [],
    trackingSuggestions: Array.isArray(trackingSuggestions) ? trackingSuggestions : [],
    patternObservations: patternObservations || "",
    timestamp
  };
}
