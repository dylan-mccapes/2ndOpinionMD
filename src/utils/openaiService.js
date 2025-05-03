import axios from 'axios';

export const processSymptomInput = async (formData) => {
  try {
    console.log('===== DIAGNOSE REQUEST DEBUG INFO =====');
    console.log('Original form data:', formData);
    
    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error('Authentication required. Please log in.');
    }
    
    let symptoms = [];
    if (formData.symptoms && Array.isArray(formData.symptoms)) {
      symptoms = formData.symptoms.map(s => {
        if (typeof s === 'object' && s.label) {
          return s.label;
        } else if (typeof s === 'string') {
          return s;
        } else {
          return String(s);
        }
      });
    } else if (formData.symptoms && typeof formData.symptoms === 'string') {
      symptoms = [formData.symptoms];
    } else {
      symptoms = ["General discomfort"];
    }
    
    console.log('Processed symptoms array:', symptoms);
    
    const demographics = {
      age: parseInt(formData.age) || 30,
      gender: formData.sex?.value || formData.gender || "Female",
      race: formData.race || "Not specified",
      height: formData.height || "5 feet 8 inches",
      weight: parseInt(formData.weight) || 150,
      occupation: formData.occupation || "Not specified"
    };
    
    console.log('Processed demographics:', demographics);
    
    const apiData = {
      symptoms: symptoms,
      demographics: {
        age: parseInt(formData.age) || 30,
        gender: formData.sex?.value || formData.gender || "Female",
        race: formData.race || "Not specified",
        height: formData.height || "5 feet 8 inches",
        weight: parseInt(formData.weight) || 150,
        occupation: formData.occupation || "Not specified"
      },
      model: "gpt-3.5-turbo" // Match default in backend
    };
    
    console.log('===== DIAGNOSE REQUEST PAYLOAD =====');
    console.log(JSON.stringify(apiData, null, 2));
    
    const requestDebugDiv = document.createElement('div');
    requestDebugDiv.id = 'request-debug-info';
    requestDebugDiv.style.display = 'none';
    requestDebugDiv.style.whiteSpace = 'pre-wrap';
    requestDebugDiv.style.fontFamily = 'monospace';
    requestDebugDiv.style.padding = '10px';
    requestDebugDiv.style.border = '1px solid #ccc';
    requestDebugDiv.style.backgroundColor = '#f5f5f5';
    requestDebugDiv.textContent = JSON.stringify(apiData, null, 2);
    
    const toggleButton = document.createElement('button');
    toggleButton.textContent = 'Toggle Request Debug Info';
    toggleButton.onclick = () => {
      const debugDiv = document.getElementById('request-debug-info');
      if (debugDiv) {
        debugDiv.style.display = debugDiv.style.display === 'none' ? 'block' : 'none';
      }
    };
    
    if (!document.getElementById('request-debug-info')) {
      document.body.appendChild(toggleButton);
      document.body.appendChild(requestDebugDiv);
    }
    
    console.log('===== SENDING REQUEST TO API =====');
    console.log(`Endpoint: ${process.env.REACT_APP_API_URL || 'http://localhost:3001'}/api/diagnose`);
    
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
    
    console.log('===== DIAGNOSE RESPONSE =====');
    console.log(JSON.stringify(response.data, null, 2));
    
    const responseDebugDiv = document.createElement('div');
    responseDebugDiv.id = 'response-debug-info';
    responseDebugDiv.style.display = 'none';
    responseDebugDiv.style.whiteSpace = 'pre-wrap';
    responseDebugDiv.style.fontFamily = 'monospace';
    responseDebugDiv.style.padding = '10px';
    responseDebugDiv.style.border = '1px solid #ccc';
    responseDebugDiv.style.backgroundColor = '#f5f5f5';
    responseDebugDiv.textContent = JSON.stringify(response.data, null, 2);
    
    const toggleResponseButton = document.createElement('button');
    toggleResponseButton.textContent = 'Toggle Response Debug Info';
    toggleResponseButton.onclick = () => {
      const debugDiv = document.getElementById('response-debug-info');
      if (debugDiv) {
        debugDiv.style.display = debugDiv.style.display === 'none' ? 'block' : 'none';
      }
    };
    
    if (!document.getElementById('response-debug-info')) {
      document.body.appendChild(toggleResponseButton);
      document.body.appendChild(responseDebugDiv);
    }
    
    return response.data;
  } catch (error) {
    console.error('===== DIAGNOSE ERROR =====');
    console.error('Error Type:', error.name);
    console.error('Error Message:', error.message);
    
    if (error.response) {
      console.error('Status:', error.response.status);
      console.error('Status Text:', error.response.statusText);
      console.error('Response Headers:', error.response.headers);
      console.error('Response Data:', error.response.data);
      
      const errorDebugDiv = document.createElement('div');
      errorDebugDiv.id = 'error-debug-info';
      errorDebugDiv.style.display = 'block';
      errorDebugDiv.style.whiteSpace = 'pre-wrap';
      errorDebugDiv.style.fontFamily = 'monospace';
      errorDebugDiv.style.padding = '10px';
      errorDebugDiv.style.border = '1px solid #f00';
      errorDebugDiv.style.backgroundColor = '#fff0f0';
      errorDebugDiv.style.color = '#f00';
      errorDebugDiv.innerHTML = `
        <h3>API Error (${error.response.status})</h3>
        <p><strong>Status:</strong> ${error.response.status} ${error.response.statusText}</p>
        <p><strong>Error Message:</strong> ${error.message}</p>
        <p><strong>Response Data:</strong></p>
        <pre>${JSON.stringify(error.response.data, null, 2)}</pre>
      `;
      
      if (!document.getElementById('error-debug-info')) {
        document.body.appendChild(errorDebugDiv);
      } else {
        document.getElementById('error-debug-info').innerHTML = errorDebugDiv.innerHTML;
      }
      
      throw new Error(`API Error (${error.response.status}): ${JSON.stringify(error.response.data)}`);
    } else if (error.request) {
      console.error('Request:', error.request);
      
      const errorDebugDiv = document.createElement('div');
      errorDebugDiv.id = 'error-debug-info';
      errorDebugDiv.style.display = 'block';
      errorDebugDiv.style.whiteSpace = 'pre-wrap';
      errorDebugDiv.style.fontFamily = 'monospace';
      errorDebugDiv.style.padding = '10px';
      errorDebugDiv.style.border = '1px solid #f00';
      errorDebugDiv.style.backgroundColor = '#fff0f0';
      errorDebugDiv.style.color = '#f00';
      errorDebugDiv.innerHTML = `
        <h3>Network Error</h3>
        <p><strong>Error Message:</strong> No response received from server. The server might be down or unreachable.</p>
        <p><strong>Request Details:</strong></p>
        <pre>${JSON.stringify(error.request, null, 2)}</pre>
      `;
      
      if (!document.getElementById('error-debug-info')) {
        document.body.appendChild(errorDebugDiv);
      } else {
        document.getElementById('error-debug-info').innerHTML = errorDebugDiv.innerHTML;
      }
      
      throw new Error('Network Error: No response received from server');
    } else {
      console.error('Error Config:', error.config);
      
      const errorDebugDiv = document.createElement('div');
      errorDebugDiv.id = 'error-debug-info';
      errorDebugDiv.style.display = 'block';
      errorDebugDiv.style.whiteSpace = 'pre-wrap';
      errorDebugDiv.style.fontFamily = 'monospace';
      errorDebugDiv.style.padding = '10px';
      errorDebugDiv.style.border = '1px solid #f00';
      errorDebugDiv.style.backgroundColor = '#fff0f0';
      errorDebugDiv.style.color = '#f00';
      errorDebugDiv.innerHTML = `
        <h3>Request Setup Error</h3>
        <p><strong>Error Message:</strong> ${error.message}</p>
      `;
      
      if (!document.getElementById('error-debug-info')) {
        document.body.appendChild(errorDebugDiv);
      } else {
        document.getElementById('error-debug-info').innerHTML = errorDebugDiv.innerHTML;
      }
      
      throw new Error(`Request Setup Error: ${error.message}`);
    }
  }
};

