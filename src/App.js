import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useNavigate } from 'react-router-dom';
import './App.css';
import './styles/GlobalStyles.css';
import './styles/Journal.css';
import { processJournalEntry } from './utils/openaiService';

import Layout from './components/layout/Layout';

import TestimonialCarousel from './components/TestimonialCarousel/TestimonialCarousel';
import ReportOverview from './components/ReportOverview/ReportOverview';
import FAQAccordion from './components/FAQAccordion/FAQAccordion';
import SymptomIntakeForm from './components/SymptomIntake/SymptomIntakeForm';
import AIResponseDisplay from './components/AIResponse/AIResponseDisplay';

import HeroSection from './components/HeroSection/HeroSection';
import DoctorEndorsement from './components/DoctorEndorsement/DoctorEndorsement';

import SplashPage from './components/auth/SplashPage';
import LoginForm from './components/auth/LoginForm';
import RegisterForm from './components/auth/RegisterForm';

import JournalForm from './components/journal/JournalForm';
import JournalList from './components/journal/JournalList';
import JournalDetail from './components/journal/JournalDetail';
import JournalEntryForm from './components/journal/JournalEntryForm.jsx';
import JournalResponse from './components/journal/JournalResponse.jsx';

function AppContent() {
  const navigate = useNavigate();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [diagnosticResults, setDiagnosticResults] = useState(null);
  const [journalResponse, setJournalResponse] = useState(null);
  
  useEffect(() => {
    const token = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    
    if (token && storedUser) {
      setIsAuthenticated(true);
      setUser(JSON.parse(storedUser));
    }
  }, []);
  
  const handleLoginSuccess = (userData) => {
    setIsAuthenticated(true);
    setUser(userData);
  };
  
  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setIsAuthenticated(false);
    setUser(null);
  };
  
  const ProtectedRoute = ({ children }) => {
    if (!isAuthenticated) {
      return <Navigate to="/login" />;
    }
    return children;
  };
  
  const sampleReport = {
    conditions: [
      {
        name: "Rheumatoid Arthritis",
        confidence: 85,
        redFlags: ["Morning joint stiffness", "Symmetric joint involvement"],
        labs: ["Rheumatoid Factor", "Anti-CCP Antibodies", "ESR/CRP"]
      },
      {
        name: "Lupus (SLE)",
        confidence: 62,
        redFlags: ["Sun sensitivity", "Fatigue", "Joint pain"],
        labs: ["ANA Test", "Anti-dsDNA", "Complete Blood Count"]
      },
      {
        name: "Fibromyalgia",
        confidence: 45,
        redFlags: ["Widespread pain", "Sleep disturbances", "Cognitive difficulties"],
        labs: ["Rule-out tests", "Sleep study"]
      }
    ]
  };
  
  const sampleDiagnosticResults = [
    {
      name: "Rheumatoid Arthritis",
      confidence: 85,
      symptoms: ["joint_pain", "morning_stiffness", "fatigue", "symmetric_swelling"],
      redFlags: ["Morning joint stiffness lasting >60 minutes", "Symmetric joint involvement"],
      labSuggestions: ["Rheumatoid Factor (RF)", "Anti-CCP Antibodies", "ESR/CRP"]
    },
    {
      name: "Lupus (SLE)",
      confidence: 62,
      symptoms: ["joint_pain", "fatigue", "skin_rash", "sun_sensitivity"],
      redFlags: ["Sun sensitivity causing rash", "Fatigue unrelieved by rest"],
      labSuggestions: ["ANA Test", "Anti-dsDNA", "Complete Blood Count"]
    }
  ];
  
  const handleSymptomFormSubmit = (data) => {
    try {
      console.log('Received diagnostic results:', data);
      
      if (!data) {
        console.error('Invalid diagnostic results received:', data);
        throw new Error('Invalid diagnostic results received');
      }
      
      setDiagnosticResults(data);
      
      navigate('/report');
    } catch (error) {
      console.error('Error handling symptom form submission:', error);
      setDiagnosticResults(sampleDiagnosticResults);
      navigate('/report');
    }
  };
  
  const handleJournalSubmit = async (entry) => {
    try {
      const response = await processJournalEntry(entry);
      setJournalResponse(response);
    } catch (error) {
      console.error('Error processing journal entry:', error);
      setJournalResponse({ 
        text: "I'm sorry, I couldn't process your journal entry at this time. Please try again later." 
      });
    }
  };

  return (
    <Router>
      <div className="App">
        <Routes>
          {/* Public routes */}
          <Route path="/splash" element={<SplashPage />} />
          <Route path="/login" element={<LoginForm onLoginSuccess={handleLoginSuccess} />} />
          <Route path="/register" element={<RegisterForm />} />
          
          {/* Redirect to splash if not authenticated */}
          <Route path="/" element={
            !isAuthenticated ? <Navigate to="/splash" /> : (
              <Layout user={user} onLogout={handleLogout}>
                <main className="App-main">
                  <div className="dashboard-container">
                    <h1>Welcome, {user?.full_name || 'User'}</h1>
                    
                    <TestimonialCarousel />
                    
                    <div className="dashboard-description">
                      <h2>Simple, Transparent Service</h2>
                      <p>
                        Choose the option that fits your needs. Track your symptoms, get insights, and share with your healthcare provider.
                      </p>
                      <p>
                        Our AI-powered platform provides second-opinion reports for autoimmune disease diagnosis support, helping you on your diagnostic journey.
                      </p>
                      <p>
                        No hidden fees or subscriptions. We're currently in beta testing and would love your feedback!
                      </p>
                    </div>
                    
                    <div className="dashboard-features">
                      <div className="feature-item">
                        <h3>Symptom Analysis</h3>
                        <ul>
                          <li>Comprehensive symptom evaluation</li>
                          <li>Potential conditions identified</li>
                          <li>Red flag symptoms highlighted</li>
                          <li>Suggested lab tests</li>
                        </ul>
                      </div>
                      <div className="feature-item">
                        <h3>Symptom Journal</h3>
                        <ul>
                          <li>Track symptoms over time</li>
                          <li>AI-powered insights</li>
                          <li>Pattern recognition</li>
                          <li>Share with healthcare providers</li>
                        </ul>
                      </div>
                    </div>
                    
                    <div className="dashboard-buttons">
                      <Link to="/intake" className="dashboard-button symptom-button">
                        <h3>Symptom Analysis</h3>
                        <p>Enter your symptoms for an AI-powered analysis</p>
                      </Link>
                      <Link to="/journal/new" className="dashboard-button journal-button">
                        <h3>Symptom Journal</h3>
                        <p>Track your symptoms over time and get insights</p>
                      </Link>
                    </div>
                  </div>
                </main>
              </Layout>
            )
          } />
          
          {/* Protected routes */}
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <Layout user={user} onLogout={handleLogout}>
                <main className="App-main">
                  <div className="dashboard-container">
                    <h1>Welcome, {user?.full_name || 'User'}</h1>
                    
                    <TestimonialCarousel />
                    
                    <div className="dashboard-description">
                      <h2>Simple, Transparent Service</h2>
                      <p>
                        Choose the option that fits your needs. Track your symptoms, get insights, and share with your healthcare provider.
                      </p>
                      <p>
                        Our AI-powered platform provides second-opinion reports for autoimmune disease diagnosis support, helping you on your diagnostic journey.
                      </p>
                      <p>
                        No hidden fees or subscriptions. We're currently in beta testing and would love your feedback!
                      </p>
                    </div>
                    
                    <div className="dashboard-features">
                      <div className="feature-item">
                        <h3>Symptom Analysis</h3>
                        <ul>
                          <li>Comprehensive symptom evaluation</li>
                          <li>Potential conditions identified</li>
                          <li>Red flag symptoms highlighted</li>
                          <li>Suggested lab tests</li>
                        </ul>
                      </div>
                      <div className="feature-item">
                        <h3>Symptom Journal</h3>
                        <ul>
                          <li>Track symptoms over time</li>
                          <li>AI-powered insights</li>
                          <li>Pattern recognition</li>
                          <li>Share with healthcare providers</li>
                        </ul>
                      </div>
                    </div>
                    
                    <div className="dashboard-buttons">
                      <Link to="/intake" className="dashboard-button symptom-button">
                        <h3>Symptom Analysis</h3>
                        <p>Enter your symptoms for an AI-powered analysis</p>
                      </Link>
                      <Link to="/journal/new" className="dashboard-button journal-button">
                        <h3>Symptom Journal</h3>
                        <p>Track your symptoms over time and get insights</p>
                      </Link>
                    </div>
                  </div>
                </main>
              </Layout>
            </ProtectedRoute>
          } />
          
          <Route path="/intake" element={
            <ProtectedRoute>
              <Layout user={user} onLogout={handleLogout}>
                <main className="App-main">
                  <SymptomIntakeForm onSubmit={handleSymptomFormSubmit} />
                  <div className="home-button-container">
                    <Link to="/dashboard" className="btn btn-secondary home-button">Return to Dashboard</Link>
                  </div>
                </main>
              </Layout>
            </ProtectedRoute>
          } />
          
          <Route path="/report" element={
            <ProtectedRoute>
              <Layout user={user} onLogout={handleLogout}>
                <main className="App-main">
                  <AIResponseDisplay diagnosticResults={diagnosticResults || sampleDiagnosticResults} />
                  <div className="home-button-container">
                    <Link to="/dashboard" className="btn btn-secondary home-button">Return to Dashboard</Link>
                  </div>
                </main>
              </Layout>
            </ProtectedRoute>
          } />
          
          {/* Journal routes */}
          <Route path="/journal" element={
            <ProtectedRoute>
              <Layout user={user} onLogout={handleLogout}>
                <main className="App-main">
                  <JournalList />
                  <div className="home-button-container">
                    <Link to="/dashboard" className="btn btn-secondary home-button">Return to Dashboard</Link>
                  </div>
                </main>
              </Layout>
            </ProtectedRoute>
          } />
          
          <Route path="/journal/new" element={
            <ProtectedRoute>
              <Layout user={user} onLogout={handleLogout}>
                <main className="App-main">
                  <JournalEntryForm onSubmit={handleJournalSubmit} />
                  {journalResponse && <JournalResponse response={journalResponse} />}
                  <div className="home-button-container">
                    <Link to="/dashboard" className="btn btn-secondary home-button">Return to Dashboard</Link>
                  </div>
                </main>
              </Layout>
            </ProtectedRoute>
          } />
          
          <Route path="/journal/:entryId" element={
            <ProtectedRoute>
              <Layout user={user} onLogout={handleLogout}>
                <main className="App-main">
                  <JournalDetail />
                  <div className="home-button-container">
                    <Link to="/dashboard" className="btn btn-secondary home-button">Return to Dashboard</Link>
                  </div>
                </main>
              </Layout>
            </ProtectedRoute>
          } />
          
          {/* Public information pages */}
          <Route path="/privacy" element={
            <Layout user={user} onLogout={handleLogout}>
              <main className="App-main">
                <h1>Privacy Policy</h1>
                <p>This is the privacy policy page.</p>
                <div className="home-button-container">
                  <Link to="/dashboard" className="btn btn-secondary home-button">Return to Dashboard</Link>
                </div>
              </main>
            </Layout>
          } />
          
          <Route path="/disclaimer" element={
            <Layout user={user} onLogout={handleLogout}>
              <main className="App-main">
                <h1>Medical Disclaimer</h1>
                <p>This is the medical disclaimer page.</p>
                <div className="home-button-container">
                  <Link to="/dashboard" className="btn btn-secondary home-button">Return to Dashboard</Link>
                </div>
              </main>
            </Layout>
          } />
        </Routes>
      </div>
    </Router>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
