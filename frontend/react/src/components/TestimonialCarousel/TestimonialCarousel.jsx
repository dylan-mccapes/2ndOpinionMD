import React, { useState, useEffect } from 'react';
import './TestimonialCarousel.css';

const testimonials = [
  {
    quote: "2ndOpinionMD helped me understand my diagnosis when no one else could.",
    author: "Emily R.",
    condition: "Lupus"
  },
  {
    quote: "I finally got clarity after months of confusion. Highly recommended.",
    author: "Mark D.",
    condition: "Rheumatoid Arthritis"
  },
  {
    quote: "The report gave my doctor the exact information needed to order the right tests.",
    author: "Jamie S.",
    condition: "Fibromyalgia"
  }
];

const TestimonialCarousel = () => {
  const [activeIndex, setActiveIndex] = useState(0);
  
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveIndex((current) => (current + 1) % testimonials.length);
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);
  
  return (
    <section className="testimonial-section">
      <div className="testimonial-container">
        <h2>What Patients Are Saying</h2>
        <div className="testimonial-carousel">
          <div className="testimonial-track" style={{ transform: `translateX(-${activeIndex * 100}%)` }}>
            {testimonials.map((item, index) => (
              <div key={index} className="testimonial-card">
                <div className="quote-mark">"</div>
                <p className="testimonial-quote">{item.quote}</p>
                <div className="testimonial-author">
                  <strong>{item.author}</strong>
                  <span className="testimonial-condition">{item.condition}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default TestimonialCarousel;
