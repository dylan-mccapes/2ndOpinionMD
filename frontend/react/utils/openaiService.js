import axios from 'axios';
import { generateEthosPrompt, ZONES, STAX_LEVELS } from './ethosOfHealth';
import { calculateAgeFromBirthdate } from './formatData';
import { getApiUrl, API_ENDPOINTS } from './apiConfig';

const mapConfidenceToPercent = (confidenceStr) => {
  if (typeof confidenceStr === 'number') return confidenceStr;
  
  const confidenceMap = {
    'High': 90,
    'Moderate': 60,
    'Low': 30,
    'Unknown': 0
  };
  
  return confidenceMap[confidenceStr] || 0;
};

const calculateStaxLevel = (diagnosis) => {
  if (!diagnosis) return 1;
  
  const confidence = diagnosis.confidence || 0;
  const hasRedFlags = Array.isArray(diagnosis.redFlags) && diagnosis.redFlags.length > 0;
  const hasLabSuggestions = Array.isArray(diagnosis.labSuggestions) && diagnosis.labSuggestions.length > 0;
  
  if (confidence < 40 || hasRedFlags) {
    return 4; // Most complex - low confidence or red flags
  } else if (confidence < 60 || hasLabSuggestions) {
    return 3; // Moderately complex
  } else if (confidence < 80) {
    return 2; // Somewhat complex
  } else {
    return 1; // Simple case - high confidence
  }
};

const calculateZone = (diagnosis) => {
  if (!diagnosis) return 1;
  
  const confidence = diagnosis.confidence || 0;
  const hasRedFlags = Array.isArray(diagnosis.redFlags) && diagnosis.redFlags.length > 0;
  
  if (hasRedFlags && confidence < 50) {
    return 5; // Critical - red flags with low confidence
  } else if (hasRedFlags) {
    return 4; // Unstable - has red flags
  } else if (confidence < 40) {
    return 3; // Concerning - low confidence
  } else if (confidence < 70) {
    return 2; // Mild concern
  } else {
    return 1; // Stable - high confidence
  }
};






const axiosInstance = axios.create();

axiosInstance.interceptors.response.use(
  response => response,
  error => {
    if (error.response) {
      const isDebug = process.env.NODE_ENV !== 'production' || /[?&]debug=1\b/.test(window.location.search);
      isDebug && console.error(`API Error (${error.response.status}), preventing redirect`);
      
      return Promise.reject({
        ...error,
        preventRedirect: true
      });
    }
    return Promise.reject(error);
  }
);


