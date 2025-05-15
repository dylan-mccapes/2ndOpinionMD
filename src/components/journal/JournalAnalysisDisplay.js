import React from 'react';
import { ZONES, STAX_LEVELS } from '../../utils/ethosOfHealth';
import { downloadTimelinePdf } from '../../utils/pdfGenerator';
import '../../styles/Journal.css';

const JournalAnalysisDisplay = ({ analysis, timelineData }) => {
  if (!analysis) return null;
  
  const getStaxColor = (level) => {
    switch (level) {
      case 1: return 'stax-1';
      case 2: return 'stax-2';
      case 3: return 'stax-3';
      case 4: return 'stax-4';
      default: return 'stax-1';
    }
  };
  
  const getZoneColor = (zone) => {
    switch (zone) {
      case 1: return 'zone-1';
      case 2: return 'zone-2';
      case 3: return 'zone-3';
      case 4: return 'zone-4';
      case 5: return 'zone-5';
      default: return 'zone-1';
    }
  };
  
  const getConfidenceColor = (confidence) => {
    if (confidence >= 80) return '#28a745'; // Green
    if (confidence >= 60) return '#ffc107'; // Yellow
    return '#dc3545'; // Red
  };
  
  const handleDownloadPdf = () => {
    if (timelineData) {
      downloadTimelinePdf(timelineData, `diagnosis-timeline-${Date.now()}.pdf`);
    }
  };
  
  return (
    <div className="journal-analysis">
      <h3>AI Analysis</h3>
      
      {/* Analysis section */}
      <div className="analysis-results">
        <h4>Analysis Results:</h4>
        {analysis.patternObservations && (
          <div className="pattern-observations">
            <p><strong>Pattern Observations:</strong> {analysis.patternObservations}</p>
          </div>
        )}
        <p>{analysis.analysis || "No analysis available."}</p>
        <div className="debug-info">
          <button 
            onClick={() => {
              const debugDiv = document.getElementById('journal-debug-info');
              if (debugDiv) {
                debugDiv.style.display = debugDiv.style.display === 'none' ? 'block' : 'none';
              }
            }}
            style={{
              fontSize: '10px',
              padding: '2px 5px',
              marginTop: '5px',
              backgroundColor: '#f0f0f0',
              border: '1px solid #ccc',
              borderRadius: '3px',
              cursor: 'pointer',
              display: process.env.NODE_ENV === 'development' ? 'block' : 'none'
            }}
          >
            Toggle Debug Info
          </button>
          <pre style={{ display: 'none' }}>{JSON.stringify(analysis, null, 2)}</pre>
        </div>
      </div>
      
      {/* Diagnoses section with updated confidence scores */}
      {analysis.diagnoses && analysis.diagnoses.length > 0 && (
        <div className="diagnoses-list">
          <h4>Updated Diagnoses:</h4>
          {analysis.diagnoses.map((diagnosis, index) => (
            <div key={index} className="diagnosis-card">
              <div className="diagnosis-header">
                <h3>{diagnosis.name}</h3>
                <div className="diagnosis-badges">
                  <div className="confidence-badge" style={{ 
                    backgroundColor: getConfidenceColor(diagnosis.confidence)
                  }}>
                    {diagnosis.confidence}% confidence
                  </div>
                  
                  {diagnosis.staxLevel && (
                    <span className={`stax-badge ${getStaxColor(diagnosis.staxLevel)}`}>
                      STAX {diagnosis.staxLevel}
                    </span>
                  )}
                  
                  {diagnosis.zone && (
                    <span className={`zone-badge ${getZoneColor(diagnosis.zone)}`}>
                      Zone {diagnosis.zone}
                    </span>
                  )}
                </div>
              </div>
              
              {diagnosis.status && diagnosis.status !== 'initial' && (
                <div className={`diagnosis-status ${diagnosis.status}`}>
                  {diagnosis.status === 'new' ? 'New Diagnosis' : 
                   diagnosis.status === 'confirmed' ? 'Confirmed' : 
                   diagnosis.status === 'eliminated' ? 'Eliminated' : ''}
                </div>
              )}
              
              {diagnosis.tags && diagnosis.tags.length > 0 && (
                <div className="diagnosis-tags">
                  {diagnosis.tags.map((tag, i) => (
                    <span key={i} className="tag">{tag}</span>
                  ))}
                </div>
              )}
              
              {(diagnosis.staxLevel || diagnosis.zone) && (
                <div className="diagnostic-terrain">
                  <h4>Diagnostic Terrain</h4>
                  <div className="terrain-indicators">
                    {diagnosis.staxLevel && (
                      <div className="terrain-indicator">
                        <span className={`stax-badge ${getStaxColor(diagnosis.staxLevel)}`}>
                          STAX {diagnosis.staxLevel}
                        </span>
                        <p className="terrain-description">
                          {STAX_LEVELS[diagnosis.staxLevel] || `STAX Level ${diagnosis.staxLevel}: Complexity level ${diagnosis.staxLevel}`}
                        </p>
                      </div>
                    )}
                    {diagnosis.zone && (
                      <div className="terrain-indicator">
                        <span className={`zone-badge ${getZoneColor(diagnosis.zone)}`}>
                          Zone {diagnosis.zone}
                        </span>
                        <p className="terrain-description">
                          {ZONES[diagnosis.zone] || `Zone ${diagnosis.zone}: Stability level ${diagnosis.zone}`}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      
      {/* RAG Data section */}
      <div className="analysis-categories">
        <h4>Relevant Data Retrieved:</h4>
        
        {/* Potential Related Conditions section */}
        <div className="analysis-section">
          <h5>Potential Related Conditions:</h5>
          <div className="related-conditions">
            <div className="condition-card">
              <h6>Sarcoidosis <span className="icd-code">ICD: D86.9</span></h6>
              <div className="condition-symptoms">
                <strong>Symptoms:</strong>
                <ul>
                  <li>Fatigue</li>
                  <li>Persistent dry cough</li>
                  <li>Shortness of breath</li>
                  <li>Chest pain</li>
                  <li>Skin lesions (erythema nodosum, lupus pernio)</li>
                  <li>Joint pain and swelling</li>
                  <li>Eye inflammation (uveitis)</li>
                  <li>Enlarged lymph nodes</li>
                  <li>Neurological symptoms (in neurosarcoidosis)</li>
                  <li>Cardiac arrhythmias (in cardiac sarcoidosis)</li>
                </ul>
              </div>
              <div className="condition-lab-markers">
                <strong>Lab Markers:</strong>
                <ul>
                  <li>Elevated angiotensin-converting enzyme (ACE) in 60-70%</li>
                  <li>Elevated calcium levels (in ~10%)</li>
                  <li>Elevated liver enzymes (in hepatic involvement)</li>
                  <li>Elevated inflammatory markers (ESR, CRP)</li>
                  <li>Hypergammaglobulinemia</li>
                  <li>Lymphopenia in some cases</li>
                </ul>
              </div>
            </div>
            
            <div className="condition-card">
              <h6>Chronic Lyme Disease/Post-Treatment Lyme Disease Syndrome <span className="icd-code">ICD: A69.20</span></h6>
              <div className="condition-symptoms">
                <strong>Symptoms:</strong>
                <ul>
                  <li>Persistent fatigue</li>
                  <li>Cognitive difficulties</li>
                  <li>Migratory joint and muscle pain</li>
                  <li>Paresthesias and neuropathic pain</li>
                  <li>Sleep disturbances</li>
                  <li>Headaches</li>
                  <li>Neck stiffness</li>
                  <li>Palpitations and dysautonomia</li>
                  <li>Mood changes</li>
                  <li>Relapsing-remitting pattern of symptoms</li>
                </ul>
              </div>
              <div className="condition-lab-markers">
                <strong>Lab Markers:</strong>
                <ul>
                  <li>Variable serologic testing results (ELISA, Western blot)</li>
                  <li>Possible CD57+ NK cell depression</li>
                  <li>Normal inflammatory markers in many cases</li>
                  <li>Possible coinfection markers (Babesia, Bartonella, etc.)</li>
                  <li>Specialized testing with variable validation (ELISpot, etc.)</li>
                </ul>
              </div>
            </div>
            
            <div className="condition-card">
              <h6>Fibromyalgia <span className="icd-code">ICD: M79.7</span></h6>
              <div className="condition-symptoms">
                <strong>Symptoms:</strong>
                <ul>
                  <li>Widespread musculoskeletal pain</li>
                  <li>Tender points at specific locations</li>
                  <li>Profound fatigue</li>
                  <li>Sleep disturbances</li>
                  <li>Cognitive difficulties ('fibro fog')</li>
                  <li>Headaches</li>
                  <li>Irritable bowel symptoms</li>
                  <li>Paresthesias</li>
                  <li>Temperature sensitivity</li>
                  <li>Anxiety and depression</li>
                </ul>
              </div>
              <div className="condition-lab-markers">
                <strong>Lab Markers:</strong>
                <ul>
                  <li>No specific diagnostic markers</li>
                  <li>Normal inflammatory markers (ESR, CRP)</li>
                  <li>Normal autoantibody profiles</li>
                  <li>Often normal complete blood count</li>
                  <li>Possible vitamin D deficiency</li>
                  <li>Sometimes low-normal thyroid function</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
        
        {/* Autoimmune Information section */}
        <div className="analysis-section">
          <h5>Autoimmune Information:</h5>
          <div className="autoimmune-info">
            <div className="autoimmune-card">
              <h6>#AutoimmuneDx_AutoimmuneMyocarditis</h6>
              <div className="autoimmune-details">
                <p><strong>Type:</strong> confirmedAutoimmuneDx</p>
                <p><strong>Immune Risk Level:</strong> High</p>
                <p><strong>Mechanism:</strong> Immune cells attack the heart muscle, leading to chest pain, arrhythmias, and impaired cardiac function.</p>
                <p><strong>Zone Impact:</strong> +1.0 / +1.0</p>
                <div className="symbolic-meaning">
                  <strong>Symbolic Meaning:</strong>
                  <p>The heart becomes a target—this reflects deep psychic heartbreak or betrayal, buried so deeply the immune system now cries in its place.</p>
                </div>
              </div>
            </div>
            
            <div className="autoimmune-card">
              <h6>#AutoimmuneAdjacentDx_ChronicFatigueSyndrome</h6>
              <div className="autoimmune-details">
                <p><strong>Type:</strong> autoimmuneAdjacentDx</p>
                <p><strong>Immune Risk Level:</strong> Moderate</p>
                <p><strong>Mechanism:</strong> Complex immune dysregulation and chronic inflammation (often post-viral) lead to profound fatigue unrelieved by rest.</p>
                <p><strong>Zone Impact:</strong> +0.5 / +1.0</p>
                <div className="symbolic-meaning">
                  <strong>Symbolic Meaning:</strong>
                  <p>Debilitating exhaustion symbolizes burnout and a soul pushed beyond limits; it may indicate the body and mind telling you to slow down. Underlying stress or unprocessed grief might be manifesting as extreme fatigue, urging one to reclaim balance and self-care.</p>
                </div>
              </div>
            </div>
            
            <div className="autoimmune-card">
              <h6>#AutoimmuneAdjacentDx_PersistentVertigoSyndrome</h6>
              <div className="autoimmune-details">
                <p><strong>Type:</strong> autoimmuneAdjacentDx</p>
                <p><strong>Immune Risk Level:</strong> Moderate</p>
                <p><strong>Mechanism:</strong> Vestibular hypersensitivity, immune dysfunction, and trauma-linked brainstem dysregulation result in chronic dizziness and spatial disorientation.</p>
                <p><strong>Zone Impact:</strong> +0.6 / +0.5</p>
                <div className="symbolic-meaning">
                  <strong>Symbolic Meaning:</strong>
                  <p>No solid ground beneath the feet—this terrain mirrors the loss of emotional footing, instability after betrayal, or a psychic terrain that no longer knows what's real or safe.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Similar Case Studies section */}
        <div className="analysis-section">
          <h5>Similar Case Studies:</h5>
          <div className="case-studies">
            <div className="case-study-card">
              <h6>AIDx-0002: Rheumatoid Arthritis</h6>
              <div className="case-study-details">
                <p><strong>Diagnostic Zone:</strong> 3</p>
                <p><strong>STAX Score:</strong> 3</p>
                <p><strong>Flare Type:</strong> Pathologic</p>
                
                <div className="symptom-timeline">
                  <strong>Symptom Timeline:</strong>
                  <ul>
                    <li>Intermittent aching pain and stiffness in small hand joints, worse in the morning</li>
                    <li>Persistent symmetric joint swelling and warmth in wrists and fingers, with prolonged morning stiffness</li>
                    <li>Increasing fatigue and difficulty with daily tasks due to joint pain</li>
                    <li>Spread of arthritis to larger joints (knees, ankles) over time</li>
                    <li>Joint deformities begin to appear in fingers after years of uncontrolled inflammation</li>
                  </ul>
                </div>
                
                <div className="misdiagnosed-as">
                  <strong>Misdiagnosed As:</strong>
                  <ul>
                    <li>Osteoarthritis</li>
                    <li>Fibromyalgia</li>
                    <li>Lupus</li>
                  </ul>
                </div>
                
                <p><strong>Eventual Diagnosis Time:</strong> 0.7 years</p>
                
                <div className="ethos-tags">
                  <strong>Ethos Terrain Tags:</strong>
                  <ul>
                    <li>smoking</li>
                    <li>periodontal bacteria</li>
                    <li>chronic stress</li>
                  </ul>
                </div>
                
                <div className="suppressors">
                  <strong>Suppressors:</strong>
                  <ul>
                    <li>Methotrexate (DMARD) to reduce autoimmune joint damage</li>
                    <li>Biologic TNF-inhibitor therapy for refractory joint inflammation</li>
                    <li>NSAIDs and low-dose corticosteroids for symptom relief during flares</li>
                    <li>Regular exercise and physical therapy to maintain joint function</li>
                    <li>Smoking cessation and anti-inflammatory diet to support remission</li>
                  </ul>
                </div>
                
                <div className="case-summary">
                  <strong>Case Summary:</strong>
                  <p>A 45-year-old woman developed intermittent hand pain and prolonged morning stiffness that were initially attributed to age-related osteoarthritis. Over months, her joint swelling became persistent and symmetric, involving both wrists and multiple finger joints. Fatigue set in as mundane tasks like opening jars grew difficult. She was misdiagnosed with fibromyalgia and treated only symptomatically for about 8 months. When she failed to improve and started showing joint erosions on X-ray, serologic testing revealed rheumatoid arthritis. By the time of diagnosis, erosive changes had begun in her finger joints. With appropriate treatment (methotrexate and a TNF blocker), her pain and inflammation came under control. In retrospect, an earlier evaluation by rheumatology could have prevented months of unchecked disease activity and joint damage.</p>
                </div>
                
                <div className="citations">
                  <strong>Citations:</strong>
                  <ul>
                    <li>PMID: 36874695, Factors Leading to Diagnostic and Therapeutic Delay of Rheumatoid Arthritis and Their Impact on Disease Outcome, 2023</li>
                    <li>PMID: 29056771, Diagnostic delays in rheumatic diseases with associated arthritis, 2017</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Journal Entry Analysis */}
        <div className="analysis-section">
          <h5>Journal Entry Analysis:</h5>
          <div className="analysis-text">
            {analysis.patternObservations && (
              <p><strong>Pattern Observations:</strong> {analysis.patternObservations}</p>
            )}
            <p>{analysis.analysis || "No analysis available."}</p>
            <div className="debug-info">
              <button 
                onClick={() => {
                  const debugDiv = document.getElementById('journal-debug-info');
                  if (debugDiv) {
                    debugDiv.style.display = debugDiv.style.display === 'none' ? 'block' : 'none';
                  }
                }}
                style={{
                  fontSize: '10px',
                  padding: '2px 5px',
                  marginTop: '5px',
                  backgroundColor: '#f0f0f0',
                  border: '1px solid #ccc',
                  borderRadius: '3px',
                  cursor: 'pointer',
                  display: process.env.NODE_ENV === 'development' ? 'block' : 'none'
                }}
              >
                Toggle Debug Info
              </button>
              <pre style={{ display: 'none' }}>{JSON.stringify(analysis, null, 2)}</pre>
            </div>
          </div>
        </div>
      </div>
      
      {/* PDF Download Button */}
      <div className="timeline-actions">
        <button 
          onClick={handleDownloadPdf} 
          className="btn btn-primary download-btn"
          disabled={!timelineData}
        >
          Download Timeline PDF
        </button>
      </div>
      
      <div className="important-note">
        <p>This analysis is for informational purposes only and is not a medical diagnosis. Please consult with a healthcare professional for proper evaluation and diagnosis.</p>
      </div>
    </div>
  );
};

export default JournalAnalysisDisplay;
