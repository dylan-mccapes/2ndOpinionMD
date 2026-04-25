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

Install / restore / embed: `scripts/portalnode4090_install_postgres.sh`, `scripts/portalnode4090_restore_mkg.sh`, `scripts/portalnode4090_embed_rag_slice.sh` (wraps `server/scripts/embed_rag_corpus_local_slice.py`, **BAAI/bge-base-en-v1.5** 768-d). Embed accepts **`SYNC_DATABASE_URL`** or **`DATABASE_URL`** or **`PGUSER`+`PGDATABASE`+`PGPASSWORD`** (+ **`PGHOST`**). On Ubuntu 24.04+ use **`scripts/portalnode4090_bootstrap_venv_embed.sh`** (PEP 668 — no system `pip install`). If **`pip install -r server/requirements.txt`** still tries to **build `psycopg2` from source** (`libpq-fe.h` missing), **`git pull`** (requirements use **`psycopg2-binary`** only) or install **`sudo apt-get install -y libpq-dev build-essential`**.

### This machine (Windows + WSL Ubuntu)

Pilot Postgres is **Linux-only** (Ubuntu packages: PostgreSQL + `postgresql-*-pgvector`). On Windows, use **WSL2**; do not run the `.sh` installer in PowerShell.

1. **WSL:** `wsl --install -d Ubuntu` (once), then open **Ubuntu** and `sudo apt-get update`.
2. **Install cluster + role + DB** from the repo you already cloned (any drive letter, e.g. `C:\2OPMD\2ndOpinionMD-MVP`):
   - **PowerShell:** `cd` to `...\2ndOpinionMD-MVP\scripts`, then  
     `.\portalnode4090_wsl.ps1 -InstallFromRepo -WslDistro Ubuntu`  
     Or **inside WSL:**  
     `cd /mnt/c/2OPMD/2ndOpinionMD-MVP && sudo bash scripts/portalnode4090_install_postgres.sh`
