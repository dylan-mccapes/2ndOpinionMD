# HANDOFF: Will Duncan — 2ndOpinionMD Security & UX Context

**For:** Will Duncan (Offensive Security Engineer → 2OPMD UX/Implementation)  
**From:** Dylan McCapes (operator) + .🦖LEGOS2 (Raptor Operator, filing)  
**Date:** 2026-03-03  
**Purpose:** Security red-flag inventory + project context for contractor onboarding  
**Prerequisites:** Resume on file (`job_search/2OPMD_UX_HIRE/Will_Duncan__Resume.pdf`), RECEIPT_WILL_DUNCAN_EMAIL_INTRO_20260302

---

## 0. Role Context

You were offered UX work on the RAG demo at 2ndopinionmd.ai/rag-demo — React app, boilerplate in place. Your resume is security-focused (20 yrs, penetration testing, exploit dev, red team) with strong full-stack and AI/ML. This handoff assumes you will look at the codebase through both lenses: implementation and security. We want you to see the red flags before you start, so we can triage honestly.

---

## 1. Security Red Flags (What You’d Notice)

These are the things an offensive security engineer would flag. No surprises.

### 1.1 JWT Secret Fallback (HIGH)

**Location:** `server/api/auth_postgres.py:45`

```python
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-jwt")
```

If `SECRET_KEY` is not set in production, the app falls back to a known default. JWT tokens become forgeable.

**Status:** `.env.example` has placeholder. Production *must* set `SECRET_KEY`. Not verified in startup.

**Recommendation:** Fail fast on missing `SECRET_KEY` in production (`APP_ENV=production`).

---

### 1.2 Unauthenticated RAG / Coding Endpoints (HIGH for HIPAA)

**Locations:**  
- `server/api/rag_stream_ask.py` — `/api/rag/ask_stream`, `/api/rag/coding_stream`  
- `server/api/rag_routes.py` — `/api/rag/ask`  
- `server/api/coding_routes.py` — `/api/coding`  
- `server/api/rag_stream_routes.py` — `/api/rag/search`

No `Depends(get_current_user_postgres)`. These endpoints accept clinical text and return diagnoses/codes. If PHI flows through (e.g., from a logged-in frontend that sends user context), that’s a HIPAA exposure. If they’re intentionally public for demo, the boundary needs to be explicit and documented.

**Status:** RAG demo is currently public. Auth-gated routes exist (journal, portal, patient, doctor) but RAG streaming does not require auth.

**Recommendation:** Document the intended trust boundary. If demo-only, add a banner. If production, gate on auth.

---

### 1.3 ADMIN_TOKEN for Diagnostic Rules Upsert (MEDIUM)

**Location:** `server/api/diagnostic_rules_routes.py:79`

```python
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
# ...
if not ADMIN_TOKEN or x_admin_token != ADMIN_TOKEN:
    raise HTTPException(401, ...)
```

Uses `X-Admin-Token` header. If `ADMIN_TOKEN` is unset, endpoint correctly rejects. Concerns: header could appear in logs; use constant-time compare.

**Status:** Env-driven. No constant-time comparison visible.

---

### 1.4 PHI in Repository (MEDIUM–HIGH)

**Locations:**  
- `2ndOpinionMD-MVP/receipts/` — EOHD packets, `*NORMAN_ROBERTS*`  
- Contains: MRN, DOB, address, medications, diagnoses

If this is real patient data, it should not be in version control.

**Status:** Appears to be test/comfort case (Norman Eric Roberts). Needs explicit classification: synthetic, de-identified, or real — and handling policy.

---

### 1.5 Hardcoded Credentials in Setup Script (LOW–MEDIUM)

**Location:** `server/scripts/setup_complete_postgres.sh:26,31`

```bash
sudo -u postgres psql -c "CREATE USER devin WITH PASSWORD 'devin123';"
sed -i 's|DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://devin:devin123@localhost:5432/2ndopinionmd|' .env
```

