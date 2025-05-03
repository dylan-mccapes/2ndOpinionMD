import axios from 'axios';

export const processSymptomInput = async (formData) => {
  try {
    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error('Authentication required. Please log in.');
    }
    
    const symptoms = formData.symptoms && formData.symptoms.length > 0 
      ? formData.symptoms.map(s => s.label) 
      : ["General discomfort"];
    
    const demographics = {
      age: parseInt(formData.age) || 30,
      gender: formData.sex?.value || "Female", // Use Female as default
      race: formData.race || "Not specified",
      height: formData.height || "5 feet 8 inches",
      weight: parseInt(formData.weight) || 150,
      occupation: formData.occupation || "Not specified"
    };
    
    const apiData = {
      symptoms: symptoms,
      demographics: demographics,
      model: "gpt-3.5-turbo" // Match default in backend
    };
    
    console.log('Sending diagnose request:', JSON.stringify(apiData, null, 2));
    
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
    
    console.log('Diagnose response:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error processing symptom input:', error.response?.data || error.message);
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
