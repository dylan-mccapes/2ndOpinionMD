const { POSSIBLE_DIAGNOSES } = require('./constants');

/**
 * Formats symptom data from the request
 * @param {Object} formData - Form data from the request
 * @returns {Object} - Formatted data
 */
const calculateAgeFromBirthdate = (birthdate) => {
  const today = new Date();
  const birth = new Date(birthdate);
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age--;
  }
  return age;
};

const formatSymptomData = (formData) => {
  const symptoms = Array.isArray(formData.input_data.symptoms) 
    ? formData.input_data.symptoms 
    : [formData.input_data.symptoms];
  
  const priorDiagnoses = formData.input_data.prior_diagnoses && formData.input_data.prior_diagnoses.length > 0 
    ? formData.input_data.prior_diagnoses 
    : [];

  const age = formData.input_data.birthdate ? calculateAgeFromBirthdate(formData.input_data.birthdate) : formData.input_data.age;

  return {
    user_id: formData.user_id || "anonymous_1234",
    input_type: formData.input_type || "symptom_query",
    input_data: {
      age: parseInt(age),
      birthdate: formData.input_data.birthdate,
      sex: formData.input_data.sex,
      height: formData.input_data.height,
      weight: formData.input_data.weight,
      race: formData.input_data.race,
      occupation: formData.input_data.occupation,
      symptoms,
      duration_months: parseInt(formData.input_data.duration_months || 0),
      prior_diagnoses: priorDiagnoses,
      environmental_factors: formData.input_data.environmental_factors || [],
      life_stressors: formData.input_data.life_stressors || ""
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
  generateDiagnosticResults,
  calculateAgeFromBirthdate
};
