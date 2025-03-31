import { POSSIBLE_DIAGNOSES } from './constants';

export const formatSymptomData = (formData) => {
  const symptoms = formData.symptoms ? formData.symptoms.map(symptom => symptom.value) : [];
  
  const priorDiagnoses = formData.priorDiagnoses && formData.priorDiagnoses.length > 0 
    ? formData.priorDiagnoses.map(diagnosis => diagnosis.value) 
    : [];

  return {
    user_id: "anonymous_1234",
    input_type: "symptom_query",
    input_data: {
      age: parseInt(formData.age),
      sex: formData.sex.value,
      symptoms,
      duration_months: parseInt(formData.durationMonths || 0),
      prior_diagnoses: priorDiagnoses
    },
    context_flags: {
      hipaa_mode: true,
      model_version: process.env.REACT_APP_MODEL_VERSION || "gpt-4-turbo",
      return_format: "json"
    }
  };
};

export const simulateAIResponse = (formData) => {
  let symptoms = [];
  
  if (!formData) {
    return [];
  }
  
  if (formData.input_data && formData.input_data.symptoms) {
    symptoms = formData.input_data.symptoms;
  } 
  else if (formData.symptoms) {
    symptoms = Array.isArray(formData.symptoms) ? 
      formData.symptoms.map(s => typeof s === 'object' && s.value ? s.value : s) : [];
  }
  
  if (!symptoms || symptoms.length === 0) {
    return [{
      name: 'Long COVID (PASC)',
      confidence: 45,
      symptoms: ['fatigue', 'brain_fog', 'rapid_heart_rate', 'shortness_of_breath', 'post_exertional_malaise'],
      redFlags: ['Symptoms began after COVID infection', 'Post-exertional malaise'],
      labSuggestions: ['D-dimer', 'Complete blood count', 'Comprehensive metabolic panel', 'Chest X-ray']
    }];
  }
  
  const filteredDiagnoses = POSSIBLE_DIAGNOSES
    .map(diagnosis => {
      const matchingSymptoms = diagnosis.symptoms.filter(s => symptoms.includes(s));
      const matchScore = Math.max(0.4, matchingSymptoms.length / diagnosis.symptoms.length);
      
      const adjustedConfidence = Math.round(diagnosis.confidence * matchScore);
      
      return {
        ...diagnosis,
        confidence: Math.min(adjustedConfidence, diagnosis.confidence)
      };
    })
    .filter(diagnosis => diagnosis.confidence > 20) // Lower threshold to include more diagnoses
    .sort((a, b) => b.confidence - a.confidence) // Sort by confidence
    .slice(0, 5); // Limit to top 5
  
  if (filteredDiagnoses.length === 0) {
    return [{
      name: 'Long COVID (PASC)',
      confidence: 45,
      symptoms: ['fatigue', 'brain_fog', 'rapid_heart_rate', 'shortness_of_breath', 'post_exertional_malaise'],
      redFlags: ['Symptoms began after COVID infection', 'Post-exertional malaise'],
      labSuggestions: ['D-dimer', 'Complete blood count', 'Comprehensive metabolic panel', 'Chest X-ray']
    }];
  }
  
  return filteredDiagnoses;
};
