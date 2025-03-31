import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';
import './styles/GlobalStyles.css';

import Layout from './components/layout/Layout';

import TestimonialCarousel from './components/TestimonialCarousel/TestimonialCarousel';
import ReportOverview from './components/ReportOverview/ReportOverview';
import FAQAccordion from './components/FAQAccordion/FAQAccordion';
import SymptomIntakeForm from './components/SymptomIntake/SymptomIntakeForm';
import AIResponseDisplay from './components/AIResponse/AIResponseDisplay';

import HeroSection from './components/HeroSection/HeroSection';
import PricingSection from './components/PricingSection/PricingSection';

function App() {
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
        <Layout>
          <Routes>
            <Route path="/" element={
              <main className="App-main">
                {HeroSection && <HeroSection />}
                <TestimonialCarousel />
                <ReportOverview report={sampleReport} />
                {PricingSection && <PricingSection />}
                <FAQAccordion />
              </main>
            } />
            
            <Route path="/intake" element={
              <main className="App-main">
                <SymptomIntakeForm onSubmit={handleSymptomFormSubmit} />
              </main>
            } />
            
            <Route path="/report" element={
              <main className="App-main">
                <AIResponseDisplay diagnosticResults={sampleDiagnosticResults} />
              </main>
            } />
            
            <Route path="/privacy" element={
              <main className="App-main">
                <h1>Privacy Policy</h1>
                <p>This is the privacy policy page.</p>
              </main>
            } />
            
            <Route path="/disclaimer" element={
              <main className="App-main">
                <h1>Medical Disclaimer</h1>
                <p>This is the medical disclaimer page.</p>
              </main>
            } />
          </Routes>
        </Layout>
      </div>
    </Router>
  );
}

export default App;
