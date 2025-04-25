const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const dotenv = require('dotenv');
const jwt = require('jsonwebtoken');
const fs = require('fs');
const path = require('path');
const mongoose = require('mongoose');
const { generateDiagnosticResults } = require('./utils/diagnosticUtils');
const { generatePdfReport } = require('./utils/pdfGenerator');
const { authenticateToken, generateToken } = require('./middleware/auth');
const connectDB = require('./config/db');
const User = require('./models/UserSchema');
const Report = require('./models/ReportSchema');

dotenv.config();

connectDB();

const app = express();
const PORT = process.env.PORT || 3000;

const pdfDir = process.env.PDF_OUTPUT_DIR || './pdf_reports';
if (!fs.existsSync(pdfDir)) {
  fs.mkdirSync(pdfDir, { recursive: true });
}

app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

app.get('/', (req, res) => {
  res.json({
    message: '2ndOpinionMD.ai API is running',
    version: '1.0.0',
    endpoints: [
      { path: '/api/auth/register', method: 'POST', description: 'Register a new user' },
      { path: '/api/auth/login', method: 'POST', description: 'Login and get authentication token' },
      { path: '/api/user/profile', method: 'GET', description: 'Get user profile (requires authentication)' },
      { path: '/api/diagnose', method: 'POST', description: 'Submit symptom data for diagnosis (requires authentication)' },
      { path: '/api/generate-pdf', method: 'POST', description: 'Generate PDF report from diagnostic results (requires authentication)' },
      { path: '/api/reports', method: 'GET', description: 'Get user reports (requires authentication)' },
      { path: '/api/fields/symptoms', method: 'GET', description: 'Get available symptoms (requires authentication)' },
      { path: '/api/fields/prior-diagnoses', method: 'GET', description: 'Get available prior diagnoses (requires authentication)' },
      { path: '/api/fields/sex-options', method: 'GET', description: 'Get available sex options (requires authentication)' }
    ]
  });
});

app.post('/api/auth/register', async (req, res) => {
  try {
    const { email, password, firstName, lastName } = req.body;
    
    if (!email || !password) {
      return res.status(400).json({ 
        error: 'Missing required fields',
        requiredFields: ['email', 'password']
      });
    }
    
    const existingUser = await User.findOne({ email });
    if (existingUser) {
      return res.status(409).json({ 
        error: 'User already exists',
        message: 'A user with this email already exists'
      });
    }
    
    const user = new User({
      email,
      password, // Password will be hashed by the pre-save hook
      firstName,
      lastName,
      role: 'patient'
    });
    
    await user.save();
    
    const token = generateToken(user);
    
    res.status(201).json({
      success: true,
      message: 'User registered successfully',
      token,
      user: {
        id: user._id,
        email: user.email,
        firstName: user.firstName,
        lastName: user.lastName,
        role: user.role
      }
    });
  } catch (error) {
    console.error('Error registering user:', error);
    res.status(500).json({ 
      error: 'Internal server error',
      message: error.message
    });
  }
});

app.post('/api/auth/login', async (req, res) => {
  try {
    const { email, password } = req.body;
    
    if (!email || !password) {
      return res.status(400).json({ 
        error: 'Missing required fields',
        requiredFields: ['email', 'password']
      });
    }
    
    const user = await User.findOne({ email });
    if (!user) {
      return res.status(401).json({ 
        error: 'Authentication failed',
        message: 'Invalid email or password'
      });
    }
    
    const isPasswordValid = await user.comparePassword(password);
    if (!isPasswordValid) {
      return res.status(401).json({ 
        error: 'Authentication failed',
        message: 'Invalid email or password'
      });
    }
    
    const token = generateToken(user);
    
    res.json({
      success: true,
      message: 'Login successful',
      token,
      user: {
        id: user._id,
        email: user.email,
        firstName: user.firstName,
        lastName: user.lastName,
        role: user.role
      }
    });
  } catch (error) {
    console.error('Error logging in:', error);
    res.status(500).json({ 
      error: 'Internal server error',
      message: error.message
    });
  }
});

app.get('/api/user/profile', authenticateToken, async (req, res) => {
  try {
    const user = await User.findById(req.user.id);
    
    if (!user) {
      return res.status(404).json({ 
        error: 'User not found',
        message: 'User does not exist'
      });
    }
    
    res.json({
      success: true,
      user: {
        id: user._id,
        email: user.email,
        firstName: user.firstName,
        lastName: user.lastName,
        role: user.role
      }
    });
  } catch (error) {
    console.error('Error getting user profile:', error);
    res.status(500).json({ 
      error: 'Internal server error',
      message: error.message
    });
  }
});

