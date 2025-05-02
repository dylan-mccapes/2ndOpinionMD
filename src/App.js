import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom';
import './App.css';
import './styles/GlobalStyles.css';
import './styles/Journal.css';

import Layout from './components/layout/Layout';

import TestimonialCarousel from './components/TestimonialCarousel/TestimonialCarousel';
import ReportOverview from './components/ReportOverview/ReportOverview';
import FAQAccordion from './components/FAQAccordion/FAQAccordion';
import SymptomIntakeForm from './components/SymptomIntake/SymptomIntakeForm';
import AIResponseDisplay from './components/AIResponse/AIResponseDisplay';

import HeroSection from './components/HeroSection/HeroSection';
import PricingSection from './components/PricingSection/PricingSection';
import DoctorEndorsement from './components/DoctorEndorsement/DoctorEndorsement';

import SplashPage from './components/auth/SplashPage';
import LoginForm from './components/auth/LoginForm';
import RegisterForm from './components/auth/RegisterForm';

import JournalForm from './components/journal/JournalForm';
import JournalList from './components/journal/JournalList';
import JournalDetail from './components/journal/JournalDetail';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  
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
                  {HeroSection && <HeroSection />}
                  <TestimonialCarousel />
                  <DoctorEndorsement />
                  <ReportOverview report={sampleReport} />
                  {PricingSection && <PricingSection />}
                  <FAQAccordion />
                </main>
              </Layout>
            )
          } />
          
          {/* Protected routes */}
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <Layout user={user} onLogout={handleLogout}>
                <main className="App-main">
                  <h1>Welcome, {user?.full_name || 'User'}</h1>
                  <div className="dashboard-actions">
                    <Link to="/journal" className="dashboard-button">
                      Journal
                    </Link>
                    <Link to="/intake" className="dashboard-button">
                      Symptom Intake
                    </Link>
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
                </main>
              </Layout>
            </ProtectedRoute>
          } />
          
          <Route path="/report" element={
            <ProtectedRoute>
              <Layout user={user} onLogout={handleLogout}>
                <main className="App-main">
                  <AIResponseDisplay diagnosticResults={sampleDiagnosticResults} />
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
                </main>
              </Layout>
            </ProtectedRoute>
          } />
          
          <Route path="/journal/new" element={
            <ProtectedRoute>
              <Layout user={user} onLogout={handleLogout}>
                <main className="App-main">
                  <JournalForm />
                </main>
              </Layout>
            </ProtectedRoute>
          } />
          
          <Route path="/journal/:entryId" element={
            <ProtectedRoute>
              <Layout user={user} onLogout={handleLogout}>
                <main className="App-main">
                  <JournalDetail />
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
              </main>
            </Layout>
          } />
          
          <Route path="/disclaimer" element={
            <Layout user={user} onLogout={handleLogout}>
              <main className="App-main">
                <h1>Medical Disclaimer</h1>
                <p>This is the medical disclaimer page.</p>
              </main>
            </Layout>
          } />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
