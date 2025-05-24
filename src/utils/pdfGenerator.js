import jsPDF from 'jspdf';

/**
 * Generates a PDF report from the diagnostic results
 * @param {Array} diagnosticResults - Array of diagnostic results
 * @returns {Promise} - Promise that resolves when PDF is generated
 */
export const generatePdfReport = async (diagnosticResults) => {
  if (!diagnosticResults || diagnosticResults.length === 0) {
    console.error('No diagnostic results to generate PDF');
    return;
  }

  const pdf = new jsPDF('p', 'mm', 'a4');
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const margin = 15;
  const contentWidth = pageWidth - (margin * 2);
  
  pdf.setFont('helvetica');
  
  pdf.setFillColor(59, 130, 246); // Primary color from GlobalStyles.css
  pdf.rect(0, 0, pageWidth, 30, 'F');
  pdf.setTextColor(255, 255, 255);
  pdf.setFontSize(20);
  pdf.text('2ndOpinionMD.ai', margin, 15);
  pdf.setFontSize(12);
  pdf.text('AI-powered second opinions for autoimmune disease diagnosis', margin, 23);
  
  pdf.setTextColor(0, 0, 0);
  
  pdf.setFontSize(18);
  pdf.text('Diagnostic Report', margin, 40);
  
  const currentDate = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
  pdf.setFontSize(10);
  pdf.text(`Generated on: ${currentDate}`, margin, 48);
  
  let yPosition = 55;
  
  pdf.setFontSize(14);
  pdf.text('Potential Diagnoses', margin, yPosition);
  yPosition += 8;
  
  diagnosticResults.forEach((diagnosis, index) => {
    if (yPosition > pageHeight - 50) {
      pdf.addPage();
      yPosition = 20;
    }
    
    pdf.setFontSize(12);
    pdf.setFont('helvetica', 'bold');
    pdf.text(`${index + 1}. ${diagnosis.name}`, margin, yPosition);
    
    const confidenceColor = getConfidenceColor(diagnosis.confidence);
    pdf.setTextColor(confidenceColor.r, confidenceColor.g, confidenceColor.b);
    pdf.text(`${diagnosis.confidence}% confidence`, pageWidth - margin - 40, yPosition);
    pdf.setTextColor(0, 0, 0);
    
    yPosition += 6;
    
    if (diagnosis.staxLevel || diagnosis.zone) {
      pdf.setFontSize(9);
      pdf.setFont('helvetica', 'italic');
      
      let terrainText = '';
      if (diagnosis.staxLevel) {
        terrainText += `STAX Level: ${diagnosis.staxLevel}`;
      }
      
      if (diagnosis.zone) {
        terrainText += terrainText ? ' | ' : '';
        terrainText += `Zone: ${diagnosis.zone}`;
      }
      
      pdf.text(terrainText, margin, yPosition);
      yPosition += 5;
    }
    
    if (diagnosis.tags && diagnosis.tags.length > 0) {
      pdf.setFontSize(9);
      pdf.setFont('helvetica', 'italic');
      pdf.text(`Tags: ${diagnosis.tags.join(', ')}`, margin, yPosition);
      yPosition += 5;
    }
    
    pdf.setFont('helvetica', 'normal');
    pdf.setFontSize(10);
    pdf.text('Common Symptoms:', margin, yPosition);
    yPosition += 5;
    
    diagnosis.symptoms.forEach(symptom => {
      pdf.text(`• ${formatSymptomName(symptom)}`, margin + 5, yPosition);
      yPosition += 5;
    });
    
    if (diagnosis.redFlags && diagnosis.redFlags.length > 0) {
      if (yPosition > pageHeight - 40) {
        pdf.addPage();
        yPosition = 20;
      }
      
      pdf.setTextColor(220, 53, 69); // Red color for red flags
      pdf.text('Red Flags:', margin, yPosition);
      yPosition += 5;
      
      diagnosis.redFlags.forEach(flag => {
        pdf.text(`• ${flag}`, margin + 5, yPosition);
        yPosition += 5;
      });
      
      pdf.setTextColor(0, 0, 0);
    }
    
    if (diagnosis.labSuggestions && diagnosis.labSuggestions.length > 0) {
      if (yPosition > pageHeight - 40) {
        pdf.addPage();
        yPosition = 20;
      }
      
      pdf.setTextColor(59, 130, 246); // Primary color for lab suggestions
      pdf.text('Suggested Tests:', margin, yPosition);
      yPosition += 5;
      
      diagnosis.labSuggestions.forEach(test => {
        pdf.text(`• ${test}`, margin + 5, yPosition);
        yPosition += 5;
      });
      
      pdf.setTextColor(0, 0, 0);
    }
    
    yPosition += 8;
  });
  
  if (yPosition > pageHeight - 60) {
    pdf.addPage();
    yPosition = 20;
  }
  
  pdf.setDrawColor(200, 200, 200);
  pdf.line(margin, yPosition, pageWidth - margin, yPosition);
  yPosition += 10;
  
  pdf.setFontSize(12);
  pdf.setFont('helvetica', 'bold');
  pdf.text('Important Disclaimer', margin, yPosition);
  yPosition += 6;
  
  pdf.setFont('helvetica', 'normal');
  pdf.setFontSize(9);
  const disclaimerText = 'This report is for informational purposes only and is not a medical diagnosis. ' +
    'This tool is designed to help you track and journal your symptoms to share with your healthcare provider. ' +
    'Please consult with a healthcare professional for proper evaluation and diagnosis. ' +
    'The confidence percentages are based on symptom matching and are not clinical assessments. ' +
    '2ndOpinionMD.ai provides this information as a tool to assist in discussions with healthcare providers.';
  
  const splitDisclaimer = pdf.splitTextToSize(disclaimerText, contentWidth);
  pdf.text(splitDisclaimer, margin, yPosition);
  
  const footerText = '© 2023 2ndOpinionMD.ai - All Rights Reserved';
  pdf.setFontSize(8);
  pdf.text(footerText, pageWidth / 2, pageHeight - 10, { align: 'center' });
  
  return pdf;
};

