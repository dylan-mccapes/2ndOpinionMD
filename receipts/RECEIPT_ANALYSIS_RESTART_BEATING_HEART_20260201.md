# RECEIPT: Analysis of Restart .BeatingHeart Process (2026-02-01)

**Artifact under review:** receipts/RESTART_BEATING_HEART_20260201.md (trimmed; earlier noise removed by operator)  
**Reviewer:** Auto (Executor)  
**Mode:** Process analysis · blockers · resolution · lessons  
**Date:** 2026-02-01

---

## 1. Process summary

The document is a terminal log of the **.BeatingHeart restart** for 2OPMD (2ndOpinionMD-MVP): rebuilding the venv, attempting to run the FastAPI server, recovering PostgreSQL, and achieving a running server.

**Outcome:** Server started successfully; Uvicorn running on http://0.0.0.0:8000; database connection initialized.

---

## 2. Phases (as recorded)

| Phase | Action | Result |
|-------|--------|--------|
| 1 | `rm -rf .BeatingHeart` then `./SETUP_BEATING_HEART.sh` | .BeatingHeart recreated with Python 3.12; full `server/requirements.txt` install (uvicorn, asyncpg, etc.) |
| 2 | First `./RUN_POSTGRES_APP.sh` | **Fail:** `InvalidRequestError: The asyncio extension requires an async driver. The loaded 'psycopg2' is not async.` (DATABASE_URL was plain `postgresql://`) |
| 3 | Second `./RUN_POSTGRES_APP.sh` (after app fix: URL normalized to `postgresql+asyncpg://`) | **Fail:** `ConnectionRefusedError` on `('::1', 5432)` — PostgreSQL not running |
| 4 | `brew services start postgresql@14` | **Fail:** `Bootstrap failed: 5: Input/output error` (launchctl) |
| 5 | `launchctl bootout gui/501 ... postgresql@14.plist` then `brew services start postgresql@14` | **Success:** PostgreSQL service started |
| 6 | `pg_ctl -D /opt/homebrew/var/postgresql@14 start` (attempt while service already/still claimed port) | **Fail:** `FATAL: lock file "postmaster.pid" already exists` (HINT: PID 939) |
| 7 | `kill -9 $(lsof -i :5432 -t)` | **No-op:** lsof returned nothing (stale lock; no process on 5432) |
| 8 | `kill -9 939`; `rm .../postmaster.pid`; `pg_ctl -D ... start` | **Success:** PostgreSQL started; automatic recovery; "database system is ready to accept connections" |
| 9 | `./RUN_POSTGRES_APP.sh` | **Success:** "Database connection initialized successfully"; "Uvicorn running on http://0.0.0.0:8000" |

---

## 3. Blockers and resolutions

1. **Async driver (psycopg2 vs asyncpg)**  
   - **Blocker:** App passed plain `postgresql://` to `create_async_engine`; SQLAlchemy loaded psycopg2 (sync).  
   - **Resolution:** Normalize URL in lifespan/session: if `postgresql://` and no `+asyncpg`, replace with `postgresql+asyncpg://`. (Done in app_postgres.py and server/db/session.py.)

2. **PostgreSQL not running**  
   - **Blocker:** Nothing listening on 5432 → ConnectionRefusedError.  
   - **Resolution:** Start PostgreSQL (see next).

3. **launchctl bootstrap failure**  
   - **Blocker:** `brew services start postgresql@14` → exit 5 (Input/output error).  
   - **Resolution:** Unload stale plist: `launchctl bootout gui/501 ~/Library/LaunchAgents/homebrew.mxcl.postgresql@14.plist`, then `brew services start postgresql@14` again → success.

4. **Stale postmaster.pid**  
   - **Blocker:** postmaster.pid existed (PID 939); no process on 5432; `pg_ctl start` refused.  
   - **Resolution:** `kill -9 939` (from HINT); `rm /opt/homebrew/var/postgresql@14/postmaster.pid`; then `pg_ctl -D /opt/homebrew/var/postgresql@14 start`.  
   - **Note:** `kill -9 $(lsof -i :5432 -t)` was useless when nothing was bound to 5432; must kill PID from lock file and remove lock.

5. **kill with empty PID list (macOS)**  
   - **Blocker:** `kill -9 $(lsof -i :5432 -t)` → `kill: usage: ...` when lsof returned empty.  
   - **Resolution:** SpellBook updated: macOS-safe form `PIDS=$(lsof -i :5432 -t); [ -n "$PIDS" ] && kill -9 $PIDS`; plus **postgres_stale_lock_spell**: kill PID from HINT, rm postmaster.pid, pg_ctl start.

---

## 4. Lessons for future restarts

- **Venv:** Python 3.12 required; SETUP_BEATING_HEART.sh enforces it. Relaxed pins (psycopg, numpy, scikit-learn) allowed install to complete.  
- **Config:** SYNC_DATABASE_URL is primary for rag_corpus; app derives async URL from it when needed.  
- **PostgreSQL order of operations:** (1) If brew services fails, try launchctl bootout then brew services start. (2) If postmaster.pid exists but no process on 5432: kill PID from HINT, rm postmaster.pid, pg_ctl start. (3) Use 127.0.0.1 in URL if localhost→IPv6 causes issues.  
- **SpellBook:** kill_port_spell (with macOS-safe variant) and postgres_stale_lock_spell document the above.

---

## 5. Assessment

- **Process:** Noisy but linear; each failure had a clear next step; operator (and prior fixes) resolved each blocker.  
- **Document:** RESTART_BEATING_HEART_20260201.md is a useful raw log for debugging; the trimmed version (noise removed) preserves the full sequence: venv build → async URL fix → PG not running → launchctl/postmaster.pid recovery → server up.  
- **Reproducibility:** A future "restart .BeatingHeart" runbook can be: (1) SETUP_BEATING_HEART.sh from 2ndOpinionMD-MVP, (2) ensure PostgreSQL is running (brew services or pg_ctl; if stale lock, use postgres_stale_lock_spell), (3) RUN_POSTGRES_APP.sh.

---

**Ingested from:** 2ndOpinionMD-MVP/receipts/RESTART_BEATING_HEART_20260201.md  
**Analysis filed:** 2ndOpinionMD-MVP/receipts/RECEIPT_ANALYSIS_RESTART_BEATING_HEART_20260201.md  
**Status:** Complete
