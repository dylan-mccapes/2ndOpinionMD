# 2ndOpinionMD Express Server

Express server for 2ndOpinionMD.ai - AI-powered second opinions for autoimmune disease diagnosis with MongoDB integration.

## Features

- HIPAA-compliant authentication
- Server-side PDF report generation
- API endpoints for all form fields
- MongoDB integration for data persistence

## Prerequisites

- Node.js v18+
- MongoDB v6.0+

## Installation

1. Clone the repository
2. Install dependencies

```bash
cd 2ndopinionmd-express-server
npm install
```

3. Configure environment variables in `.env` file

```
PORT=3000
JWT_SECRET=your_jwt_secret_key_for_hipaa_compliance
MONGO_URI=mongodb://localhost:27017/2ndopinionmd
PDF_OUTPUT_DIR=./pdf_reports
CORS_ORIGIN=http://localhost:3000
MODEL_VERSION=gpt-4-turbo
```

## Running the Server

### Development

```bash
npm run dev
```

### Production

```bash
npm start
```

## MongoDB Integration

This server uses MongoDB for data persistence. The following models are defined:

### User Schema

- email (String, required, unique)
- password (String, required, hashed)
- firstName (String)
- lastName (String)
- role (String, enum: ['patient', 'doctor', 'admin'])

### Report Schema

- userId (ObjectId, reference to User)
- inputData (Object)
  - age (Number)
  - sex (String)
  - symptoms (Array of Strings)
  - duration_months (Number)
  - prior_diagnoses (Array of Strings)
- diagnosticResults (Array of Objects)
  - name (String)
  - confidence (Number)
  - symptoms (Array of Strings)
  - redFlags (Array of Strings)
  - labSuggestions (Array of Strings)
- pdfUrl (String)

## API Endpoints

### Authentication

- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login and get authentication token
- `GET /api/user/profile` - Get user profile (requires authentication)

### Diagnosis

- `POST /api/diagnose` - Submit symptom data for diagnosis (requires authentication)
- `POST /api/generate-pdf` - Generate PDF report from diagnostic results (requires authentication)
- `GET /api/reports` - Get user reports (requires authentication)

### Form Fields

- `GET /api/fields/symptoms` - Get available symptoms (requires authentication)
- `GET /api/fields/prior-diagnoses` - Get available prior diagnoses (requires authentication)
- `GET /api/fields/sex-options` - Get available sex options (requires authentication)

## Testing

A comprehensive test plan is available in `test-plan.md`. To run automated tests:

```bash
chmod +x test.sh
./test.sh
```

This will test all API endpoints and MongoDB integration.

## HIPAA Compliance

This server implements several security features for HIPAA compliance:

1. JWT-based authentication with token expiration
2. Password hashing with bcrypt
3. Protected routes requiring valid tokens
4. MongoDB for secure data storage
5. HIPAA mode flag in diagnostic requests

## PDF Generation

The server generates PDF reports from diagnostic results using jsPDF. Reports include:

1. Potential diagnoses with confidence scores
2. Matching symptoms
3. Red flags
4. Lab test suggestions
5. Disclaimer and footer

## License

ISC
