# 2ndOpinionMD.ai – MVP Development Repo

This is the official MVP codebase for **2ndOpinionMD.ai**, a HIPAA-forward, AI-powered platform providing second-opinion reports for autoimmune disease diagnosis support.

---

## 🚀 Project Description

2ndOpinionMD.ai empowers users to receive a personalized, AI-generated second opinion for hard-to-diagnose autoimmune conditions. Using symptom input + a proprietary misdiagnosis database, the platform generates a PDF-ready, doctor-facing report with:

- Top likely conditions (e.g., Lupus, MS, RA, etc.)
- Red-flag symptom patterns
- Suggested labs/imaging
- Scientific references
- Disclaimer & next-step recommendations

The platform now includes user authentication and a journaling feature to track symptoms, environmental factors, and health metrics over time, providing valuable context for diagnosis.

---

## 🛠️ Environment Setup

### 🧬 Required Versions
- **Python**: `v3.10` or higher for the backend server
- **PostgreSQL**: Running instance for application data

### 📦 Installation
After cloning this repo, install backend dependencies:

```bash
cd server
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 💻 Running the App (Local Dev)
To start the backend server:

```bash
cd server
source venv/bin/activate  # On Windows: venv\Scripts\activate
python -m uvicorn api.app_postgres:app --host 0.0.0.0 --port 8000 --reload
```

API will be available at:
👉 http://localhost:8000

### 🔑 Environment Configuration
Create a `.env` file in the server directory with required API keys and database configuration.

### 🔧 Dev Testing - Journal API

Manual testing commands for journal endpoints:

```bash
# 1) Login and get token
export TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=you@example.com&password=yourpassword' | jq -r .access_token)

# 2) List entries (both paths should return 200, no 307 redirects)
curl -i -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/journal
curl -i -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/journal/

# 3) Create entry (should return 201)
curl -i -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"symptoms":[{"symptom":"headache","severity":5}],"notes":"Test entry"}' \
  http://127.0.0.1:8000/api/journal

# 4) Read entry (replace {id} with actual entry ID)
curl -i -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/journal/{id}

# 5) Delete entry (replace {id} with actual entry ID)
curl -i -X DELETE -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/journal/{id}
```

**Expected Results:**
- No 307 redirects on any endpoint
- All endpoints return 401 without Bearer token
- POST returns 201 Created
- No `/api/journal/journal` routes in logs

## 📋 Features

### 🔒 Authentication
- User registration and login
- JWT-based authentication
- Secure password hashing
- Protected routes for authenticated users

### 📝 Journaling
- Track symptoms with severity ratings and dates
- Record environmental factors and stressors
- Monitor diet and substance use
- Document sleep quality and other health metrics
- AI-powered analysis of journal entries
- Follow-up questions generated based on entries
- Historical context maintained between entries

### 🧠 AI Diagnosis
- Symptom-based condition matching
- Red flag identification
- Lab and imaging suggestions
- Scientific references

## 🧾 File Structure

```
2ndOpinionMD-MVP/
 ┣ 📂server
 ┃ ┣ 📂api
 ┃ ┃ ┣ app_postgres.py
 ┃ ┃ ┣ auth.py
 ┃ ┃ ┗ eoh_gap_retrieval.py
 ┃ ┣ 📂eoh
 ┃ ┃ ┗ module_49c_policy.py
 ┃ ┗ requirements.txt
 ┣ 📂database
 ┃ ┣ 📂schemas
 ┃ ┗ 📂sql
 ┗ 📄 README.md
```

## 🔐 Security Features

### Rate Limiting

The API implements rate limiting to protect against brute force attacks and abuse:

- Authentication endpoints: 5 requests per minute per IP address
- General API endpoints: 60 requests per minute per IP address
- **Diagnose endpoint (`/api/diagnose`)**: 10 requests per minute per IP address (public access)

When rate limits are exceeded, the API returns a 429 Too Many Requests response with a Retry-After header indicating when the client should try again.

### Public Endpoints

The `/api/diagnose` endpoint is publicly accessible without authentication to allow guest users to submit symptoms for analysis. This endpoint includes:

- Enhanced payload validation (max 50 symptoms, 500 characters each)
- Strict rate limiting (10 requests/minute per IP)
- Request duration logging and structured error responses
- Deprecated alias at `/api/diagnosis` (logs deprecation warnings)

### Email Verification

User registration requires email verification:

- When a user registers, a verification email is sent to their email address
- The user must click the verification link to activate their account
- Unverified users cannot log in to the application
- Verification tokens expire after 30 minutes
- Users can request a new verification email if needed

### Email Allow-List

The system supports an email allow-list for non-2ndopinionmd.ai email addresses:

- Emails in the allow-list can register even if they don't have a 2ndopinionmd.ai domain
- The allow-list is stored in a plain text file at `/server/allowed_emails.txt`
- Each email should be on a separate line
- Lines starting with `#` are treated as comments and ignored
- Email matching is case-insensitive

### Security Middleware

The API implements security middleware to block suspicious requests:

- Blocks access to sensitive files and paths (/.env, /.git, etc.)
- Returns 403 Forbidden for blocked requests
- Logs blocked requests with source IP address
- Protects against common scanning and exploitation attempts

## 🧠 Notes for Future Devs
- Backend API provides clinical reasoning and diagnostic support.
- No PHI is stored without explicit consent.
- System includes modular Ethos-of-Health (EoH) reasoning framework.
- PostgreSQL is used for application data storage.

## 📄 Future To-Do (Post-MVP)
- Add formal test suite
- Implement backend report PDF generator
- Add email delivery (via nate@2ndopinionmd.ai)
- Migrate to secure API architecture
- HIPAA-compliant data collection (opt-in)
- ~~Symptom journal tracking (Phase 2)~~ ✅ Implemented
- ~~OpenAI integration for symptom and journal analysis~~ ✅ Implemented
- Payment gateway for Basic ($19.99) and Advanced ($49.99) reports
- Tiered journaling capabilities based on subscription plans

## 💬 Contact
For access, support, or onboarding:

📧 nate@2ndopinionmd.ai
🔗 2ndOpinionMD.ai (coming soon)

Built with ❤️ to shorten the diagnostic journey for millions suffering from misdiagnosed autoimmune diseases.


