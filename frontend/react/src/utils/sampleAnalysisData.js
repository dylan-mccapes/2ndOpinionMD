export const sampleAnalysisData = {
  analysis: "The patient reports symptoms of fatigue and headache, which are common but nonspecific and could be indicative of a range of conditions including autoimmune disorders. There is no mention of environmental factors or life stressors in the journal entry, which limits the scope of analysis to the symptoms alone.",
  symptoms: ["tired", "headache"],
  environmental_factors: [],
  life_stressors: [],
  diagnoses: [
    {
      name: "Chronic Fatigue Syndrome",
      confidence: 60,
      status: "new",
      staxLevel: 2,
      zone: 3,
      tags: ["#SuspectedDx_ChronicFatigueSyndrome", "#EarlyZoneShift"]
    },
    {
      name: "Migraine",
      confidence: 50,
      status: "new",
      staxLevel: 2,
      zone: 3,
      tags: ["#SuspectedDx_Migraine", "#EarlyZoneShift"]
    }
  ],
  journalingRecommendation: {
    promptType: "Clinical",
    suggestedPrompt: "Please describe any recent changes in your daily routine or stress levels that might be affecting your health."
  },
  followUpQuestions: [
    "Have there been any recent changes in your diet or environment?",
    "Can you describe the nature of your headaches - are they localized, throbbing, or accompanied by other symptoms like nausea or light sensitivity?"
  ],
  trackingSuggestions: [
    "Consider maintaining a detailed symptom diary to track the frequency, duration, and severity of headaches.",
    "Note any potential triggers or alleviating factors for your symptoms."
  ],
  patternObservations: "The patient consistently reports symptoms of fatigue and headache, suggesting a pattern that may warrant further investigation into chronic conditions.",
  timestamp: "2025-08-17T09:15:10.016948"
};

export const sampleAnalysisDataComplex = {
  analysis: "The patient reports multiple symptoms including joint pain, fatigue, and skin rash, occurring in the context of recent workplace stress and potential mold exposure. The combination of symptoms and environmental factors suggests possible autoimmune involvement.",
  symptoms: ["joint_pain", "fatigue", "skin_rash", "morning_stiffness"],
  environmental_factors: ["mold_exposure", "workplace_chemicals", "poor_air_quality"],
  life_stressors: ["work_deadline_pressure", "family_illness", "financial_concerns"],
  diagnoses: [
    {
      name: "Lupus (SLE)",
      confidence: 75,
      status: "suspected",
      staxLevel: 3,
      zone: 4,
      tags: ["#AutoimmuneDx_Lupus", "#EnvironmentalTriggers", "#HighPriority"]
    },
    {
      name: "Rheumatoid Arthritis",
      confidence: 65,
      status: "possible",
      staxLevel: 2,
      zone: 3,
      tags: ["#AutoimmuneDx_RA", "#JointInvolvement"]
    }
  ],
  journalingRecommendation: {
    promptType: "Environmental",
    suggestedPrompt: "Please document your daily environment, including workplace conditions, home environment, and any potential exposures that might be contributing to your symptoms."
  },
  followUpQuestions: [
    "How long have you been exposed to the workplace chemicals?",
    "Have you noticed if your symptoms improve when you're away from work?",
    "Are there any family members with similar autoimmune conditions?"
  ],
  trackingSuggestions: [
    "Track symptom severity in relation to environmental exposures",
    "Monitor stress levels and their correlation with symptom flares",
    "Document sleep quality and its impact on morning stiffness"
  ],
  patternObservations: "Clear correlation between environmental stressors and symptom onset, with morning stiffness pattern suggesting inflammatory arthritis. Stress appears to be a significant trigger for symptom exacerbation.",
  timestamp: "2025-08-17T16:23:00.000000"
};
