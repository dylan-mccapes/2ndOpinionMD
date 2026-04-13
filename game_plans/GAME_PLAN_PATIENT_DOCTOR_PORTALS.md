# Game Plan: Patient & Doctor Portals (Phase 5c)

**Date:** 2026-02-20  
**Status:** Proposed  
**Owner:** Product + Devin  

---

## What This Is

2ndOpinionMD has two distinct user types: **patients** and **doctors**. Each gets a dedicated portal with role-specific features. The modes screen (ASK, CODING, EoH, EoHD) becomes the **splash page** shown to unauthenticated users, with login/register CTAs. After login, users are routed to their respective portal based on the role they chose at registration.

---

## Summary

| Role   | Portal        | Key Features                                                         |
|--------|---------------|----------------------------------------------------------------------|
| Patient| Patient Portal| Journal, timeline upload, EoHD query, own health data                 |
| Doctor | Doctor Portal | Patient list, view patient journals/timelines, ambient coding (future)|

---

## User Flow

### Registration (New Requirement)

```
/auth/register
    │
    ├─► Email, password, full name (existing)
    │
    └─► **Role selection (required):**
        ○ I am a patient  → user_type = "patient"
        ○ I am a doctor   → user_type = "doctor"
    │
    ▼
Email verification → /auth/verify → /auth/login
```

### Splash Page (Modes Screen)

- **Route:** `/` (HomePage)
- **Unauthenticated:** Show mode cards (ASK, CODING, EoH, EoHD) + "LOGIN" and "REGISTER" buttons. Clicking a mode prompts login if not authenticated.
- **Authenticated:** Redirect to role-specific portal:
  - Patient → `/patient` (patient portal)
  - Doctor  → `/doctor` (doctor portal)

### Patient Portal (`/patient`)

- **Access:** Authenticated users with `user_type === "patient"`
- **Features:**
  - **Journal** — Create, view, delete journal entries. AI analysis. Link to `/journal`
  - **Timeline** — Upload PDF, view timeline status, EoHD investigations. Links to `/timeline/upload`, `/eohd`
  - **Settings** — Profile, password
- **Layout:** Sidebar or tabs: Journal | Timeline | EoHD | Settings

### Doctor Portal (`/doctor`)

- **Access:** Authenticated users with `user_type === "doctor"`
- **Features:**
  - **Patient List** — List of patients linked to this doctor. Click to view patient detail.
  - **Patient Detail** — View patient's journal (read-only), timeline status, EoHD context. No edit of patient data.
  - **Ambient Coding** (future) — Audio capture, live transcript, code suggestions. See GAME_PLAN_DOCTOR_PORTAL.md
- **Layout:** Patient list (main) | Patient detail (drill-down) | Settings

---

## Data Model Changes

### 1. User Table

Add column:

```sql
user_type VARCHAR(20) NOT NULL DEFAULT 'patient'
  -- Values: 'patient' | 'doctor'
```

- **Migration:** Add `user_type` column. Existing users default to `'patient'` or require backfill.

### 2. Doctor–Patient Relationship

**Option A: Linking table (recommended)**

```sql
CREATE TABLE doctor_patients (
  id UUID PRIMARY KEY,
  doctor_id UUID NOT NULL REFERENCES users(id),
  patient_id UUID NOT NULL REFERENCES users(id),
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(doctor_id, patient_id)
);
```

- Doctors add patients (by invite code, email, or admin assignment).
- A patient can have multiple doctors; a doctor has many patients.

**Option B: Patient has doctor_id (simpler MVP)**

```sql
-- Add to users or a patient_profiles table
doctor_id UUID REFERENCES users(id)  -- nullable; patient's primary doctor
```

- One doctor per patient for MVP.
- Doctor sees patients where `patient.doctor_id = current_user.id`.

**Recommendation for Phase 5c:** Option B (patient has `doctor_id`) for speed. Can evolve to Option A later.

### 3. Patient Profiles (optional)

If not storing doctor_id on users:

