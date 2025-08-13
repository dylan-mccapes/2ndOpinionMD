import React from 'react';
import './HeroSection.css';
import NetworkBackground from '../NetworkBackground/NetworkBackground';
import SecurityBadge from '../SecurityBadge/SecurityBadge';

const HeroSection = () => {
  return (
    <section className="hero-section">
      <NetworkBackground opacity={0.1} />
      <div className="hero-container">
        <div className="hero-content">
          <h1 className="fade-in">Get a Second Opinion on Your Autoimmune Symptoms</h1>
          <p className="fade-in" style={{ animationDelay: '150ms' }}>
            Our AI-powered platform analyzes your symptoms and provides insights
            on potential autoimmune conditions that may have been overlooked.
          </p>
          <div className="hero-cta fade-in" style={{ animationDelay: '300ms' }}>
            <a href="/intake" className="btn btn-primary">
              Start Symptom Analysis
            </a>
            <a href="#pricing" className="btn btn-secondary">
              View Pricing
            </a>
          </div>
          <div className="fade-in" style={{ animationDelay: '450ms' }}>
            <SecurityBadge />
          </div>
        </div>
        <div className="hero-image fade-in" style={{ animationDelay: '300ms' }}>
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
