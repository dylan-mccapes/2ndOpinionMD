const { POSSIBLE_DIAGNOSES } = require('./constants');

/**
 * Formats symptom data from the request
 * @param {Object} formData - Form data from the request
 * @returns {Object} - Formatted data
 */
const formatSymptomData = (formData) => {
  const symptoms = Array.isArray(formData.input_data.symptoms) 
    ? formData.input_data.symptoms 
    : [formData.input_data.symptoms];
  
  const priorDiagnoses = formData.input_data.prior_diagnoses && formData.input_data.prior_diagnoses.length > 0 
    ? formData.input_data.prior_diagnoses 
    : [];

  return {
    user_id: formData.user_id || "anonymous_1234",
    input_type: formData.input_type || "symptom_query",
    input_data: {
      age: parseInt(formData.input_data.age),
      sex: formData.input_data.sex,
      symptoms,
      duration_months: parseInt(formData.input_data.duration_months || 0),
      prior_diagnoses: priorDiagnoses
    },
    context_flags: formData.context_flags || {
      hipaa_mode: true,
      model_version: process.env.MODEL_VERSION || "gpt-4-turbo",
      return_format: "json"
    }
  };
};

/**
 * Generates diagnostic results based on symptom data
 * @param {Object} formData - Formatted form data
 * @returns {Array} - Array of diagnostic results
 */
const generateDiagnosticResults = (formData) => {
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

module.exports = {
  formatSymptomData,
  generateDiagnosticResults
};
