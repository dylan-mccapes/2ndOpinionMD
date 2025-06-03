import { POSSIBLE_DIAGNOSES } from './constants';

export const calculateAgeFromBirthdate = (birthdate) => {
  const today = new Date();
  const birth = new Date(birthdate);
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age--;
  }
  return age;
};

export const formatSymptomData = (formData) => {
  const symptoms = typeof formData.symptoms === 'string' ? formData.symptoms : 
    (formData.symptoms ? formData.symptoms.map(symptom => symptom.value || symptom) : []);
  
  const priorDiagnoses = typeof formData.priorDiagnoses === 'string' ? formData.priorDiagnoses :
    (formData.priorDiagnoses && formData.priorDiagnoses.length > 0 
      ? formData.priorDiagnoses.map(diagnosis => diagnosis.value || diagnosis) 
      : []);

  const age = formData.birthdate ? calculateAgeFromBirthdate(formData.birthdate) : 0;
  
  return {
    user_id: "anonymous_1234",
    input_type: "symptom_query",
    input_data: {
      age: age,
      birthdate: formData.birthdate,
      sex: formData.sex.value,
      height: formData.height,
      weight: formData.weight,
      race: formData.race?.value || formData.race,
      occupation: formData.occupation,
      symptoms,
      duration_months: parseInt(formData.durationMonths || 0),
      prior_diagnoses: priorDiagnoses,
      environmental_factors: formData.environmental_factors || [],
      life_stressors: formData.life_stressors || ""
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