Dev/setup convenience. If this script is ever run against a shared or cloud DB, credentials are exposed.

**Recommendation:** Parameterize or remove; use env vars for setup.

---

### 1.6 Deprecated Auth Module (LOW)

**Location:** `server/api/auth_deprecated.py`

Deprecated auth routes still in tree. Could be dead code or alternate surface.

**Recommendation:** Remove if unused, or clearly mark and route away.

---

### 1.7 CORS Configuration

**Location:** `server/api/app_postgres.py` — `CORS_ALLOW_ORIGINS` from env

`.env.example`: `https://2ndopinionmd.ai`, `http://localhost:3000`, etc. Verify production does not use `*`.

---

### 1.8 Diagnostic Rules Read Endpoints (LOW)

**Locations:**  
- `GET /api/diagnostic_rules/list` — optional `q` param  
- `GET /api/diagnostic_rules/{rule_key}`  
- `POST /api/diagnostic_rules/{rule_key}/apply` — body: `facts`

Read endpoints are unauthenticated. `rule_key` in path — check for IDOR if keys are predictable. `apply` accepts arbitrary `facts`; ensure no injection in downstream eval.

---

### 1.9 Rate Limiting

**Location:** `server/utils/rate_limiter.py`

- Auth: 5 req/min  
- General: 60 req/min  
- Diagnose: 10 req/min  

RAG streaming may have different limits. Verify coverage for high-cost endpoints.

---

### 1.10 Security Middleware (Positive)

**Location:** `server/api/app_postgres.py:276–294`

Blocks: `/.env`, `/.git`, `/.config`, `/.aws`, `/.ssh`, `wp-admin`, `phpinfo`, etc. Good defensive hardening.

---

## 2. Project Structure (Where to Look)

| Path | Purpose |
|------|---------|
| `2opmd_spellbook.json` | Canonical spec — endpoints, UX invariants, env vars |
| `server/api/app_postgres.py` | Main FastAPI app, CORS, security middleware, router mounts |
| `server/api/auth_postgres.py` | JWT, bcrypt, `get_current_user_postgres` |
| `server/api/auth_routes_postgres.py` | Register, login, verify, forgot/reset password |
| `server/api/rag_stream_*.py` | SSE streaming for ASK, CODING, EoH, EoHD |
| `server/api/diagnostic_rules_routes.py` | Rules CRUD, `X-Admin-Token` |
| `server/utils/rate_limiter.py` | Rate limit deps |
| `.env.example` | All env vars; `.env` gitignored |
| `HANDOFF_MKG_INGESTION_ANDRAS.md` | Data ingestion (MakefileBook) |
| `docs/MKE.md` | Machine Knowledge Engine architecture |

---

## 3. What We’re Asking of You

1. **Implementation:** Turn the RAG demo boilerplate into a solid, usable interface. React + RAG API wiring. You have the technical ceiling for it.

2. **Security lens:** As you work, note anything else that raises flags. We’d rather know early.

3. **Scope clarification:** If the role is “implement from existing patterns” — you’re qualified. If it’s “design systems, Figma, user research” — that’s a different skills match. Worth a call to align.

---

## 4. Cross-Refs

- **Resume:** `job_search/2OPMD_UX_HIRE/Will_Duncan__Resume.pdf`
- **Receipt:** `job_search/2OPMD_UX_HIRE/RECEIPT_WILL_DUNCAN_EMAIL_INTRO_20260302.md`
- **SpellBook:** `2ndOpinionMD-MVP/2opmd_spellbook.json`
- **Live event (intro):** `receipts/live_events/LIVE_EVENT_LOG_FRONTIERS_APF_20260227.md` (§ Will Duncan)
- **Receipts structure:** `docs/RECEIPTS_AND_REPORTS_STRUCTURE.md`

---

**Filed:** 2ndOpinionMD-MVP/HANDOFF_WILL_DUNCAN_SECURITY_2OPMD_20260303.md  
**Actor:** .🦖LEGOS2