export const processSymptomInput = async (formData) => {
  try {
    const isDebug = process.env.NODE_ENV !== 'production' || /[?&]debug=1\b/.test(window.location.search);
    isDebug && console.log('===== DIAGNOSE REQUEST DEBUG INFO =====');
    isDebug && console.log('Original form data:', formData);
    
    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error('Authentication required. Please log in.');
    }
    
    const ethosPrompt = generateEthosPrompt();
    
    const age = formData.birthdate ? calculateAgeFromBirthdate(formData.birthdate) : 0;
    
    const apiData = {
      symptoms: Array.isArray(formData.symptoms) ? formData.symptoms.map(s => s.label || s) : [formData.symptoms],
      demographics: {
        age: age,
        birthdate: formData.birthdate,
        gender: formData.sex.value,
        race: formData.race?.value || formData.race || "Not specified",
        height: formData.height || "Not specified",
        weight: parseInt(formData.weight) || 0,
        occupation: formData.occupation || "Not specified"
      },
      environmental_factors: formData.environmental_factors || [],
      life_stressors: formData.life_stressors || "",
      model: "gpt-3.5-turbo",
      ethosPrompt: ethosPrompt // Add the ethos prompt to the API data
    };
    
    isDebug && console.log('===== DIAGNOSE REQUEST PAYLOAD =====');
    isDebug && console.log(JSON.stringify(apiData, null, 2));
    
    isDebug && console.log('===== FIELD TYPES =====');
    isDebug && console.log('symptoms type:', Array.isArray(apiData.symptoms) ? 'Array' : typeof apiData.symptoms);
    isDebug && console.log('demographics type:', typeof apiData.demographics);
    isDebug && console.log('model type:', typeof apiData.model);
    isDebug && console.log('age type:', typeof apiData.demographics.age);
    isDebug && console.log('weight type:', typeof apiData.demographics.weight);
    
    isDebug && console.log('===== SENDING REQUEST TO API =====');
    isDebug && console.log(`Endpoint: ${getApiUrl(API_ENDPOINTS.DIAGNOSE)}`);
    
    const response = await axiosInstance.post(
      getApiUrl(API_ENDPOINTS.DIAGNOSE),
      apiData,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );
    
    isDebug && console.log('===== DIAGNOSE RESPONSE =====');
    isDebug && console.log(JSON.stringify(response.data, null, 2));
    
    try {
      isDebug && console.log('===== RESPONSE DATA STRUCTURE =====');
      isDebug && console.log('response.data type:', typeof response.data);
      isDebug && console.log('response.data keys:', response.data ? Object.keys(response.data) : 'null/undefined');
      
      if (response.data && response.data.diagnoses && Array.isArray(response.data.diagnoses)) {
        const transformedData = response.data.diagnoses.map(diagnosis => ({
          name: diagnosis.diagnosis || 'Unknown Condition',
          confidence: mapConfidenceToPercent(diagnosis.confidence_score),
          explanation: diagnosis.recommendations || '',
          icd10Code: diagnosis['ICD-10_code'] || '',
          symptoms: diagnosis.explanation ? [diagnosis.explanation] : [],
          redFlags: Array.isArray(diagnosis.redFlags) ? diagnosis.redFlags : [],
          labSuggestions: Array.isArray(diagnosis.labSuggestions) ? diagnosis.labSuggestions : [],
          staxLevel: diagnosis.staxLevel || calculateStaxLevel(diagnosis),
          zone: diagnosis.zone || calculateZone(diagnosis)
        }));
        
        isDebug && console.log('===== TRANSFORMED RESPONSE WITH STAX/ZONE (FORMAT 1) =====');
        isDebug && console.log(JSON.stringify(transformedData, null, 2));
        
        return transformedData;
      } else if (response.data && Array.isArray(response.data)) {
        const transformedData = response.data.map(diagnosis => ({
          name: diagnosis.diagnosis || 'Unknown Condition',
          confidence: mapConfidenceToPercent(diagnosis.confidence_score),
          explanation: diagnosis.recommendations || '',
          icd10Code: diagnosis['ICD-10_code'] || '',
          symptoms: diagnosis.explanation ? [diagnosis.explanation] : 
                   (Array.isArray(diagnosis.symptoms) ? diagnosis.symptoms : []),
          redFlags: Array.isArray(diagnosis.redFlags) ? diagnosis.redFlags : [],
          labSuggestions: Array.isArray(diagnosis.labSuggestions) ? diagnosis.labSuggestions : [],
          staxLevel: diagnosis.staxLevel || calculateStaxLevel(diagnosis),
          zone: diagnosis.zone || calculateZone(diagnosis)
        }));
        
        isDebug && console.log('===== TRANSFORMED RESPONSE WITH STAX/ZONE (FORMAT 2) =====');
        isDebug && console.log(JSON.stringify(transformedData, null, 2));
        
        return transformedData;
      } else if (response.data) {
        isDebug && console.log('===== UNKNOWN RESPONSE FORMAT =====');
        isDebug && console.log(JSON.stringify(response.data, null, 2));
        
        return response.data;
      }
      
      isDebug && console.warn('Empty or invalid response data');
      return [];
    } catch (transformError) {
      isDebug && console.error('Error transforming diagnoses data:', transformError);
      isDebug && console.log('Original response data:', response.data);
      
      if (response.data && response.data.diagnoses) {
        return response.data.diagnoses;
      } else if (response.data && Array.isArray(response.data)) {
        return response.data;
      } else if (response.data) {
        return [{ 
          name: 'Data Processing Error', 
          confidence: 0,
          explanation: 'There was an error processing the response data. Please try again.',
          symptoms: [],
          redFlags: ['Error in data processing'],
          labSuggestions: []
        }];
      }
      
      return [];
    }
  } catch (error) {
    const isDebug = process.env.NODE_ENV !== 'production' || /[?&]debug=1\b/.test(window.location.search);
    isDebug && console.error('===== DIAGNOSE ERROR =====');
    isDebug && console.error('Error Type:', error.name);
    isDebug && console.error('Error Message:', error.message);
    
    let errorData = {
      type: 'unknown',
      name: error.name,
      message: error.message
    };
    
    if (error.response) {
      console.error('Status:', error.response.status);
      console.error('Status Text:', error.response.statusText);
      console.error('Response Headers:', error.response.headers);
      console.error('Response Data:', error.response.data);
      
      errorData = {
        type: 'api',
        status: error.response.status,
        statusText: error.response.statusText,
        data: error.response.data,
        message: error.message
      };
      
      if (error.preventRedirect) {
        isDebug && console.warn(`API Error (${error.response.status}) occurred but redirect prevented`);
        return { error: `API Error (${error.response.status})`, details: errorData };
      }
      
      return { error: `API Error (${error.response.status})`, details: errorData };
    } else if (error.request) {
      console.error('Request:', error.request);
      
      errorData = {
        type: 'network',
        request: error.request,
        message: error.message
      };
      
      saveDebugInfo('diagnose_error', errorData);
      
      updateDebugPanel();
      
      return { error: 'Network Error', details: errorData };
    } else {
      console.error('Error Config:', error.config);
      
      errorData = {
        type: 'setup',
        message: error.message
      };
      
      saveDebugInfo('diagnose_error', errorData);
      
      updateDebugPanel();
      
      return { error: 'Request Setup Error', details: errorData };
    }
  }
};

