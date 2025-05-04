import axios from 'axios';

const saveDebugInfo = (key, data) => {
  try {
    localStorage.setItem(key, JSON.stringify(data));
  } catch (e) {
    console.error('Error saving debug info to localStorage:', e);
  }
};

const getDebugInfo = (key) => {
  try {
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : null;
  } catch (e) {
    console.error('Error retrieving debug info from localStorage:', e);
    return null;
  }
};

const clearDebugInfo = (key) => {
  try {
    localStorage.removeItem(key);
  } catch (e) {
    console.error('Error clearing debug info from localStorage:', e);
  }
};

const createPersistentDebugPanel = () => {
  if (document.getElementById('persistent-debug-panel')) {
    return;
  }
  
  const panel = document.createElement('div');
  panel.id = 'persistent-debug-panel';
  panel.style.position = 'fixed';
  panel.style.bottom = '10px';
  panel.style.right = '10px';
  panel.style.zIndex = '9999';
  panel.style.backgroundColor = '#f8f9fa';
  panel.style.border = '1px solid #dee2e6';
  panel.style.borderRadius = '4px';
  panel.style.padding = '10px';
  panel.style.boxShadow = '0 0 10px rgba(0,0,0,0.1)';
  panel.style.maxWidth = '400px';
  panel.style.maxHeight = '80vh';
  panel.style.overflow = 'auto';
  panel.style.display = 'none';
  
  const toggleButton = document.createElement('button');
  toggleButton.textContent = 'Debug Panel';
  toggleButton.style.position = 'fixed';
  toggleButton.style.bottom = '10px';
  toggleButton.style.right = '10px';
  toggleButton.style.zIndex = '10000';
  toggleButton.style.padding = '5px 10px';
  toggleButton.style.backgroundColor = '#007bff';
  toggleButton.style.color = 'white';
  toggleButton.style.border = 'none';
  toggleButton.style.borderRadius = '4px';
  toggleButton.style.cursor = 'pointer';
  
  toggleButton.onclick = () => {
    if (panel.style.display === 'none') {
      panel.style.display = 'block';
      updateDebugPanel();
    } else {
      panel.style.display = 'none';
    }
  };
  
  document.body.appendChild(toggleButton);
  document.body.appendChild(panel);
  
  updateDebugPanel();
};

const updateDebugPanel = () => {
  const panel = document.getElementById('persistent-debug-panel');
  if (!panel) return;
  
  panel.innerHTML = '';
  
  const title = document.createElement('h3');
  title.textContent = 'Debug Information';
  title.style.marginTop = '0';
  panel.appendChild(title);
  
  const clearButton = document.createElement('button');
  clearButton.textContent = 'Clear All Debug Info';
  clearButton.style.marginBottom = '10px';
  clearButton.style.padding = '5px 10px';
  clearButton.style.backgroundColor = '#dc3545';
  clearButton.style.color = 'white';
  clearButton.style.border = 'none';
  clearButton.style.borderRadius = '4px';
  clearButton.style.cursor = 'pointer';
  clearButton.onclick = () => {
    clearDebugInfo('diagnose_request');
    clearDebugInfo('diagnose_response');
    clearDebugInfo('diagnose_error');
    clearDebugInfo('journal_request');
    clearDebugInfo('journal_response');
    clearDebugInfo('journal_error');
    updateDebugPanel();
  };
  panel.appendChild(clearButton);
  
  const breakpointToggle = document.createElement('div');
  breakpointToggle.style.marginBottom = '10px';
  
  const breakpointCheckbox = document.createElement('input');
  breakpointCheckbox.type = 'checkbox';
  breakpointCheckbox.id = 'debug-breakpoint-toggle';
  breakpointCheckbox.checked = localStorage.getItem('debug_breakpoints_enabled') === 'true';
  breakpointCheckbox.onchange = () => {
    localStorage.setItem('debug_breakpoints_enabled', breakpointCheckbox.checked);
  };
  
  const breakpointLabel = document.createElement('label');
  breakpointLabel.htmlFor = 'debug-breakpoint-toggle';
  breakpointLabel.textContent = 'Enable Breakpoints on Errors';
  breakpointLabel.style.marginLeft = '5px';
  
  breakpointToggle.appendChild(breakpointCheckbox);
  breakpointToggle.appendChild(breakpointLabel);
  panel.appendChild(breakpointToggle);
  
  const sections = [
    { key: 'diagnose_request', title: 'Diagnose Request' },
    { key: 'diagnose_response', title: 'Diagnose Response' },
    { key: 'diagnose_error', title: 'Diagnose Error' },
    { key: 'journal_request', title: 'Journal Request' },
    { key: 'journal_response', title: 'Journal Response' },
    { key: 'journal_error', title: 'Journal Error' }
  ];
  
  sections.forEach(section => {
    const data = getDebugInfo(section.key);
    if (data) {
      const sectionDiv = document.createElement('div');
      sectionDiv.style.marginBottom = '15px';
      
      const sectionTitle = document.createElement('h4');
      sectionTitle.textContent = section.title;
      sectionTitle.style.marginBottom = '5px';
      sectionDiv.appendChild(sectionTitle);
      
      const sectionContent = document.createElement('pre');
      sectionContent.style.whiteSpace = 'pre-wrap';
      sectionContent.style.backgroundColor = '#f5f5f5';
      sectionContent.style.padding = '10px';
      sectionContent.style.borderRadius = '4px';
      sectionContent.style.fontSize = '12px';
      sectionContent.style.maxHeight = '200px';
      sectionContent.style.overflow = 'auto';
      sectionContent.textContent = JSON.stringify(data, null, 2);
      sectionDiv.appendChild(sectionContent);
      
      panel.appendChild(sectionDiv);
    }
  });
  
  if (panel.childElementCount <= 3) { // title, clear button, and breakpoint toggle
    const noData = document.createElement('p');
    noData.textContent = 'No debug information available.';
    noData.style.fontStyle = 'italic';
    panel.appendChild(noData);
  }
};