3. **Save the password** the installer prints (or set `PORTALNODE_DB_PASSWORD` before step 2). Copy **`docs/PORTALNODE_SECRETS.local.md.example`** → **`docs/PORTALNODE_SECRETS.local.md`** and fill **`SYNC_DATABASE_URL`** / **`PGPASSWORD`** (see table above: **127.0.0.1** + **portalnode** user).
4. **Load data:** copy the Mac dump tree (with **`05b_rag_corpus_slice.copy.gz`**) onto this PC, then from WSL (or **`.\portalnode4090_wsl.ps1 -Restore`** with **`$env:PGPASSWORD`** set) run **`scripts/portalnode4090_restore_mkg.sh`** with **`DUMP_DIR`** pointing at that folder. **`portalnode4090_wsl.ps1 -Restore`** auto-resolves the restore script from this clone via **`wslpath`** (works for repos outside **`C:\Users\<you>\2ndOpinionMD-MVP`**).
5. **Optional:** local **`embedding_local`** backfill: **`scripts/portalnode4090_bootstrap_venv_embed.sh`**, then **`scripts/portalnode4090_embed_rag_slice.sh`** (or run the Python module directly).
6. **MKG + 8B harness (4090):** from repo root in WSL (venv + `PYTHONPATH`), **`bash scripts/portalnode4090_mkg_harness.sh "your clinical query"`** — sets **`OLLAMA_MODEL=eoh-llama`** and **`OLLAMA_NUM_CTX=32768`** (main q8_0 Modelfile). Rebuild after edits: **`ollama create eoh-llama -f server/ollama/eoh-llama3.1-8b.Modelfile`**. Local 4050 Lucifer stays **`eoh-llama-lucifer`** + 16K Modelfile.

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
| `relation "text.mimiciv_notes_resolved" does not exist` on **`02_*.sql.gz`** | **`ehr.v_timeline_note_events`** joins MIMIC text not shipped in the pilot dump. Current **`portalnode4090_restore_mkg.sh`** creates **`database/sql/portalnode_stub_text_mimic_for_4090.sql`** before 02; pull latest and re-run restore (after DB reset if 02 partially applied). |
| `text search configuration "public.simple_unaccent" does not exist` on **`05a_*.sql.gz`** | Mac FTS config missing on pilot. Restore runs **`database/sql/portalnode_stub_simple_unaccent.sql`** before 05a; **`portalnode4090_install_postgres.sh`** / reset also enable **`unaccent`**. Pull latest; **`CREATE EXTENSION unaccent`** as `postgres` if the DB predates that line, then re-run restore from 05a or full reset+restore. |
| `function public.keep_embedding_on_update() does not exist` on **`05a_*.sql.gz`** | **`rag_corpus`** triggers from Mac reference this function; not shipped in slice dumps. Restore runs **`database/sql/portalnode_stub_keep_embedding_on_update.sql`** (no-op) before 05a. Pull latest; or apply that SQL manually then replay 05a. |
| `function public.rag_corpus_tsv_update() does not exist` on **`05a_*.sql.gz`** | **`rag_corpus`** `ts` refresh trigger from Mac. Restore runs **`database/sql/portalnode_stub_rag_corpus_tsv_update.sql`** after **`simple_unaccent`** stub. Re-drop **`rag_corpus`** if replaying 05a after a partial apply. |
| `function public._set_updated_at() does not exist` | Mac **`updated_at`** trigger helper referenced from **`02`–`05a`**. Restore runs **`database/sql/portalnode_stub_set_updated_at.sql`** before **`02`**. |
| `relation "rag_corpus" already exists` replaying **`05a_*.sql.gz`** | **`05a` is not idempotent.** Use **`./scripts/portalnode4090_replay_05a.sh`** (same **`DUMP_DIR`** / **`PG*`** as restore) — drops **`rag_corpus`**, reapplies 05a stubs + **`05a`**. Then run **`01`** only if auth seed never loaded, then **`05b`**. Or full **`sudo bash scripts/portalnode4090_reset_mkg_target_db.sh`** + **`portalnode4090_restore_mkg.sh`**. |

---

## Local embed progress (`embedding_local`)

`server/scripts/embed_rag_corpus_local_slice.py` (via **`./scripts/portalnode4090_embed_rag_slice.sh`**) fills **`public.rag_corpus.embedding_local`** (768-d), **`embedding_local_model`**, and **`embedding_local_at`** per batch commit. While it runs, check progress **from another SSH session** on the same host:

```bash
export SYNC_DATABASE_URL='postgresql://portalnode:PASSWORD@127.0.0.1:5432/portalnode'
./scripts/portalnode4090_embed_progress.sh
```

Or poll every 30 seconds:

```bash
watch -n 30 ./scripts/portalnode4090_embed_progress.sh
```

**Manual SQL** (same DB; `psql` URI or `PG*` vars):

```sql
-- Overall
SELECT COUNT(*) AS total,
       COUNT(embedding_local) AS embedded,
       COUNT(*) - COUNT(embedding_local) AS remaining,
       ROUND(100.0 * COUNT(embedding_local) / NULLIF(COUNT(*), 0), 2) AS pct_done
FROM public.rag_corpus;

-- Heartbeat: last committed batch
SELECT MAX(embedding_local_at) AS last_embed_at_utc
FROM public.rag_corpus
WHERE embedding_local IS NOT NULL;

-- Where work is left (by source)
SELECT source,
       COUNT(*) FILTER (WHERE embedding_local IS NULL) AS pending
FROM public.rag_corpus
GROUP BY 1
HAVING COUNT(*) FILTER (WHERE embedding_local IS NULL) > 0
ORDER BY pending DESC
LIMIT 20;
```

The Python process also prints **`updated N rows (~X rows/s) last_id=...`** to stdout each batch — if it runs in **`tmux`/`screen`**, attach to that pane for a live line log.

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

*Last updated: 2026-04-24 — WSL `-InstallFromRepo`, restore path via `wslpath`, embed progress + ports.*
