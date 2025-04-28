/**
 * Report model for in-memory storage
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
    const report = {
      id: this.nextId++,
      userId: reportData.userId,
      inputData: reportData.inputData,
      diagnosticResults: reportData.diagnosticResults,
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
