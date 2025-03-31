import React from 'react';
import './PricingSection.css';

const PricingSection = () => {
  const pricingPlans = [
    {
      name: 'Basic',
      price: '$29',
      description: 'One-time report for individuals seeking initial insights',
      features: [
        'Symptom analysis',
        'Top 3 potential conditions',
        'PDF report',
        'Email delivery'
      ],
      buttonText: 'Get Started',
      buttonLink: '/intake',
      highlighted: false
    },
    {
      name: 'Premium',
      price: '$49',
      description: 'Comprehensive analysis with detailed recommendations',
      features: [
        'All Basic features',
        'Top 5 potential conditions',
        'Red flag symptoms highlighted',
        'Suggested lab tests',
        'Follow-up consultation'
      ],
      buttonText: 'Choose Premium',
      buttonLink: '/intake?plan=premium',
      highlighted: true
    },
    {
      name: 'Professional',
      price: '$199',
      description: 'For healthcare providers supporting multiple patients',
      features: [
        'All Premium features',
        '5 patient reports',
        'Provider dashboard',
        'Condition comparison',
        'Priority support',
        'HIPAA compliance'
      ],
      buttonText: 'Contact Sales',
      buttonLink: '/contact',
      highlighted: false
    }
  ];

  return (
    <section id="pricing" className="pricing-section">
      <div className="pricing-container">
        <h2>Simple, Transparent Pricing</h2>
        <p className="pricing-description">
          Choose the plan that fits your needs. No hidden fees or subscriptions.
        </p>
        
        <div className="pricing-plans">
          {pricingPlans.map((plan, index) => (
            <div 
              key={index} 
              className={`pricing-card ${plan.highlighted ? 'highlighted' : ''}`}
            >
              <div className="pricing-header">
                <h3>{plan.name}</h3>
                <div className="pricing-price">{plan.price}</div>
                <p className="pricing-subtitle">{plan.description}</p>
              </div>
              
              <ul className="pricing-features">
                {plan.features.map((feature, idx) => (
                  <li key={idx}>{feature}</li>
                ))}
              </ul>
              
              <a 
                href={plan.buttonLink} 
                className={`btn ${plan.highlighted ? 'btn-primary' : 'btn-secondary'}`}
              >
                {plan.buttonText}
              </a>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default PricingSection;
