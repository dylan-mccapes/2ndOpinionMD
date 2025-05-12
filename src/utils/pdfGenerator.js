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