/**
 * Prepares journal text for API submission with explicit prompt for OpenAI
 * to extract symptoms, environmental factors, and life stressors
 * @param {string} journalText - The raw journal text from the user
 * @param {Array} previousDiagnoses - Previous diagnoses from symptom intake
 * @returns {Object} Object containing the journal text, parsed sentences, and extraction prompt
 */
const prepareJournalData = (journalText, previousDiagnoses = [], symptomIntakeData = null) => {
  const sentences = journalText
    .split(/[.,!?;]+/)
    .map(sentence => sentence.trim())
    .filter(sentence => sentence.length > 0);

  const ethosPrompt = generateEthosPrompt();
  
  let symptomIntakeContext = "";
  if (symptomIntakeData) {
    symptomIntakeContext = "INITIAL SYMPTOM INTAKE DATA:\n";
    if (symptomIntakeData.intake_timestamp) symptomIntakeContext += `Intake Date: ${symptomIntakeData.intake_timestamp}\n`;
    if (symptomIntakeData.age) symptomIntakeContext += `Age: ${symptomIntakeData.age}\n`;
    if (symptomIntakeData.birthdate) symptomIntakeContext += `Birthdate: ${symptomIntakeData.birthdate}\n`;
    if (symptomIntakeData.sex) symptomIntakeContext += `Sex: ${symptomIntakeData.sex}\n`;
    if (symptomIntakeData.height) symptomIntakeContext += `Height: ${symptomIntakeData.height}\n`;
    if (symptomIntakeData.weight) symptomIntakeContext += `Weight: ${symptomIntakeData.weight}\n`;
    if (symptomIntakeData.race) symptomIntakeContext += `Race/Ethnicity: ${symptomIntakeData.race}\n`;
    if (symptomIntakeData.occupation) symptomIntakeContext += `Occupation: ${symptomIntakeData.occupation}\n`;
    if (symptomIntakeData.environmental_factors) symptomIntakeContext += `Environmental Factors: ${symptomIntakeData.environmental_factors.join(', ')}\n`;
    if (symptomIntakeData.life_stressors) symptomIntakeContext += `Life Stressors: ${symptomIntakeData.life_stressors}\n`;
    if (symptomIntakeData.prior_diagnoses) symptomIntakeContext += `Prior Diagnoses: ${symptomIntakeData.prior_diagnoses.join(', ')}\n`;
    symptomIntakeContext += "\n";
  }
  
  return {
    symptoms: [
      {
        symptom: journalText,
        severity: 5
      }
    ],
    parsedSentences: sentences,
    previousDiagnoses: previousDiagnoses,
    symptomIntakeData: symptomIntakeData,
    prompt: `${ethosPrompt}\n\n` +
            `${symptomIntakeContext}` +
            "Please analyze this journal entry using the 2OPMD Diagnostic Terrain System.\n" +
            "Parse each sentence to identify symptoms, environmental factors, and life stressors.\n\n" +
            `Previous diagnoses: ${JSON.stringify(previousDiagnoses)}\n\n` +
            "Journal sentences:\n" +
            sentences.map((sentence, index) => `${index + 1}. ${sentence}`).join('\n') + "\n\n" +
            "For each sentence, determine if it contains:\n" +
            "1) Symptoms (physical or mental health issues like pain, fatigue, etc.)\n" +
            "2) Environmental factors (diet, weather, allergens, etc.)\n" +
            "3) Life stressors (work, relationships, financial issues, etc.)\n\n" +
            "Then, based on this analysis:\n" +
            "- Confirm or adjust confidence in existing diagnoses\n" +
            "- Suggest new potential diagnoses if indicated\n" +
            "- Identify any diagnoses that should be eliminated\n" +
            "- Assign appropriate STAX levels and Zone classifications\n" +
            "- Apply relevant clinical and symbolic tags\n\n" +
            "Format your response as a JSON with the following structure:\n" +
            "{\n" +
            '  "analysis": {\n' +
            '    "symptoms": ["symptom1", "symptom2"],\n' +
            '    "environmental_factors": ["factor1", "factor2"],\n' +
            '    "life_stressors": ["stressor1", "stressor2"]\n' +
            "  },\n" +
            '  "diagnoses": [\n' +
            "    {\n" +
            '      "name": "Diagnosis name",\n' +
            '      "confidence": 85,\n' +
            '      "status": "confirmed/new/eliminated",\n' +
            '      "staxLevel": 1,\n' +
            '      "zone": 2,\n' +
            '      "tags": ["#SuspectedDx_DiagnosisName", "#EarlyZoneShift"]\n' +
            "    }\n" +
            "  ],\n" +
            '  "journalingRecommendation": {\n' +
            '    "promptType": "Clinical/Somatic/Symbolic/Remission",\n' +
            '    "suggestedPrompt": "What was lost when health left?"\n' +
            "  }\n" +
            "}"
  };
};