const formatSymptomName = (symptom) => {
  return symptom
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

const getConfidenceColor = (confidence) => {
  if (confidence >= 80) {
    return { r: 40, g: 167, b: 69 }; // Green
  } else if (confidence >= 60) {
    return { r: 255, g: 193, b: 7 }; // Yellow
  } else {
    return { r: 220, g: 53, b: 69 }; // Red
  }
};

export const downloadPdfReport = async (diagnosticResults, filename = 'medical-report.pdf') => {
  try {
    const pdf = await generatePdfReport(diagnosticResults);
    if (pdf) {
      pdf.save(filename);
    }
  } catch (error) {
    console.error('Error generating PDF:', error);
  }
};

/**
 * Generates a PDF timeline report from journal entries and initial diagnosis
 * @param {Object} timelineData - Object containing initialDiagnosis and journalEntries
 * @returns {Promise} - Promise that resolves when PDF is generated
 */
export const generateTimelinePdf = async (timelineData) => {
  if (!timelineData || !timelineData.initialDiagnosis || !timelineData.journalEntries) {
    console.error('No timeline data to generate PDF');
    return;
  }

  const pdf = new jsPDF('p', 'mm', 'a4');
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const margin = 15;
  const contentWidth = pageWidth - (margin * 2);
  
  pdf.setFont('helvetica');
  
  pdf.setFillColor(59, 130, 246); // Primary color
  pdf.rect(0, 0, pageWidth, 30, 'F');
  pdf.setTextColor(255, 255, 255);
  pdf.setFontSize(20);
  pdf.text('2ndOpinionMD.ai', margin, 15);
  pdf.setFontSize(12);
  pdf.text('Diagnosis Timeline Report', margin, 23);
  
  pdf.setTextColor(0, 0, 0);
  
  pdf.setFontSize(18);
  pdf.text('Diagnosis History Timeline', margin, 40);
  
  const currentDate = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
  pdf.setFontSize(10);
  pdf.text(`Generated on: ${currentDate}`, margin, 48);
  
  let yPosition = 55;
  
  pdf.setFontSize(14);
  pdf.setFont('helvetica', 'bold');
  pdf.text('Initial Assessment', margin, yPosition);
  yPosition += 6;
  
  const initialDate = new Date(timelineData.initialDiagnosis.date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
  pdf.setFontSize(10);
  pdf.setFont('helvetica', 'italic');
  pdf.text(`Date: ${initialDate}`, margin, yPosition);
  yPosition += 8;
  
  pdf.setFont('helvetica', 'bold');
  pdf.text('Initial Diagnoses:', margin, yPosition);
  yPosition += 6;
  
  if (timelineData.initialDiagnosis.diagnoses && timelineData.initialDiagnosis.diagnoses.length > 0) {
    timelineData.initialDiagnosis.diagnoses.forEach((diagnosis, index) => {
      if (yPosition > pageHeight - 50) {
        pdf.addPage();
        yPosition = 20;
      }
      
      pdf.setFontSize(10);
      pdf.setFont('helvetica', 'normal');
      pdf.text(`${index + 1}. ${diagnosis.name} - Confidence: ${diagnosis.confidence}%`, margin + 5, yPosition);
      yPosition += 5;
      
      if (diagnosis.staxLevel || diagnosis.zone) {
        pdf.setFontSize(8);
        pdf.setFont('helvetica', 'italic');
        
        let terrainText = '';
        if (diagnosis.staxLevel) {
          terrainText += `STAX Level: ${diagnosis.staxLevel}`;
        }
        
        if (diagnosis.zone) {
          terrainText += terrainText ? ' | ' : '';
          terrainText += `Zone: ${diagnosis.zone}`;
        }
        
        pdf.text(terrainText, margin + 10, yPosition);
        yPosition += 4;
      }
    });
  } else {
    pdf.setFontSize(10);
    pdf.setFont('helvetica', 'italic');
    pdf.text('No initial diagnoses recorded.', margin + 5, yPosition);
    yPosition += 5;
  }
  
  yPosition += 5;
  
  if (timelineData.journalEntries && timelineData.journalEntries.length > 0) {
    pdf.setFontSize(14);
    pdf.setFont('helvetica', 'bold');
    pdf.text('Journal Entry Timeline', margin, yPosition);
    yPosition += 8;
    
    timelineData.journalEntries.forEach((entry, entryIndex) => {
      if (yPosition > pageHeight - 60) {
        pdf.addPage();
        yPosition = 20;
      }
      
      const entryDate = new Date(entry.date).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
      
      pdf.setFillColor(240, 240, 240);
      pdf.rect(margin, yPosition - 4, contentWidth, 6, 'F');
      pdf.setFontSize(11);
      pdf.setFont('helvetica', 'bold');
      pdf.text(`Journal Entry: ${entryDate}`, margin + 2, yPosition);
      yPosition += 8;
      
      if (entry.notes) {
        pdf.setFontSize(9);
        pdf.setFont('helvetica', 'normal');
        const splitNotes = pdf.splitTextToSize(entry.notes, contentWidth - 10);
        pdf.text(splitNotes, margin + 5, yPosition);
        yPosition += splitNotes.length * 4 + 4;
      }
      
      if (entry.symptoms && entry.symptoms.length > 0) {
        pdf.setFontSize(9);
        pdf.setFont('helvetica', 'bold');
        pdf.text('Symptoms:', margin + 5, yPosition);
        yPosition += 4;
        
        pdf.setFont('helvetica', 'normal');
        entry.symptoms.forEach(symptom => {
          pdf.text(`• ${symptom.symptom} (Severity: ${symptom.severity}/10)`, margin + 10, yPosition);
          yPosition += 4;
        });
        yPosition += 2;
      }
      
      if (entry.ai_analysis) {
        const analysis = entry.ai_analysis;
        
        if (yPosition > pageHeight - 60) {
          pdf.addPage();
          yPosition = 20;
        }
        
        pdf.setFontSize(9);
        pdf.setFont('helvetica', 'bold');
        pdf.text('AI Analysis:', margin + 5, yPosition);
        yPosition += 4;
        
        if (analysis.symptoms && analysis.symptoms.length > 0) {
          pdf.setFont('helvetica', 'italic');
          pdf.text('Identified Symptoms:', margin + 10, yPosition);
          yPosition += 4;
          
          pdf.setFont('helvetica', 'normal');
          analysis.symptoms.forEach(symptom => {
            pdf.text(`• ${symptom}`, margin + 15, yPosition);
            yPosition += 4;
          });
        }
        
        if (analysis.environmental_factors && analysis.environmental_factors.length > 0) {
          if (yPosition > pageHeight - 40) {
            pdf.addPage();
            yPosition = 20;
          }
          
          pdf.setFont('helvetica', 'italic');
          pdf.text('Environmental Factors:', margin + 10, yPosition);
          yPosition += 4;
          
          pdf.setFont('helvetica', 'normal');
          analysis.environmental_factors.forEach(factor => {
            pdf.text(`• ${factor}`, margin + 15, yPosition);
            yPosition += 4;
          });
        }
        
        if (analysis.life_stressors && analysis.life_stressors.length > 0) {
          if (yPosition > pageHeight - 40) {
            pdf.addPage();
            yPosition = 20;
          }
          
          pdf.setFont('helvetica', 'italic');
          pdf.text('Life Stressors:', margin + 10, yPosition);
          yPosition += 4;
          
          pdf.setFont('helvetica', 'normal');
          analysis.life_stressors.forEach(stressor => {
            pdf.text(`• ${stressor}`, margin + 15, yPosition);
            yPosition += 4;
          });
        }
        
        if (analysis.diagnoses && analysis.diagnoses.length > 0) {
          if (yPosition > pageHeight - 60) {
            pdf.addPage();
            yPosition = 20;
          }
          
          pdf.setFont('helvetica', 'bold');
          pdf.text('Updated Diagnoses:', margin + 10, yPosition);
          yPosition += 4;
          
          analysis.diagnoses.forEach(diagnosis => {
            pdf.setFont('helvetica', 'normal');
            
            let statusText = '';
            if (diagnosis.status === 'new') {
              statusText = ' (NEW)';
              pdf.setTextColor(0, 128, 0); // Green for new
            } else if (diagnosis.status === 'eliminated') {
              statusText = ' (ELIMINATED)';
              pdf.setTextColor(192, 0, 0); // Red for eliminated
            } else {
              pdf.setTextColor(0, 0, 0); // Black for confirmed
            }
            
            pdf.text(`• ${diagnosis.name}${statusText} - Confidence: ${diagnosis.confidence}%`, margin + 15, yPosition);
            pdf.setTextColor(0, 0, 0); // Reset text color
            yPosition += 4;
            
            if (diagnosis.staxLevel || diagnosis.zone) {
              pdf.setFontSize(8);
              pdf.setFont('helvetica', 'italic');
              
              let terrainText = '';
              if (diagnosis.staxLevel) {
                terrainText += `STAX Level: ${diagnosis.staxLevel}`;
              }
              
              if (diagnosis.zone) {
                terrainText += terrainText ? ' | ' : '';
                terrainText += `Zone: ${diagnosis.zone}`;
              }
              
              pdf.text(terrainText, margin + 20, yPosition);
              yPosition += 4;
            }
          });
        }
      }
      
      yPosition += 10;
    });
  } else {
    pdf.setFontSize(10);
    pdf.setFont('helvetica', 'italic');
    pdf.text('No journal entries recorded.', margin + 5, yPosition);
    yPosition += 5;
  }
  
  if (yPosition > pageHeight - 60) {
    pdf.addPage();
    yPosition = 20;
  }
  
  pdf.setDrawColor(200, 200, 200);
  pdf.line(margin, yPosition, pageWidth - margin, yPosition);
  yPosition += 10;
  
  pdf.setFontSize(12);
  pdf.setFont('helvetica', 'bold');
  pdf.text('Important Disclaimer', margin, yPosition);
  yPosition += 6;
  
  pdf.setFont('helvetica', 'normal');
  pdf.setFontSize(9);
  const disclaimerText = 'This timeline report is for informational purposes only and is not a medical diagnosis. ' +
    'This tool helps you track symptom patterns over time to share with your healthcare provider. ' +
    'Please consult with a healthcare professional for proper evaluation and diagnosis. ' +
    'The confidence percentages are based on symptom matching and are not clinical assessments. ' +
    '2ndOpinionMD.ai provides this information as a tool to assist in discussions with healthcare providers.';
  
  const splitDisclaimer = pdf.splitTextToSize(disclaimerText, contentWidth);
  pdf.text(splitDisclaimer, margin, yPosition);
  
  const footerText = '© 2023 2ndOpinionMD.ai - All Rights Reserved';
  pdf.setFontSize(8);
  pdf.text(footerText, pageWidth / 2, pageHeight - 10, { align: 'center' });
  
  return pdf;
};

/**
 * Downloads a PDF timeline report
 * @param {Object} timelineData - Object containing initialDiagnosis and journalEntries
 * @param {string} filename - Name of the PDF file to download
 */
export const downloadTimelinePdf = async (timelineData, filename = 'diagnosis-timeline.pdf') => {
  try {
    const pdf = await generateTimelinePdf(timelineData);
    if (pdf) {
      pdf.save(filename);
    }
  } catch (error) {
    console.error('Error generating timeline PDF:', error);
  }
};
