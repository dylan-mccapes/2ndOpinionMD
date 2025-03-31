import React from 'react';
import './HeroSection.css';

const HeroSection = () => {
  return (
    <section className="hero-section">
      <div className="hero-container">
        <div className="hero-content">
          <h1>Get a Second Opinion on Your Autoimmune Symptoms</h1>
          <p>
            Our AI-powered platform analyzes your symptoms and provides insights
            on potential autoimmune conditions that may have been overlooked.
          </p>
          <div className="hero-buttons">
            <a href="/intake" className="btn btn-primary">
              Start Symptom Analysis
            </a>
            <a href="#pricing" className="btn btn-secondary">
              View Pricing
            </a>
          </div>
        </div>
        <div className="hero-image">
          <img 
            src="/images/doctor-ai.png" 
            alt="AI-powered medical analysis" 
            onError={(e) => {
              e.target.onerror = null;
              e.target.src = 'https://via.placeholder.com/500x400?text=AI+Medical+Analysis';
            }}
          />
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
