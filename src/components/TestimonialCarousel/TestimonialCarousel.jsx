import React from 'react';
import './TestimonialCarousel.css';

const testimonials = [
  {
    quote: "2ndOpinionMD helped me understand my diagnosis when no one else could.",
    author: "Emily R."
  },
  {
    quote: "I finally got clarity after months of confusion. Highly recommended.",
    author: "Mark D."
  }
];

const TestimonialCarousel = () => {
  return (
    <section className="testimonial-section">
      <h2>What Patients Are Saying</h2>
      <div className="testimonial-list">
        {testimonials.map((item, index) => (
          <div key={index} className="testimonial-card">
            <p>"{item.quote}"</p>
            <strong>- {item.author}</strong>
          </div>
        ))}
      </div>
    </section>
  );
};

export default TestimonialCarousel;
