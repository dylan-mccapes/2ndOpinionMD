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
- **Node.js**: `v18`
- **Yarn**: Installed and used for package management
- **Python**: `v3.10` or higher for the backend server
- **MongoDB**: Running instance for user data and journal entries

We recommend using [NVM](https://github.com/nvm-sh/nvm) to manage your Node versions.

To set the correct version:
```zsh
nvm use 18
```

You can also create a .nvmrc file in the root with:
```zsh
echo "18" > .nvmrc
```

### 📦 Installation
After cloning this repo, install dependencies:

**Frontend:**
```zsh
yarn install
```

**Backend:**
```zsh
cd server
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 💻 Running the App (Local Dev)
To start the development server:

**Frontend:**
```zsh
yarn dev
```

**Backend:**
```zsh
cd server
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn api.app:app --reload --port 3001
```

Then open your browser to:
👉 http://localhost:3000

### 🔑 Environment Configuration
Create a `.env` file in the root directory with the following variables:

```
# === API KEYS ===
OPENAI_API_KEY=your-openai-api-key-here
BASTION_API_KEY=your-bastion-api-key-here

# === MODEL ROUTING CONFIG ===
DEFAULT_AI_MODEL=gpt-4-turbo
HIPAA_AI_MODEL=bastion
USE_HIPAA_MODE=true

# === APP CONFIGURATION ===
PORT=3000
DOMAIN_URL=http://localhost:3000

# === EMAIL SETTINGS ===
REPORT_EMAIL_FROM=nate@2ndopinionmd.ai
ENABLE_DARK_MODE=true

# === MONGODB CONFIGURATION ===
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=2ndopinionmd
SECRET_KEY=your-secret-key-for-jwt
ACCESS_TOKEN_EXPIRE_MINUTES=30

# === CHROMA DB CONFIGURATION ===
CHROMA_PERSIST_DIR=./chroma_db
```

### 🧹 Formatting & Linting
To auto-format the codebase:
```zsh
yarn format
```
This ensures consistent code style for all components and pages.

### 🧪 Testing
We are not using a test suite at MVP stage.
✅ If the app builds and runs (yarn dev), treat it as a successful pass.

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
 ┣ 📂public
 ┃ ┗ 📂images
 ┃   ┣ 2ndOpinionMD-logo.jpg
 ┃   ┗ brain-heartbeat.png
 ┣ 📂server
 ┃ ┣ 📂api
 ┃ ┃ ┣ app.py
 ┃ ┃ ┣ auth.py
 ┃ ┃ ┗ journal.py
 ┃ ┣ 📂models
 ┃ ┃ ┗ 📂mongodb
 ┃ ┃   ┣ auth.py
 ┃ ┃   ┣ database.py
 ┃ ┃   ┗ models.py
 ┃ ┣ 📂vectordb
 ┃ ┃ ┣ chroma_setup.py
 ┃ ┃ ┗ query_engine.py
 ┃ ┗ requirements.txt
 ┣ 📂src
 ┃ ┣ 📂components
 ┃ ┃ ┣ 📂auth
 ┃ ┃ ┃ ┣ LoginForm.js
 ┃ ┃ ┃ ┣ RegisterForm.js
 ┃ ┃ ┃ ┗ SplashPage.js
 ┃ ┃ ┣ 📂journal
 ┃ ┃ ┃ ┣ JournalDetail.js
 ┃ ┃ ┃ ┣ JournalForm.js
 ┃ ┃ ┃ ┗ JournalList.js
 ┃ ┃ ┣ NavBar.jsx
 ┃ ┃ ┣ HeroSection.jsx
 ┃ ┃ ┣ PricingSection.jsx
 ┃ ┃ ┣ TestimonialCarousel.jsx
 ┃ ┃ ┣ FAQAccordion.jsx
 ┃ ┃ ┣ ReportOverview.jsx
 ┃ ┃ ┣ ConditionCard.jsx
 ┃ ┃ ┗ Footer.jsx
 ┃ ┣ 📂styles
 ┃ ┃ ┣ GlobalStyles.css
 ┃ ┃ ┣ Journal.css
 ┃ ┃ ┗ SplashPage.css
 ┃ ┗ App.js
 ┣ 📄 .env
 ┣ 📄 .nvmrc
 ┣ 📄 package.json
 ┗ 📄 README.md
```

## 🎨 Style Guide
### Color Variables
```css
:root {
  --color-primary: #3A7BD5;
  --color-secondary: #58B09C;
  --color-bg: #F7F9FA;
  --color-text-primary: #333333;
  --color-text-secondary: #666666;
}
```

### Fonts
- Headings: 'Inter', sans-serif (weight 700)
- Body: 'Roboto', sans-serif (weight 400)

### Font Sizes:
- Headings: 28–36px
- Body: 16–18px
- Line Height: 1.5
- Border Radius: 8px
- Spacing Scale: 8px / 16px / 24px

## 🔐 Security Features

### Rate Limiting

The API implements rate limiting to protect against brute force attacks and abuse:

- Authentication endpoints: 5 requests per minute per IP address
- General API endpoints: 60 requests per minute per IP address

When rate limits are exceeded, the API returns a 429 Too Many Requests response with a Retry-After header indicating when the client should try again.

### Email Verification

User registration requires email verification:

- When a user registers, a verification email is sent to their email address
- The user must click the verification link to activate their account
- Unverified users cannot log in to the application
- Verification tokens expire after 30 minutes
- Users can request a new verification email if needed

## 🧠 Notes for Devin & Future Devs
- All commands assume Node 18 is active.
- Yarn must be used instead of npm.
- No PHI is stored at this stage.
- PDF reports are generated based on symptom input + structured disease database (100+ conditions).
- Components are modular to allow reuse + future expansion.
- We are using React (with potential migration to Next.js or Vercel hosting later).
- A/B Testing for Hero Variants A & B is built in (pass variant="A" or "B" to the HeroSection component).
- Journal entries include AI-powered analysis with follow-up questions.
- Initial symptoms from the intake page are tracked with dates and demographics.
- MongoDB is used for user authentication and journal storage.

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


