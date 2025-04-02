import React from 'react';
import './DoctorEndorsement.css';

const doctors = [
  {
    name: "Dr. Sarah Johnson, MD",
    specialty: "Rheumatology",
    credential: "Board Certified",
    quote: "2ndOpinionMD provides valuable insights that can help patients discuss overlooked possibilities with their healthcare providers.",
    image: "/images/doctor-johnson.jpg" // Will use placeholder if not available
  },
  {
    name: "Dr. Michael Chen, MD, PhD",
    specialty: "Immunology",
    credential: "Harvard Medical School",
    quote: "The AI analysis identifies patterns that can be missed in routine evaluations, especially for complex autoimmune conditions.",
    image: "/images/doctor-chen.jpg" // Will use placeholder if not available
  }
];

const DoctorEndorsement = () => {
  return (
    <section className="doctor-endorsement-section">
      <div className="doctor-endorsement-container">
        <h2>Trusted by Medical Professionals</h2>
        <p className="section-subtitle">Leading specialists recognize the value of our AI-driven analysis</p>
        
        <div className="doctor-cards">
          {doctors.map((doctor, index) => (
            <div key={index} className="doctor-card scroll-reveal">
              <div className="doctor-image">
                <img 
                  src={doctor.image} 
                  alt={doctor.name} 
                  onError={(e) => {
                    e.target.onerror = null;
                    e.target.src = 'https://via.placeholder.com/150x150?text=Doctor+Photo';
                  }}
                />
              </div>
              <div className="doctor-content">
                <h3>{doctor.name}</h3>
                <p className="doctor-credentials">{doctor.specialty} • {doctor.credential}</p>
                <blockquote>"{doctor.quote}"</blockquote>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default DoctorEndorsement;