const axiosInstance = axios.create();

axiosInstance.interceptors.response.use(
  response => response,
  error => {
    if (error.response) {
      console.error(`API Error (${error.response.status}), preventing redirect`);
      saveDebugInfo('api_error', {
        status: error.response.status,
        statusText: error.response.statusText,
        data: error.response.data,
        message: error.message
      });
      
      return Promise.reject({
        ...error,
        preventRedirect: true
      });
    }
    return Promise.reject(error);
  }
);

const setBreakpointIfEnabled = () => {
  if (localStorage.getItem('debug_breakpoints_enabled') === 'true') {
    console.log('Debug breakpoint would be set here if debugger statements were enabled');
  }
};

export const processSymptomInput = async (formData) => {
  try {
    console.log('===== DIAGNOSE REQUEST DEBUG INFO =====');
    console.log('Original form data:', formData);
    
    createPersistentDebugPanel();
    
    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error('Authentication required. Please log in.');
    }
    
    const apiData = {
      symptoms: formData.symptoms.map(s => s.label),
      demographics: {
        age: parseInt(formData.age),
        gender: formData.sex.value,
        race: formData.race || "Not specified",
        height: formData.height || "Not specified",
        weight: parseInt(formData.weight) || 0,
        occupation: formData.occupation || "Not specified"
      },
      model: "gpt-3.5-turbo"
    };
    
    console.log('===== DIAGNOSE REQUEST PAYLOAD =====');
    console.log(JSON.stringify(apiData, null, 2));
    
    console.log('===== FIELD TYPES =====');
    console.log('symptoms type:', Array.isArray(apiData.symptoms) ? 'Array' : typeof apiData.symptoms);
    console.log('demographics type:', typeof apiData.demographics);
    console.log('model type:', typeof apiData.model);
    console.log('age type:', typeof apiData.demographics.age);
    console.log('weight type:', typeof apiData.demographics.weight);
    
    saveDebugInfo('diagnose_request', apiData);
    
    updateDebugPanel();
    
    console.log('===== SENDING REQUEST TO API =====');
    console.log(`Endpoint: ${process.env.REACT_APP_API_URL || 'http://localhost:3001'}/api/diagnose`);
    
    const response = await axiosInstance.post(
      `${process.env.REACT_APP_API_URL || 'http://localhost:3001'}/api/diagnose`,
      apiData,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );
    
    console.log('===== DIAGNOSE RESPONSE =====');
    console.log(JSON.stringify(response.data, null, 2));
    
    saveDebugInfo('diagnose_response', response.data);
    
    clearDebugInfo('diagnose_error');
    
    updateDebugPanel();
    
    try {
      console.log('===== RESPONSE DATA STRUCTURE =====');
      console.log('response.data type:', typeof response.data);
      console.log('response.data keys:', response.data ? Object.keys(response.data) : 'null/undefined');
      
      if (response.data && response.data.diagnoses && Array.isArray(response.data.diagnoses)) {
        const transformedData = response.data.diagnoses.map(diagnosis => ({
          name: diagnosis.name || 'Unknown Condition',
          confidence: diagnosis.confidence || 0,
          symptoms: diagnosis.explanation ? [diagnosis.explanation] : [],
          redFlags: Array.isArray(diagnosis.redFlags) ? diagnosis.redFlags : [],
          labSuggestions: Array.isArray(diagnosis.labSuggestions) ? diagnosis.labSuggestions : []
        }));
        
        console.log('===== TRANSFORMED RESPONSE (FORMAT 1) =====');
        console.log(JSON.stringify(transformedData, null, 2));
        
        return transformedData;
      } else if (response.data && Array.isArray(response.data)) {
        const transformedData = response.data.map(diagnosis => ({
          name: diagnosis.name || 'Unknown Condition',
          confidence: diagnosis.confidence || 0,
          symptoms: diagnosis.explanation ? [diagnosis.explanation] : 
                   (Array.isArray(diagnosis.symptoms) ? diagnosis.symptoms : []),
          redFlags: Array.isArray(diagnosis.redFlags) ? diagnosis.redFlags : [],
          labSuggestions: Array.isArray(diagnosis.labSuggestions) ? diagnosis.labSuggestions : []
        }));
        
        console.log('===== TRANSFORMED RESPONSE (FORMAT 2) =====');
        console.log(JSON.stringify(transformedData, null, 2));
        
        return transformedData;
      } else if (response.data) {
        console.log('===== UNKNOWN RESPONSE FORMAT =====');
        console.log(JSON.stringify(response.data, null, 2));
        
        return response.data;
      }
      
      console.warn('Empty or invalid response data');
      return [];
    } catch (transformError) {
      console.error('Error transforming diagnoses data:', transformError);
      console.log('Original response data:', response.data);
      
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
    console.error('===== DIAGNOSE ERROR =====');
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
      
      saveDebugInfo('diagnose_error', errorData);
      
      updateDebugPanel();
      
      if (error.preventRedirect) {
        console.warn(`API Error (${error.response.status}) occurred but redirect prevented`);
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

export const processJournalEntry = async (journalText) => {
  try {
    console.log('===== JOURNAL REQUEST DEBUG INFO =====');
    console.log('Journal text:', journalText);
    
    createPersistentDebugPanel();
    
    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error('Authentication required. Please log in.');
    }
    
    const requestData = { entry: journalText };
    
    console.log('===== JOURNAL REQUEST PAYLOAD =====');
    console.log(JSON.stringify(requestData, null, 2));
    
    saveDebugInfo('journal_request', requestData);
    
    updateDebugPanel();
    
    console.log('===== SENDING REQUEST TO API =====');
    console.log(`Endpoint: ${process.env.REACT_APP_API_URL || 'http://localhost:3001'}/api/journal/journal`);
    
    const response = await axiosInstance.post(
      `${process.env.REACT_APP_API_URL || 'http://localhost:3001'}/api/journal/journal`,
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
    
    return response.data;
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
        return { error: 'Authentication error', details: errorData };
      }
      
      return { error: `API Error (${error.response.status})`, details: errorData };
    } else if (error.request) {
      console.error('Request:', error.request);
      
      errorData = {
        type: 'network',
        request: error.request,
        message: error.message
      };
      
      saveDebugInfo('journal_error', errorData);
      
      updateDebugPanel();
      
      return { error: 'Network Error', details: errorData };
    } else {
      console.error('Error Config:', error.config);
      
      errorData = {
        type: 'setup',
        message: error.message
      };
      
      saveDebugInfo('journal_error', errorData);
      
      updateDebugPanel();
      
      return { error: 'Request Setup Error', details: errorData };
    }
  }
};
