import { normalizeStringList } from './normalizeList';

export function parseJournalAnalysis(raw) {
  if (!raw) return null;

  let data = raw;
  if (typeof raw === "string") {
    try { 
      data = JSON.parse(raw); 
    } catch {
      return {
        analysis: raw,
        symptoms: [],
        environmental_factors: [],
        life_stressors: [],
        diagnoses: [],
        journalingRecommendation: { promptType: null, suggestedPrompt: null },
        followUpQuestions: [],
        trackingSuggestions: [],
        patternObservations: "",
        timestamp: null
      };
    }
  }
  if (!data || typeof data !== "object") return null;

  return normalize(data);
}

function normalize(data) {
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

  const normSymptoms = Array.isArray(symptoms)
    ? symptoms.map(s => {
        if (typeof s === "string") return s;
        if (s && typeof s === "object") return s.name ?? s.symptom ?? "";
        return "";
      }).filter(Boolean)
    : [];

  const normDiagnoses = Array.isArray(diagnoses)
    ? diagnoses.map(d => ({
        name: d?.name ?? "",
        confidence:
          typeof d?.confidence === "number"
            ? d.confidence
            : (Number(d?.confidence) || null),
        status: d?.status ?? null,
        staxLevel: d?.staxLevel ?? null,
        zone: d?.zone ?? null,
        tags: normalizeStringList(d?.tags)
      }))
    : [];

  return {
    analysis,
    symptoms: normSymptoms,
    environmental_factors: normalizeStringList(environmental_factors),
    life_stressors: normalizeStringList(life_stressors),
    diagnoses: normDiagnoses,
    journalingRecommendation: {
      promptType: journalingRecommendation?.promptType ?? null,
      suggestedPrompt: journalingRecommendation?.suggestedPrompt ?? null
    },
    followUpQuestions: normalizeStringList(followUpQuestions),
    trackingSuggestions: normalizeStringList(trackingSuggestions),
    patternObservations: patternObservations || "",
    timestamp
  };
}