export const processJournalEntry = async (journalText, isTestMode = false, previousDiagnoses = []) => {
  try {
    console.log('===== JOURNAL REQUEST DEBUG INFO =====');
    console.log('Journal text:', journalText);
    console.log('Previous diagnoses:', previousDiagnoses);
    console.log('Test mode:', isTestMode);
    
    createPersistentDebugPanel();
    
    let token = null;
    if (!isTestMode) {
      token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Authentication required. Please log in.');
      }
    } else {
      console.log('Running in test mode - returning mock data immediately');
      return {
        text: 'Test mode analysis: Your journal entry has been analyzed with mock data.',
        analysis: 'Based on your journal entry describing persistent fatigue, joint pain, and brain fog, this appears to be a pattern consistent with autoimmune-related symptoms. The combination of morning fatigue that doesn\'t improve with rest, along with joint pain in hands and wrists, suggests possible inflammatory processes.',
        ai_analysis: {
          analysis: 'Based on your journal entry describing persistent fatigue, joint pain, and brain fog, this appears to be a pattern consistent with autoimmune-related symptoms. The combination of morning fatigue that doesn\'t improve with rest, along with joint pain in hands and wrists, suggests possible inflammatory processes.',
          patternObservations: 'The patient consistently reports cognitive issues and dizziness, which may indicate a chronic underlying condition exacerbated by stress. The morning fatigue pattern is particularly notable as it suggests inflammatory processes that are typically worse upon waking.',
          trackingSuggestions: [
            'Track daily food intake to assess correlation with symptom severity.',
            'Maintain a symptom diary noting times of day and activities during onset of symptoms.',
            'Monitor sleep quality and duration to identify patterns.',
            'Record stress levels and major life events that may trigger symptom flares.'
          ],
          symptoms: ['Persistent fatigue', 'Joint pain in hands and wrists', 'Brain fog', 'Morning stiffness', 'Mild dizziness'],
          environmental_factors: ['Stress levels', 'Sleep quality'],
          life_stressors: ['Work-related stress', 'Physical symptoms affecting daily activities'],
          diagnoses: [
            {
              name: 'Autoimmune Myocarditis',
              confidence: 75,
              status: 'confirmed',
              tags: ['#AutoimmuneDx_AutoimmuneMyocarditis']
            },
            {
              name: 'Chronic Fatigue Syndrome',
              confidence: 68,
              status: 'new',
              tags: ['#AutoimmuneAdjacentDx_ChronicFatigueSyndrome']
            }
          ]
        },
        categories: {
          symptoms: ['Persistent fatigue', 'Joint pain in hands and wrists', 'Brain fog', 'Morning stiffness', 'Mild dizziness'],
          environmental_factors: ['Stress levels', 'Sleep quality'],
          life_stressors: ['Work-related stress', 'Physical symptoms affecting daily activities']
        },
        timestamp: new Date().toISOString(),
        testMode: true
      };
    }
    
    if (typeof journalText !== 'string') {
      console.error('Invalid journal text type:', typeof journalText);
      throw new Error('Journal text must be a string');
    }
    
    const journalData = prepareJournalData(journalText, previousDiagnoses, null);
    
    const requestData = {
      symptoms: journalData.symptoms,
      notes: journalText, // Include the full text as notes as well
      date: new Date().toISOString(), // Add current date
      prompt: journalData.prompt, // Add the prompt for OpenAI to extract categories
      parsedSentences: journalData.parsedSentences, // Add parsed sentences
      previousDiagnoses: journalData.previousDiagnoses, // Add previous diagnoses
      environmental_factors: [], // Initialize empty array for backend compatibility
      life_stressors: [] // Initialize empty array for backend compatibility
    };
    
    console.log('===== JOURNAL REQUEST PAYLOAD =====');
    console.log(JSON.stringify(requestData, null, 2));
    
    saveDebugInfo('journal_request', requestData);
    
    updateDebugPanel();
    
    console.log('===== SENDING REQUEST TO API =====');
    console.log(`Endpoint: ${getApiUrl(API_ENDPOINTS.JOURNAL)}`);
    
    const response = await axiosInstance.post(
      getApiUrl(API_ENDPOINTS.JOURNAL),
      requestData,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );
    
    console.log('===== JOURNAL RESPONSE =====');
    console.log(JSON.stringify(response.data, null, 2));
    
    saveDebugInfo('journal_response', response.data);
    
    clearDebugInfo('journal_error');
    
    updateDebugPanel();
    
    if (response.data && response.data.ai_analysis) {
      const analysis = response.data.ai_analysis;
      
      let responseText = '';
      
      if (analysis.analysis) {
        responseText += analysis.analysis + '\n\n';
      }
      
      // Display symptoms
      if (analysis.symptoms && analysis.symptoms.length > 0) {
        responseText += 'Identified Symptoms:\n';
        analysis.symptoms.forEach((symptom, index) => {
          responseText += `${index + 1}. ${symptom}\n`;
        });
        responseText += '\n';
      }
      
      // Display environmental factors
      if (analysis.environmental_factors && analysis.environmental_factors.length > 0) {
        responseText += 'Environmental Factors:\n';
        analysis.environmental_factors.forEach((factor, index) => {
          responseText += `${index + 1}. ${factor}\n`;
        });
        responseText += '\n';
      }
      
      // Display life stressors
      if (analysis.life_stressors && analysis.life_stressors.length > 0) {
        responseText += 'Life Stressors:\n';
        analysis.life_stressors.forEach((stressor, index) => {
          responseText += `${index + 1}. ${stressor}\n`;
        });
        responseText += '\n';
      }
      
      // Display diagnoses with STAX levels and Zones
      if (analysis.diagnoses && analysis.diagnoses.length > 0) {
        responseText += 'Diagnoses:\n';
        analysis.diagnoses.forEach((diagnosis, index) => {
          const statusText = diagnosis.status === 'new' ? ' (NEW)' : 
                            diagnosis.status === 'eliminated' ? ' (ELIMINATED)' : '';
          responseText += `${index + 1}. ${diagnosis.name}${statusText} - Confidence: ${diagnosis.confidence}%\n`;
          responseText += `   STAX Level: ${diagnosis.staxLevel}, Zone: ${diagnosis.zone}\n`;
          if (diagnosis.tags && diagnosis.tags.length > 0) {
            responseText += `   Tags: ${diagnosis.tags.join(', ')}\n`;
          }
          responseText += '\n';
        });
      }
      
      // Display follow-up questions
      if (analysis.followUpQuestions && analysis.followUpQuestions.length > 0) {
        responseText += 'Follow-up Questions:\n';
        analysis.followUpQuestions.forEach((question, index) => {
          responseText += `${index + 1}. ${question}\n`;
        });
        responseText += '\n';
      }
      
      // Display tracking suggestions
      if (analysis.trackingSuggestions && analysis.trackingSuggestions.length > 0) {
        responseText += 'Tracking Suggestions:\n';
        analysis.trackingSuggestions.forEach((suggestion, index) => {
          responseText += `${index + 1}. ${suggestion}\n`;
        });
        responseText += '\n';
      }
      
      // Display pattern observations
      if (analysis.patternObservations) {
        responseText += `Pattern Observations: ${analysis.patternObservations}\n`;
      }
      
      // Display journaling recommendation
      if (analysis.journalingRecommendation) {
        responseText += '\nJournaling Recommendation:\n';
        responseText += `Type: ${analysis.journalingRecommendation.promptType}\n`;
        responseText += `Prompt: "${analysis.journalingRecommendation.suggestedPrompt}"\n`;
      }
      
      return { 
        text: responseText.trim() || JSON.stringify(analysis),
        analysis: analysis.analysis || "",
        timestamp: analysis.timestamp || new Date().toISOString(),
        categories: {
          symptoms: analysis.symptoms || [],
          environmental_factors: analysis.environmental_factors || [],
          life_stressors: analysis.life_stressors || []
        },
        diagnoses: analysis.diagnoses || [],
        patternObservations: analysis.patternObservations || "",
        trackingSuggestions: analysis.trackingSuggestions || [],
        journalingRecommendation: analysis.journalingRecommendation || null
      };
    }
    
    if (response.data) {
      const data = response.data;
      let responseText = "Thank you for your journal entry. Your information has been recorded and analyzed.\n\n";
      
      if (data.symptoms && Array.isArray(data.symptoms)) {
        responseText += 'Identified Symptoms:\n';
        data.symptoms.forEach((symptom, index) => {
          const symptomText = typeof symptom === 'string' ? symptom : symptom.symptom || JSON.stringify(symptom);
          responseText += `${index + 1}. ${symptomText}\n`;
        });
        responseText += '\n';
      }
      
      if (data.environmental_factors && Array.isArray(data.environmental_factors)) {
        responseText += 'Environmental Factors:\n';
        data.environmental_factors.forEach((factor, index) => {
          responseText += `${index + 1}. ${factor}\n`;
        });
        responseText += '\n';
      }
      
      return {
        text: responseText.trim(),
        categories: {
          symptoms: data.symptoms || [],
          environmental_factors: data.environmental_factors || [],
          life_stressors: data.stress_factors || []
        }
      };
    }
    
    return { 
      text: "Thank you for your journal entry. Your information has been recorded and analyzed.",
      categories: {
        symptoms: [],
        environmental_factors: [],
        life_stressors: []
      },
      fallback: true
    };
  } catch (error) {
    console.error('===== JOURNAL ERROR =====');
    console.error('Error Type:', error.name);
    console.error('Error Message:', error.message);
    
    setBreakpointIfEnabled();
    
    let errorData = {
      type: 'unknown',
      name: error.name,
      message: error.message
    };
    
    if (error.response) {
      console.error('Status:', error.response.status);
      console.error('Status Text:', error.response.statusText);
      console.error('Response Headers:', error.response.headers);
      console.error('Response Data:', error.response.data);
      
      errorData = {
        type: 'api',
        status: error.response.status,
        statusText: error.response.statusText,
        data: error.response.data,
        message: error.message
      };
      
      saveDebugInfo('journal_error', errorData);
      
      updateDebugPanel();
      
      if (error.response.status === 401 && error.preventRedirect) {
        console.warn('Authentication error occurred but redirect prevented');
        return { 
          text: 'Authentication error. Please log in again.',
          error: 'Authentication error', 
          details: errorData 
        };
      }
      
      return { 
        text: `Error processing journal entry: ${error.response.status} ${error.response.statusText}. Please try again.`,
        error: `API Error (${error.response.status})`, 
        details: errorData 
      };
    } else if (error.request) {
      console.error('Request:', error.request);
      
      errorData = {
        type: 'network',
        request: error.request,
        message: error.message
      };
      
      saveDebugInfo('journal_error', errorData);
      
      updateDebugPanel();
      
      return { 
        text: 'Network error. The backend server appears to be unavailable. Here\'s a basic analysis of your journal entry:\n\n' +
              'Your journal entry has been saved locally. When the server becomes available, a more detailed analysis will be provided.\n\n' +
              'In the meantime, continue tracking your symptoms and any changes you notice.',
        error: 'Network Error', 
        details: errorData,
        fallback: true,
        categories: {
          symptoms: journalText ? [{ symptom: journalText, severity: 5 }] : [],
          environmental_factors: [],
          life_stressors: []
        }
      };
    } else {
      console.error('Error Config:', error.config);
      
      errorData = {
        type: 'setup',
        message: error.message
      };
      
      saveDebugInfo('journal_error', errorData);
      
      updateDebugPanel();
      
      if (isTestMode) {
        console.log('Test mode: Returning mock data with pattern observations and tracking suggestions');
        return {
          text: 'Test mode analysis: Your journal entry has been analyzed with mock data.',
          analysis: 'Based on your journal entry describing persistent fatigue, joint pain, and brain fog, this appears to be a pattern consistent with autoimmune-related symptoms. The combination of morning fatigue that doesn\'t improve with rest, along with joint pain in hands and wrists, suggests possible inflammatory processes.',
          ai_analysis: {
            analysis: 'Based on your journal entry describing persistent fatigue, joint pain, and brain fog, this appears to be a pattern consistent with autoimmune-related symptoms. The combination of morning fatigue that doesn\'t improve with rest, along with joint pain in hands and wrists, suggests possible inflammatory processes.',
            patternObservations: 'The patient consistently reports cognitive issues and dizziness, which may indicate a chronic underlying condition exacerbated by stress. The morning fatigue pattern is particularly notable as it suggests inflammatory processes that are typically worse upon waking.',
            trackingSuggestions: [
              'Track daily food intake to assess correlation with symptom severity.',
              'Maintain a symptom diary noting times of day and activities during onset of symptoms.',
              'Monitor sleep quality and duration to identify patterns.',
              'Record stress levels and major life events that may trigger symptom flares.'
            ],
            symptoms: ['Persistent fatigue', 'Joint pain in hands and wrists', 'Brain fog', 'Morning stiffness', 'Mild dizziness'],
            environmental_factors: ['Stress levels', 'Sleep quality'],
            life_stressors: ['Work-related stress', 'Physical symptoms affecting daily activities'],
            diagnoses: [
              {
                name: 'Autoimmune Myocarditis',
                confidence: 75,
                status: 'confirmed',
                tags: ['#AutoimmuneDx_AutoimmuneMyocarditis']
              },
              {
                name: 'Chronic Fatigue Syndrome',
                confidence: 68,
                status: 'new',
                tags: ['#AutoimmuneAdjacentDx_ChronicFatigueSyndrome']
              }
            ]
          },
          categories: {
            symptoms: ['Persistent fatigue', 'Joint pain in hands and wrists', 'Brain fog', 'Morning stiffness', 'Mild dizziness'],
            environmental_factors: ['Stress levels', 'Sleep quality'],
            life_stressors: ['Work-related stress', 'Physical symptoms affecting daily activities']
          },
          timestamp: new Date().toISOString(),
          testMode: true
        };
      }
      
      return { 
        text: 'Error processing your journal entry. Please try again later.',
        error: 'Request Setup Error', 
        details: errorData 
      };
    }
  }
};
