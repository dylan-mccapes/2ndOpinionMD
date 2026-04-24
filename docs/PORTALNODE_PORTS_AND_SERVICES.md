# PortalNode / FORWARD pilot — ports, services, and data paths

Single reference for the **RTX-4090 Windows + WSL Ubuntu** pilot, the **Mac** public edge, and **local dev** defaults.  
**Secrets:** live DB password lives only in **`docs/PORTALNODE_SECRETS.local.md`** (gitignored) and/or **`.env.portalnode`** (gitignored). Use **`docs/PORTALNODE_SECRETS.local.md.example`** as a template for new machines.

Companion strategy: `reports/STRATEGY_FORWARD_PILOT_4090_DEPLOYMENT_20260424.md`.

---

## PostgreSQL (PortalNode pilot DB)

| Item | Value |
|------|--------|
| Database | `portalnode` |
| Role | `portalnode` |
| Password | In `docs/PORTALNODE_SECRETS.local.md` (not in git) |
| Port (TCP) | **5432** |
| Host from WSL (password auth) | **127.0.0.1** |
| Unix socket | `/var/run/postgresql` — **peer** auth: OS username must equal `portalnode`; typical WSL user does not, so use **127.0.0.1** + password. |
| `psql` / restore / embed | `export PGHOST=127.0.0.1 PGPORT=5432 PGUSER=portalnode PGDATABASE=portalnode` + `PGPASSWORD` from secrets file. |

Install / restore / embed scripts: `scripts/portalnode4090_install_postgres.sh`, `scripts/portalnode4090_restore_mkg.sh`, `server/scripts/embed_rag_corpus_local_slice.py`.

---

## FastAPI (main app)

| Context | Host / port |
|---------|-------------|
| Default local (uvicorn) | **http://127.0.0.1:8000** |
| Mac production (nginx → app) | **443** TLS → upstream **8000** |
| Pilot: Mac proxy → 4090 | nginx `proxy_pass` to **http://192.168.0.245:8000** (LAN) when enabled |

OpenAPI: `http://localhost:8000/docs` (dev).

---

## OCR Forge (CUDA EasyOCR service)

| Item | Value |
|------|--------|
| Port | **8765** |
| Env | `OCR_FORGE_URL` (e.g. `http://192.168.0.245:8765` from Mac, `http://127.0.0.1:8765` on same host) |
| Default in code | `server/ocr_service/client.py` → `http://localhost:8765` |

---

## Ollama (`eoh-llama-*`)

| Item | Value |
|------|--------|
| Default port | **11434** |
| Env | `OLLAMA_BASE_URL` (OpenAI-compatible base; code may strip trailing `/v1`) |
| WSL → Ollama on Windows | Often `http://$(grep nameserver /etc/resolv.conf | awk '{print $2}'):11434` — see `server/scripts/ptv_chatbot_wsl.py` |
| LAN pilot (4090) | e.g. `http://192.168.0.245:11434` when calling from Mac |

---

## SSH

| Item | Value |
|------|--------|
| Pilot host | `dylan@192.168.0.245` (example) |
| Port | **22** (default) |

Default shell on Windows OpenSSH: **PowerShell** — use `wsl -d Ubuntu -- …` for Linux commands.

---

## MKG dump / restore (pilot slice)

| Artifact | Role |
|----------|------|
| `scripts/mkg_dump_for_4090.sh` | Mac → full slice + ontology + schema |
| `scripts/mkg_dump_for_4090_slice_only.sh` | Mac → refresh `05b` + manifest only |
| `scripts/portalnode_rag_slice_sources.txt` | `rag_corpus.source` allowlist |
| `scp` to Windows | **No `rsync` on remote** — use `scp` / `tar`+`scp` |
| Typical Windows drop | `C:\Users\dylan\forward_pilot_dump\` → WSL `/mnt/c/Users/dylan/forward_pilot_dump/` |
| `role "2ndopinionmd" does not exist` on restore | Old dumps: run **`scripts/portalnode_stub_mac_owner_role.sql`** once as `postgres` (see file header). New dumps use `--no-owner` from `mkg_dump_for_4090.sh`. |
| `schema "b2b" already exists` (or similar) on re-restore | Partial **`02_*.sql.gz`** from an earlier attempt. Run **`sudo bash scripts/portalnode4090_reset_mkg_target_db.sh`**, then restore again. |

---

## Mac / production edge (reference)

| Service | Notes |
|---------|--------|
| nginx | TLS, `client_max_body_size` for large uploads |
| Static site | e.g. `/opt/homebrew/var/www/2ndopinionmd` + `index.html` |
| Hostnames | `2ndopinionmd.ai`, `upload.2ndopinionmd.ai` (grey cloud / direct when needed) |

---

## PostgreSQL (developer Mac — full MKG, not pilot)

| Item | Typical value |
|------|----------------|
| DB name | `2ndopinionmd` |
| User | `2ndopinionmd` |
| Port | **5432** |

Use `SYNC_DATABASE_URL` / `DATABASE_URL` from your local `.env` (never commit).

---

Copy `docs/PORTALNODE_SECRETS.local.md.example` → `docs/PORTALNODE_SECRETS.local.md` (gitignored) or merge into **`.env.portalnode`** and load with your app’s usual dotenv flow.

---

*Last updated: 2026-04-24 — ports aligned with repo scripts and FORWARD pilot layout.*
