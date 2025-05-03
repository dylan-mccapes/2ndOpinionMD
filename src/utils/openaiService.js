import axios from 'axios';

export const processSymptomInput = async (formData) => {
  try {
    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error('Authentication required. Please log in.');
    }
    
    const apiData = {
      symptoms: formData.symptoms.map(s => s.label),
      demographics: {
        age: parseInt(formData.age),
        sex: formData.sex.value,
        duration_months: parseInt(formData.durationMonths),
        prior_diagnoses: formData.priorDiagnoses ? formData.priorDiagnoses.map(d => d.label) : []
      },
      model: process.env.REACT_APP_MODEL_VERSION || "gpt-4-turbo"
    };
    
    const response = await axios.post(
      `${process.env.REACT_APP_API_URL || 'http://localhost:3001'}/api/diagnose`,
      apiData,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );
    
    return response.data;
  } catch (error) {
    console.error('Error processing symptom input:', error);
    throw error;
  }
};

export const processJournalEntry = async (journalText) => {
  try {
    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error('Authentication required. Please log in.');
    }
    
    const response = await axios.post(
      `${process.env.REACT_APP_API_URL || 'http://localhost:3001'}/api/journal/analyze`,
      { entry: journalText },
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );
    
    return response.data;
  } catch (error) {
    console.error('Error processing journal entry:', error);
    throw error;
  }
};
