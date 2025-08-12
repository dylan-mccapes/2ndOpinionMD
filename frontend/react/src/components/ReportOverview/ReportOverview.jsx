import React from 'react';
import './ReportOverview.css';

const ReportOverview = ({ report }) => {
  return (
    <section className="report-overview">
      <h2>AI-Powered Second Opinion Report</h2>
      <p>Review the top conditions matched based on your symptoms:</p>
      {report?.conditions?.map((cond, index) => (
        <div key={index} className="condition">
          <h3>{cond.name}</h3>
          <p>Confidence Score: {cond.confidence}%</p>
          <p>Red Flags: {cond.redFlags.join(', ')}</p>
          <p>Suggested Labs: {cond.labs.join(', ')}</p>
        </div>
      ))}
    </section>
  );
};

export default ReportOverview;
