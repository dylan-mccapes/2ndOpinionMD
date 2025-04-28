const mongoose = require('mongoose');

/**
 * Report schema for MongoDB
 */
const ReportSchema = new mongoose.Schema({
  userId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  inputData: {
    age: {
      type: Number,
      required: true
    },
    sex: {
      type: String,
      required: true,
      enum: ['male', 'female', 'other']
    },
    symptoms: {
      type: [String],
      required: true
    },
    duration_months: {
      type: Number,
      default: 0
    },
    prior_diagnoses: {
      type: [String],
      default: []
    }
  },
  diagnosticResults: [{
    name: {
      type: String,
      required: true
    },
    confidence: {
      type: Number,
      required: true
    },
    symptoms: {
      type: [String],
      default: []
    },
    redFlags: {
      type: [String],
      default: []
    },
    labSuggestions: {
      type: [String],
      default: []
    }
  }],
  pdfUrl: {
    type: String,
    default: null
  }
}, {
  timestamps: true
});

module.exports = mongoose.model('Report', ReportSchema);
