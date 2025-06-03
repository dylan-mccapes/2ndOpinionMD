const mongoose = require('mongoose');

/**
 * Report schema for MongoDB with ethos of health model integration
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
    birthdate: {
      type: Date,
      required: false
    },
    sex: {
      type: String,
      required: true,
      enum: ['male', 'female', 'other']
    },
    height: {
      type: String,
      required: false
    },
    weight: {
      type: Number,
      required: false
    },
    race: {
      type: String,
      required: false
    },
    occupation: {
      type: String,
      required: false
    },
    symptoms: {
      type: [String],
      required: true
    },
    duration_months: {
      type: Number,
      default: 0
    },
    environmental_factors: {
      type: [String],
      default: []
    },
    life_stressors: {
      type: String,
      default: ""
    },
    prior_diagnoses: {
      type: [String],
      default: []
    },
    intake_timestamp: {
      type: Date,
      default: Date.now
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
    },
    staxLevel: {
      type: Number,
      min: 1,
      max: 4,
      default: 1
    },
    zone: {
      type: Number,
      min: 1,
      max: 5,
      default: 1
    },
    tags: {
      type: [String],
      default: []
    },
    status: {
      type: String,
      enum: ['confirmed', 'new', 'eliminated', 'initial'],
      default: 'initial'
    }
  }],
  journalEntries: [{
    entryDate: {
      type: Date,
      default: Date.now
    },
    content: {
      type: String,
      required: true
    },
    analysis: {
      symptoms: [String],
      environmentalFactors: [String],
      lifeStressors: [String]
    },
    journalingRecommendation: {
      promptType: {
        type: String,
        enum: ['Clinical', 'Somatic', 'Symbolic', 'Remission'],
        default: 'Clinical'
      },
      suggestedPrompt: String
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