app.post('/api/diagnose', authenticateToken, async (req, res) => {
  try {
    const formData = req.body;
    
    if (!formData.age || !formData.sex || !formData.symptoms || !formData.durationMonths) {
      return res.status(400).json({ 
        error: 'Missing required fields',
        requiredFields: ['age', 'sex', 'symptoms', 'durationMonths']
      });
    }
    
    const formattedData = {
      user_id: req.user.id.toString(),
      input_type: "symptom_query",
      input_data: {
        age: parseInt(formData.age),
        sex: formData.sex,
        symptoms: Array.isArray(formData.symptoms) ? formData.symptoms : [formData.symptoms],
        duration_months: parseInt(formData.durationMonths || 0),
        prior_diagnoses: formData.priorDiagnoses || []
      },
      context_flags: {
        hipaa_mode: true,
        model_version: process.env.MODEL_VERSION || "gpt-4-turbo",
        return_format: "json"
      }
    };
    
    const diagnosticResults = generateDiagnosticResults(formattedData);
    
    const report = new Report({
      userId: req.user.id,
      inputData: formattedData.input_data,
      diagnosticResults
    });
    
    await report.save();
    
    res.json({
      success: true,
      reportId: report._id,
      diagnosticResults
    });
  } catch (error) {
    console.error('Error processing diagnosis:', error);
    res.status(500).json({ 
      error: 'Internal server error',
      message: error.message
    });
  }
});

app.post('/api/generate-pdf', authenticateToken, async (req, res) => {
  try {
    const { reportId, diagnosticResults } = req.body;
    
    if (!reportId && (!diagnosticResults || !Array.isArray(diagnosticResults) || diagnosticResults.length === 0)) {
      return res.status(400).json({ 
        error: 'Invalid input',
        message: 'Either reportId or diagnosticResults must be provided'
      });
    }
    
    let results = diagnosticResults;
    let report = null;
    
    if (reportId) {
      report = await Report.findById(reportId);
      
      if (!report) {
        return res.status(404).json({ 
          error: 'Report not found',
          message: 'Report does not exist'
        });
      }
      
      if (report.userId.toString() !== req.user.id) {
        return res.status(403).json({ 
          error: 'Forbidden',
          message: 'You do not have permission to access this report'
        });
      }
      
      results = report.diagnosticResults;
    }
    
    const pdf = await generatePdfReport(results);
    
    if (!pdf) {
      return res.status(500).json({ 
        error: 'PDF generation failed'
      });
    }
    
    const filename = `report_${reportId || Date.now()}.pdf`;
    const pdfPath = path.join(pdfDir, filename);
    
    const buffer = Buffer.from(pdf.output('arraybuffer'));
    fs.writeFileSync(pdfPath, buffer);
    
    const pdfData = pdf.output('datauristring');
    
    if (reportId && report) {
      await Report.findByIdAndUpdate(reportId, {
        pdfUrl: filename
      });
    }
    
    res.json({
      success: true,
      pdfData,
      filename
    });
  } catch (error) {
    console.error('Error generating PDF:', error);
    res.status(500).json({ 
      error: 'Internal server error',
      message: error.message
    });
  }
});

app.get('/api/reports', authenticateToken, async (req, res) => {
  try {
    const reports = await Report.find({ userId: req.user.id });
    
    res.json({
      success: true,
      reports
    });
  } catch (error) {
    console.error('Error getting reports:', error);
    res.status(500).json({ 
      error: 'Internal server error',
      message: error.message
    });
  }
});

app.get('/api/fields/symptoms', authenticateToken, (req, res) => {
  try {
    const { SYMPTOMS } = require('./utils/constants');
    res.json({
      success: true,
      symptoms: SYMPTOMS
    });
  } catch (error) {
    console.error('Error getting symptoms:', error);
    res.status(500).json({ 
      error: 'Internal server error',
      message: error.message
    });
  }
});

app.get('/api/fields/prior-diagnoses', authenticateToken, (req, res) => {
  try {
    const { PRIOR_DIAGNOSES } = require('./utils/constants');
    res.json({
      success: true,
      priorDiagnoses: PRIOR_DIAGNOSES
    });
  } catch (error) {
    console.error('Error getting prior diagnoses:', error);
    res.status(500).json({ 
      error: 'Internal server error',
      message: error.message
    });
  }
});

app.get('/api/fields/sex-options', authenticateToken, (req, res) => {
  try {
    const { SEX_OPTIONS } = require('./utils/constants');
    res.json({
      success: true,
      sexOptions: SEX_OPTIONS
    });
  } catch (error) {
    console.error('Error getting sex options:', error);
    res.status(500).json({ 
      error: 'Internal server error',
      message: error.message
    });
  }
});

app.listen(PORT, () => {
  console.log(`2ndOpinionMD.ai API server running on port ${PORT}`);
});

module.exports = app; // For testing