export const processJournalEntry = async (journalText) => {
  try {
    console.log('===== JOURNAL REQUEST DEBUG INFO =====');
    console.log('Journal text:', journalText);
    
    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error('Authentication required. Please log in.');
    }
    
    const requestData = { entry: journalText };
    
    console.log('===== JOURNAL REQUEST PAYLOAD =====');
    console.log(JSON.stringify(requestData, null, 2));
    
    const requestDebugDiv = document.createElement('div');
    requestDebugDiv.id = 'journal-request-debug-info';
    requestDebugDiv.style.display = 'none';
    requestDebugDiv.style.whiteSpace = 'pre-wrap';
    requestDebugDiv.style.fontFamily = 'monospace';
    requestDebugDiv.style.padding = '10px';
    requestDebugDiv.style.border = '1px solid #ccc';
    requestDebugDiv.style.backgroundColor = '#f5f5f5';
    requestDebugDiv.textContent = JSON.stringify(requestData, null, 2);
    
    const toggleButton = document.createElement('button');
    toggleButton.textContent = 'Toggle Journal Request Debug Info';
    toggleButton.onclick = () => {
      const debugDiv = document.getElementById('journal-request-debug-info');
      if (debugDiv) {
        debugDiv.style.display = debugDiv.style.display === 'none' ? 'block' : 'none';
      }
    };
    
    if (!document.getElementById('journal-request-debug-info')) {
      document.body.appendChild(toggleButton);
      document.body.appendChild(requestDebugDiv);
    }
    
    console.log('===== SENDING REQUEST TO API =====');
    console.log(`Endpoint: ${process.env.REACT_APP_API_URL || 'http://localhost:3001'}/api/journal/journal`);
    
    const response = await axios.post(
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
    
    const responseDebugDiv = document.createElement('div');
    responseDebugDiv.id = 'journal-response-debug-info';
    responseDebugDiv.style.display = 'none';
    responseDebugDiv.style.whiteSpace = 'pre-wrap';
    responseDebugDiv.style.fontFamily = 'monospace';
    responseDebugDiv.style.padding = '10px';
    responseDebugDiv.style.border = '1px solid #ccc';
    responseDebugDiv.style.backgroundColor = '#f5f5f5';
    responseDebugDiv.textContent = JSON.stringify(response.data, null, 2);
    
    const toggleResponseButton = document.createElement('button');
    toggleResponseButton.textContent = 'Toggle Journal Response Debug Info';
    toggleResponseButton.onclick = () => {
      const debugDiv = document.getElementById('journal-response-debug-info');
      if (debugDiv) {
        debugDiv.style.display = debugDiv.style.display === 'none' ? 'block' : 'none';
      }
    };
    
    if (!document.getElementById('journal-response-debug-info')) {
      document.body.appendChild(toggleResponseButton);
      document.body.appendChild(responseDebugDiv);
    }
    
    return response.data;
  } catch (error) {
    console.error('===== JOURNAL ERROR =====');
    console.error('Error Type:', error.name);
    console.error('Error Message:', error.message);
    
    if (error.response) {
      console.error('Status:', error.response.status);
      console.error('Status Text:', error.response.statusText);
      console.error('Response Headers:', error.response.headers);
      console.error('Response Data:', error.response.data);
      
      const errorDebugDiv = document.createElement('div');
      errorDebugDiv.id = 'journal-error-debug-info';
      errorDebugDiv.style.display = 'block';
      errorDebugDiv.style.whiteSpace = 'pre-wrap';
      errorDebugDiv.style.fontFamily = 'monospace';
      errorDebugDiv.style.padding = '10px';
      errorDebugDiv.style.border = '1px solid #f00';
      errorDebugDiv.style.backgroundColor = '#fff0f0';
      errorDebugDiv.style.color = '#f00';
      errorDebugDiv.innerHTML = `
        <h3>Journal API Error (${error.response.status})</h3>
        <p><strong>Status:</strong> ${error.response.status} ${error.response.statusText}</p>
        <p><strong>Error Message:</strong> ${error.message}</p>
        <p><strong>Response Data:</strong></p>
        <pre>${JSON.stringify(error.response.data, null, 2)}</pre>
      `;
      
      if (!document.getElementById('journal-error-debug-info')) {
        document.body.appendChild(errorDebugDiv);
      } else {
        document.getElementById('journal-error-debug-info').innerHTML = errorDebugDiv.innerHTML;
      }
      
      throw new Error(`Journal API Error (${error.response.status}): ${JSON.stringify(error.response.data)}`);
    } else if (error.request) {
      console.error('Request:', error.request);
      
      const errorDebugDiv = document.createElement('div');
      errorDebugDiv.id = 'journal-error-debug-info';
      errorDebugDiv.style.display = 'block';
      errorDebugDiv.style.whiteSpace = 'pre-wrap';
      errorDebugDiv.style.fontFamily = 'monospace';
      errorDebugDiv.style.padding = '10px';
      errorDebugDiv.style.border = '1px solid #f00';
      errorDebugDiv.style.backgroundColor = '#fff0f0';
      errorDebugDiv.style.color = '#f00';
      errorDebugDiv.innerHTML = `
        <h3>Journal Network Error</h3>
        <p><strong>Error Message:</strong> No response received from server. The server might be down or unreachable.</p>
        <p><strong>Request Details:</strong></p>
        <pre>${JSON.stringify(error.request, null, 2)}</pre>
      `;
      
      if (!document.getElementById('journal-error-debug-info')) {
        document.body.appendChild(errorDebugDiv);
      } else {
        document.getElementById('journal-error-debug-info').innerHTML = errorDebugDiv.innerHTML;
      }
      
      throw new Error('Journal Network Error: No response received from server');
    } else {
      console.error('Error Config:', error.config);
      
      const errorDebugDiv = document.createElement('div');
      errorDebugDiv.id = 'journal-error-debug-info';
      errorDebugDiv.style.display = 'block';
      errorDebugDiv.style.whiteSpace = 'pre-wrap';
      errorDebugDiv.style.fontFamily = 'monospace';
      errorDebugDiv.style.padding = '10px';
      errorDebugDiv.style.border = '1px solid #f00';
      errorDebugDiv.style.backgroundColor = '#fff0f0';
      errorDebugDiv.style.color = '#f00';
      errorDebugDiv.innerHTML = `
        <h3>Journal Request Setup Error</h3>
        <p><strong>Error Message:</strong> ${error.message}</p>
      `;
      
      if (!document.getElementById('journal-error-debug-info')) {
        document.body.appendChild(errorDebugDiv);
      } else {
        document.getElementById('journal-error-debug-info').innerHTML = errorDebugDiv.innerHTML;
      }
      
      throw new Error(`Journal Request Setup Error: ${error.message}`);
    }
  }
};
