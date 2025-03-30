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

---

## 🛠️ Environment Setup

### 🧬 Required Versions
- **Node.js**: `v18`
- **Yarn**: Installed and used for package management

We recommend using [NVM](https://github.com/nvm-sh/nvm) to manage your Node versions.

To set the correct version:
```bash
nvm use 18

You can also create a .nvmrc file in the root with:
echo "18" > .nvmrc

📦 Installation
After cloning this repo, install dependencies:
yarn install

💻 Running the App (Local Dev)
To start the development server:
yarn dev

Then open your browser to:
👉 http://localhost:3000


🧹 Formatting & Linting
To auto-format the codebase:
yarn format
This ensures consistent code style for all components and pages.


🧪 Testing
We are not using a test suite at MVP stage.
✅ If the app builds and runs (yarn dev), treat it as a successful pass.

🧾 File Structure (React + Components)

css
2ndOpinionMD-React/
 ┣ 📂src
 ┃ ┣ 📂components
 ┃ ┃ ┣ NavBar.jsx
 ┃ ┃ ┣ HeroSection.jsx
 ┃ ┃ ┣ PricingSection.jsx
 ┃ ┃ ┣ TestimonialCarousel.jsx
 ┃ ┃ ┣ FAQAccordion.jsx
 ┃ ┃ ┣ ReportOverview.jsx
 ┃ ┃ ┣ ConditionCard.jsx
 ┃ ┃ ┗ Footer.jsx
 ┃ ┣ 📂styles
 ┃ ┃ ┗ GlobalStyles.css
 ┃ ┗ App.jsx
 ┣ 📄 .nvmrc
 ┣ 📄 package.json
 ┗ 📄 README.md

🎨 Style Guide
Color Variables
:root {
  --color-primary: #3A7BD5;
  --color-secondary: #58B09C;
  --color-bg: #F7F9FA;
  --color-text-primary: #333333;
  --color-text-secondary: #666666;
}

Fonts
Headings: 'Inter', sans-serif (weight 700)

Body: 'Roboto', sans-serif (weight 400)

Font Sizes:

Headings: 28–36px

Body: 16–18px

Line Height: 1.5

Border Radius: 8px

Spacing Scale: 8px / 16px / 24px

🧠 Notes for Devin & Future Devs
All commands assume Node 18 is active.

Yarn must be used instead of npm.

No PHI is stored at this stage.

PDF reports are generated based on symptom input + structured disease database (100+ conditions).

Components are modular to allow reuse + future expansion.

We are using React (with potential migration to Next.js or Vercel hosting later).

A/B Testing for Hero Variants A & B is built in (pass variant="A" or "B" to the HeroSection component).


📄 Future To-Do (Post-MVP)
Add formal test suite

Implement backend report PDF generator

Add email delivery (via nate@2ndopinionmd.ai)

Migrate to secure API architecture

HIPAA-compliant data collection (opt-in)

Symptom journal tracking (Phase 2)

Payment gateway for Basic ($19.99) and Advanced ($49.99) reports

💬 Contact
For access, support, or onboarding:

📧 nate@2ndopinionmd.ai
🔗 2ndOpinionMD.ai (coming soon)

Built with ❤️ to shorten the diagnostic journey for millions suffering from misdiagnosed autoimmune diseases.


