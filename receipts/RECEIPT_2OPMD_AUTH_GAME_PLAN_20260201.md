# RECEIPT: 2OPMD Auth (Game Plan) — Session & Timeline

**Source:** game_plans/2OPMD_APPLICATION_GAME_PLAN.md § II. AUTHENTICATION SYSTEM (3Pi$73Mic87MLV4UL7)  
**Date:** 2026-02-01  
**Executor:** Auto

---

## 1. Delivered

- **Migration:** `server/alembic/versions/002_add_operators_sessions_timelines.py`
  - Tables: `operators` (operator_id, user_id FK users, operator_type, sovereignty_level), `sessions` (session_id, operator_id, session_token, instantiated_at, last_activity_at, closed_at, session_metadata), `patient_timelines` (timeline_id, patient_operator_id, timeline_name, created_at, last_enrichment_at, anonymization_consent), `timeline_access` (access_id, timeline_id, operator_id, access_level, granted_at, granted_by, expires_at, access_reason).
  - Revises: `755e5f98fff6`.

- **Session routes:** `server/api/session_routes.py`
  - **POST /api/session/instantiate** — Start Session: body `{ email, password }`; authenticates via existing User; get-or-create Operator (patient); create Session; return `{ session_token, operator_type, timeline_id }` (timeline_id null if not yet initialized).
  - **POST /api/session/close** — Close Session: `Authorization: Bearer <session_token>`; sets `sessions.closed_at`.

- **Timeline route:** same file, `timeline_router`
  - **POST /api/timeline/initialize** — First-time patient: `Authorization: Bearer <session_token>`; body `{ timeline_name, patient_info? }`; creates `patient_timelines` row; returns `{ timeline_id, created_at, status }`. Requires patient session; 400 if timeline already exists for operator.

- **App wiring:** `server/api/app_postgres.py`
  - `app.include_router(session_router, prefix="/api/session", tags=["session"])`
  - `app.include_router(timeline_router, prefix="/api/timeline", tags=["timeline"])`

---

## 2. Language (per game plan)

- **Start Session** (not Login): `/api/session/instantiate`.
- **Close Session** (not Logout): `/api/session/close`.
- Session token is opaque (`secrets.token_urlsafe(32)`), stored in `sessions.session_token`; client sends `Authorization: Bearer <session_token>`.

---

## 3. Flow

1. Client: **POST /api/session/instantiate** with email + password → `session_token`, `operator_type`, `timeline_id` (null if first time).
2. First-time patient: **POST /api/timeline/initialize** with `Authorization: Bearer <session_token>`, body `timeline_name`, optional `patient_info` → `timeline_id`.
3. Later: **POST /api/session/close** with `Authorization: Bearer <session_token>` → session closed.

Existing **/api/auth/register** and **/api/auth/token** (login) unchanged; instantiate reuses same User and adds Operator + Session.

---

## 4. Run migration

From repo root (2ndOpinionMD-MVP), with `.BeatingHeart` venv and PostgreSQL up:

```bash
source .BeatingHeart/bin/activate
cd server && alembic upgrade head
```

---

**Status:** Complete. Auth enabled per game plan; migration and routes ready.
