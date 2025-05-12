/**
 * Report model for in-memory storage with ethos of health model integration
 * In a production environment, this would be replaced with a database model
 */
class Report {
  constructor() {
    this.reports = [];
    this.nextId = 1;
  }

  /**
   * Create a new report
   * @param {Object} reportData - Report data
   * @returns {Object} - Created report
   */
  create(reportData) {
    const diagnosticResults = reportData.diagnosticResults?.map(result => ({
      ...result,
      staxLevel: result.staxLevel || 1,
      zone: result.zone || 1,
      tags: result.tags || [],
      status: result.status || 'initial'
    })) || [];

    const report = {
      id: this.nextId++,
      userId: reportData.userId,
      inputData: reportData.inputData,
      diagnosticResults: diagnosticResults,
      journalEntries: reportData.journalEntries || [],
      pdfUrl: reportData.pdfUrl || null,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    
    this.reports.push(report);
    return report;
  }

  /**
   * Find a report by ID
   * @param {number} id - Report ID
   * @returns {Object|null} - Report object or null if not found
   */
  findById(id) {
    return this.reports.find(report => report.id === id) || null;
  }

  /**
   * Find reports by user ID
   * @param {number} userId - User ID
   * @returns {Array} - Array of reports
   */
  findByUserId(userId) {
    return this.reports.filter(report => report.userId === userId);
  }

  /**
   * Update a report
   * @param {number} id - Report ID
   * @param {Object} reportData - Report data to update
   * @returns {Object|null} - Updated report or null if not found
   */
  update(id, reportData) {
    const index = this.reports.findIndex(report => report.id === id);
    
    if (index === -1) {
      return null;
    }
    
    const updatedReport = {
      ...this.reports[index],
      ...reportData,
      updatedAt: new Date()
    };
    
    this.reports[index] = updatedReport;
    return updatedReport;
  }

  /**
   * Add a journal entry to a report
   * @param {number} id - Report ID
   * @param {Object} journalEntry - Journal entry data
   * @returns {Object|null} - Updated report or null if not found
   */
  addJournalEntry(id, journalEntry) {
    const report = this.findById(id);
    if (!report) return null;

    const newEntry = {
      entryDate: journalEntry.entryDate || new Date(),
      content: journalEntry.content,
      analysis: journalEntry.analysis || {
        symptoms: [],
        environmentalFactors: [],
        lifeStressors: []
      },
      journalingRecommendation: journalEntry.journalingRecommendation || {
        promptType: 'Clinical',
        suggestedPrompt: ''
      }
    };

    if (!report.journalEntries) {
      report.journalEntries = [];
    }

    report.journalEntries.push(newEntry);
    report.updatedAt = new Date();

    return report;
  }

  /**
   * Update diagnoses based on journal analysis
   * @param {number} id - Report ID
   * @param {Array} diagnoses - Array of diagnoses from journal analysis
   * @returns {Object|null} - Updated report or null if not found
   */
  updateDiagnoses(id, diagnoses) {
    const report = this.findById(id);
    if (!report) return null;

    const existingDiagnosesMap = {};
    report.diagnosticResults.forEach(diagnosis => {
      existingDiagnosesMap[diagnosis.name] = diagnosis;
    });

    const updatedDiagnosticResults = [];

    diagnoses.forEach(diagnosis => {
      if (diagnosis.status === 'eliminated') {
        return;
      } else if (diagnosis.status === 'new') {
        updatedDiagnosticResults.push(diagnosis);
      } else if (existingDiagnosesMap[diagnosis.name]) {
        const existingDiagnosis = existingDiagnosesMap[diagnosis.name];
        updatedDiagnosticResults.push({
          ...existingDiagnosis,
          confidence: diagnosis.confidence,
          staxLevel: diagnosis.staxLevel,
          zone: diagnosis.zone,
          tags: diagnosis.tags,
          status: diagnosis.status
        });
      }
    });

    report.diagnosticResults.forEach(diagnosis => {
      const diagnosisInUpdate = updatedDiagnosticResults.find(d => d.name === diagnosis.name);
      if (!diagnosisInUpdate) {
        updatedDiagnosticResults.push(diagnosis);
      }
    });

    report.diagnosticResults = updatedDiagnosticResults;
    report.updatedAt = new Date();

    return report;
  }

  /**
   * Delete a report
   * @param {number} id - Report ID
   * @returns {boolean} - True if report was deleted
   */
  delete(id) {
    const index = this.reports.findIndex(report => report.id === id);
    
    if (index === -1) {
      return false;
    }
    
    this.reports.splice(index, 1);
    return true;
  }
}

module.exports = new Report();