```sql
CREATE TABLE patient_profiles (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL UNIQUE REFERENCES users(id),
  doctor_id UUID REFERENCES users(id),
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Backend Changes

### 1. Registration

**POST /api/auth/register**

Request body (add field):

```json
{
  "email": "user@example.com",
  "password": "...",
  "full_name": "Jane Doe",
  "user_type": "patient"   // or "doctor" — REQUIRED
}
```

- Validate `user_type in ("patient", "doctor")`.
- Store in users table.

### 2. Auth Response

**GET /api/auth/me**

Response (add field):

```json
{
  "id": "...",
  "email": "...",
  "full_name": "...",
  "subscription_tier": "free",
  "user_type": "patient",   // NEW
  "created_at": "..."
}
```

### 3. Doctor Endpoints

**GET /api/doctor/patients**

- Auth: required, `user_type === "doctor"`
- Returns: `[{ id, email, full_name, last_journal_date, has_timeline }]`
- Filter: `WHERE doctor_id = current_user.id` (or via doctor_patients join)

**GET /api/doctor/patients/{patient_id}/journal**

- Auth: required, doctor, and patient is in doctor's list
- Returns: Patient's journal entries (read-only). Reuse journal list shape.

**GET /api/doctor/patients/{patient_id}/timeline-status**

- Auth: required, doctor, patient in list
- Returns: Same as GET /api/timeline/status but for specified patient.

### 4. Patient–Doctor Linking (MVP)

**POST /api/doctor/link-patient** (or invite flow)

- Body: `{ "patient_email" }` or `{ "invite_code" }`
- Creates doctor_patient link or sets patient.doctor_id.
- Or: Admin/setup script assigns patients to doctors for MVP.

For **Phase 5c MVP**, linking can be:
- Manual: Seed data or script that sets `patient.doctor_id` for test users.
- Or: Doctor enters patient email; if patient exists and has no doctor, link is created. Patient must approve (future).

---

## Frontend Changes

### 1. Registration Page

- Add **role selector** (radio or card select): "I am a patient" | "I am a doctor"
- Required field. Submit includes `user_type`.

### 2. Splash Page (HomePage)

- **Unauthenticated:** Show mode cards. Each card click: navigate to `/auth/login?from=/ask` (or the mode route). Show LOGIN and REGISTER buttons prominently.
- **Authenticated:** Redirect to `/patient` or `/doctor` based on `user.user_type`. No mode cards for logged-in users on `/` (or show them as secondary nav).

### 3. Patient Portal Page

- **Route:** `/patient`
- **Layout:** Header with logo, nav (Journal, Timeline, EoHD, Settings), logout.
- **Content:** Dashboard or default view (e.g. Journal). Links to existing JournalPage, TimelineUploadPage, EohdPage.
- **Protected:** Auth required, `user_type === "patient"`. Else redirect or 403.

### 4. Doctor Portal Page

- **Route:** `/doctor`
- **Layout:** Header, nav (Patients, Settings), logout.
- **Content:**
  - **Patient list:** Cards or table of patients. Columns: name, email, last activity, timeline status.
  - **Patient detail:** Click patient → `/doctor/patients/:patientId` — read-only journal, timeline status, link to EoHD context (if applicable).
- **Protected:** Auth required, `user_type === "doctor"`.

### 5. Routing Updates

| Route            | Access              | Content                    |
|------------------|---------------------|----------------------------|
| `/`              | All                 | Splash (modes + login) or redirect |
| `/auth/login`    | Anonymous           | Login form                 |
| `/auth/register` | Anonymous           | Register + role selector   |
| `/patient`       | Patient only        | Patient portal shell       |
| `/patient/journal` | Patient only      | Journal (existing)         |
| `/patient/timeline` | Patient only     | Timeline upload            |
| `/patient/eohd`  | Patient only        | EoHD                       |
| `/doctor`        | Doctor only         | Doctor portal, patient list|
| `/doctor/patients/:id` | Doctor only   | Patient detail (read-only) |
| `/ask`, `/coding`, `/eoh` | Auth?        | Modes (maybe from splash)  |

---

## Implementation Phases

### Phase 5c.1: Data Model & Auth

- [ ] Add `user_type` to users (migration). Default `'patient'`.
- [ ] Add `doctor_id` to users or create doctor_patients table (migration).
- [ ] Update POST /api/auth/register to require and store `user_type`.
- [ ] Update GET /api/auth/me to return `user_type`.

### Phase 5c.2: Registration UI

- [ ] Add role selector to RegisterPage (patient | doctor).
- [ ] Submit `user_type` in registration payload.

### Phase 5c.3: Splash Page & Routing

- [ ] HomePage: unauthenticated → mode cards + LOGIN/REGISTER.
- [ ] HomePage: authenticated → redirect to `/patient` or `/doctor` by user_type.
- [ ] Add `/patient` and `/doctor` routes.
- [ ] Create PatientPortalPage (shell with nav) and DoctorPortalPage (shell with patient list).

### Phase 5c.4: Patient Portal

- [ ] PatientPortalPage: nav to Journal, Timeline, EoHD, Settings.
- [ ] Nest existing JournalPage, TimelineUploadPage, EohdPage under `/patient/*` or render in portal layout.
- [ ] Guard: only `user_type === "patient"`.

### Phase 5c.5: Doctor Portal

- [ ] GET /api/doctor/patients — list patients for current doctor.
- [ ] DoctorPortalPage: patient list UI.
- [ ] GET /api/doctor/patients/{id}/journal (or reuse journal API with patient_id when doctor).
- [ ] DoctorPatientDetailPage: read-only journal, timeline status.
- [ ] Guard: only `user_type === "doctor"`.

### Phase 5c.6: Patient–Doctor Linking (MVP)

- [ ] Seed or script to link test patients to test doctors.
- [ ] Or: simple POST /api/doctor/link-patient by email for MVP.

---

## Security

- **Authorization:** Every doctor endpoint must verify `current_user.user_type === "doctor"` and that the requested patient is in the doctor's list (or `patient.doctor_id === current_user.id`).
- **Patient data:** Patients can only access their own journal, timeline, EoHD. Doctors can read but not edit patient data.
- **Role escalation:** Users cannot change `user_type` after registration without admin support (future).

---

## Open Questions

1. **Linking flow:** How does a doctor add a patient? Invite by email? Patient enters doctor code? Admin assignment?
2. **Multi-doctor:** Can a patient have multiple doctors? (Affects schema choice.)
3. **Subscription:** Does `subscription_tier` apply to both roles, or only patients? Doctors may have different tiers (e.g. clinical, enterprise).

---

## Success Criteria

- User chooses patient or doctor at registration.
- Unauthenticated users see modes splash with login/register.
- Authenticated patients land in patient portal with journal, timeline, EoHD.
- Authenticated doctors land in doctor portal with patient list.
- Doctors can view (read-only) their patients' journal and timeline status.
- `yarn build` passes. No new dependencies unless justified.

---

**End of Game Plan**
