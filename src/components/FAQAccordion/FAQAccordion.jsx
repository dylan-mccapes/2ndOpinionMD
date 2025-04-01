import React, { useState } from 'react';
import './FAQAccordion.css';

const faqs = [
  {
    question: "How does 2ndOpinionMD.ai work?",
    answer: "Our platform analyzes your symptoms and medical history using AI to identify potential autoimmune conditions that may have been overlooked. We generate a comprehensive report with insights on possible diagnoses, red flag symptoms, and suggested labs or tests."
  },
  {
    question: "Is this a replacement for seeing a doctor?",
    answer: "No, 2ndOpinionMD.ai is not a replacement for professional medical care. Our reports are meant to provide additional insights that you can discuss with your healthcare provider. Always consult with a qualified medical professional for diagnosis and treatment."
  },
  {
    question: "How accurate are the AI-generated reports?",
    answer: "Our AI model is trained on extensive medical literature and diagnostic criteria for autoimmune conditions. While it provides valuable insights, it's important to understand that no AI system is 100% accurate. The reports should be used as a discussion tool with your healthcare provider."
  },
  {
    question: "What happens to my medical data?",
    answer: "We take privacy very seriously. At the MVP stage, we don't store your personal health information. Your symptom data is processed securely to generate your report and is not retained after your session ends."
  },
  {
    question: "Can I share my report with my doctor?",
    answer: "Yes! Our reports are designed to be shared with healthcare providers. You can download your report as a PDF and bring it to your next appointment to facilitate a more informed discussion about your symptoms."
  }
];

const FAQAccordion = () => {
  const [activeIndex, setActiveIndex] = useState(null);

  const toggleAccordion = (index) => {
    setActiveIndex(activeIndex === index ? null : index);
  };

  return (
    <section className="faq-section">
      <div className="container">
        <h2>Frequently Asked Questions</h2>
        <div className="faq-container">
          {faqs.map((faq, index) => (
            <div 
              key={index} 
              className={`faq-item ${activeIndex === index ? 'active' : ''}`}
            >
              <div 
                className="faq-question" 
                onClick={() => toggleAccordion(index)}
              >
                <h3>{faq.question}</h3>
                <span className="faq-icon">
                  {activeIndex === index ? '−' : '+'}
                </span>
              </div>
              <div className="faq-answer">
                <p>{faq.answer}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default FAQAccordion;
