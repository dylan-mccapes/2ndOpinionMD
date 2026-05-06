# STRATEGY — FORWARD Pilot on the RTX-4090 Build ("PortalNode-0")

**Date:** 2026-04-24
**Author:** 2ndOpinionMD Platform Team
**Pilot scope:** 5 → up to 500 patients (RA-first) from FORWARD anonymized track, all processing on the RTX-4090 Linux build at `dylan@192.168.0.245`.
**Public edge:** The Mac server (`2ndopinionmd.ai` / `upload.2ndopinionmd.ai`) stays up as a reverse-proxy + TLS terminator. No clinical reasoning happens on the Mac during the pilot.
**Status:** Proposal — ready for review and execution.

**Companion docs (traceable):**
- `docs/PORTALNODE_PORTS_AND_SERVICES.md` (ports, services, DSN patterns; secrets in gitignored `docs/PORTALNODE_SECRETS.local.md`)
- `reports/REPORT_FORWARD_KALEB_MICHAUD_PREP_20260421.md` (why RA-first, FORWARD ceiling = PROs only)
- `reports/REPORT_FORWARD_PILOT_DATA_REQUEST_20260422.md` (Data Request Specification — variables, cohort, format)
- `reports/STRATEGY_MKG_LOCAL_EMBEDDINGS_20260421.md` (single pgvector table, two spaces; BGE-base primary — we're applying that plan now)
- `reports/REPORT_EOH_LLAMA_70B_CALIBER_ONPREM_STUDIES_20260421.md`
- `reports/STRATEGY_BAYESIAN_PTV_UC_20260423.md` (PRO-composite flare + UC math — the output wrapper Kaleb is expecting)

---

## 0. TL;DR

1. **The 4090 becomes the full FORWARD pilot stack.** Postgres, Ollama, FastAPI, OCR Forge, embedder, frontend — everything. The Mac keeps HTTPS + nginx and proxies `/api/*` to `192.168.0.245:8000`. This matches the PortalNode-01 vision from the VC deck and the on-prem positioning Kaleb asked about.
2. **We do NOT pg_dump `rag_corpus` or MIMIC.** `rag_corpus` is 383 GB — 99 % of that is MIMIC training text we don't need for FORWARD. We ship a **rheum + canon slice (~1.1 M rows, ~90 MB raw text, no embeddings)** and **re-embed on the 4090** with `BAAI/bge-base-en-v1.5` (768-dim). That takes ~4–8 minutes of GPU time, once.
3. **The pg_dump has three layers:** (a) **shapes only** for `ehr` / `eoh` / `b2b` + core `public` auth tables (empty schema; pilot data fills it), (b) **full data** for `ontology.*` and `guidelines.*` (drug/code/phenotype crosswalks, ~9 GB → ~3 GB gzipped), (c) **text-only slice** of `rag_corpus` filtered to rheum / canon / non-MIMIC sources (~90 MB).
4. **Embedding model:** `BAAI/bge-base-en-v1.5` (768-dim) confirmed as primary per `STRATEGY_MKG_LOCAL_EMBEDDINGS`. No OpenAI calls on the 4090 pipeline. For PRO/biomedical-heavy rows we'll A/B `pritamdeka/S-PubMedBert-MS-MARCO` in Phase 2.
5. **FastAPI router on the 4090:** Yes — but it's the **whole existing `server/` app**, not a thin embedding-only router. OCR Forge already runs on the 4090 on `:8765`; we add the main FastAPI on `:8000` (same stack the Mac currently runs). One process per role, systemd-managed, air-gappable after setup.
6. **Patient data path:** Pilot patients (FORWARD-provided anonymized bundles) never touch the Mac filesystem. Uploads go through the Mac nginx straight to the 4090's FastAPI; patient_graph_vision, patient_artifacts, patient_timeline all live on the 4090's Postgres.
7. **Rollback:** One nginx config change (comment out the proxy line) and the Mac is the only origin again. Zero risk to the production demo path.

---

## 1. Why the 4090 and not the Mac

| Concern | Mac (current) | RTX-4090 (proposed) |
|---|---|---|
| LLM inference speed (8B) | ~15 tok/s on Metal | ~55 tok/s on CUDA (3.5×) |
| 70B feasibility | not today | q4_K_M fits in 24 GB once we flip `--num-gpu-layers -1`; tensor-parallel across two 4090s later |
| Embedding speed | ~200 rows/s on MPS | ~5,000 rows/s on CUDA |
| OCR Forge (EasyOCR) | already running here (port 8765) | already tested; keep it |
| Disk | 91 GB free after last cleanup | 8 TB NVMe, unused |
| Air-gap story for FORWARD | no — Mac is a public host | yes — LAN-only, can unplug post-setup |
| Matches "PortalNode-01" narrative | no | yes (Kaleb already heard this pitch) |

The 4090 is the node we've been promising. This pilot is the event that makes it real.

---

## 2. What lives where (target state)

```
                 Internet
                    │
       ┌────────────┴─────────────┐
       │  Mac (macOS, public edge) │
       │  ─ nginx + Let's Encrypt  │
       │  ─ static frontend        │
       │  ─ /api/* → 192.168.0.245 │
       │  ─ upload.2ndopinionmd.ai │
       │    → proxy_pass 4090:8000 │
       │     (client_max_body_size │
       │      unchanged: 500 MB)   │
       └────────────┬─────────────┘
                    │  LAN only
       ┌────────────┴─────────────────────────────┐
       │  RTX-4090 (Ubuntu 24.04, PortalNode-0)   │
       │  ─ Postgres 16 + pgvector  (5432, LAN)   │
       │  ─ Ollama      (11434)     eoh-llama-*   │
       │  ─ FastAPI     (8000)      server/...    │
       │  ─ OCR Forge   (8765)      already up    │
       │  ─ BGE embedder in-process (GPU, 768-d)  │
       │  ─ systemd units for all of the above    │
       │  ─ /var/lib/postgresql/pilot_ptvision    │
       │  ─ /opt/portalnode/2opmd_mvp  (git)      │
       └──────────────────────────────────────────┘
```

The Mac keeps exactly one public-facing job: **TLS + nginx.** It can be off, asleep, or replaced by Cloudflare Tunnel later; the 4090 carries the pilot.

---

## 3. Data-plane strategy — the pg_dump

### 3.1 What ships (and why)

| Layer | Schema / table | Mode | Size (est.) | Rationale |
|---|---|---|---|---|
| **A. Auth seed** | `public.users`, `public.operators`, `public.sessions`, `public.patient_timelines`, `public.timeline_access`, `public.doctor_patient_invites`, `public.journal_entries` | data + schema | < 1 MB | Seed Dylan, Andras; pilot PIs; FORWARD test user. Journal schema carries the `patient_reported_outcomes` JSON column (Alembic 006) that PRO events plug into. |
| **B. Patient substrate** | `ehr.*` (10 tables), `eoh.*` (5 tables), `b2b.*` (3 tables) | **schema only** | ~1 MB | Empty on arrival; pilot patients fill it. |
| **C. Ontology crosswalks** | `ontology.rxnorm_*`, `ontology.loinc_*`, `ontology.hpo_*`, `ontology.snomed_map_icd10cm`, `ontology.concepts`, `ontology.descriptions`, `ontology.relationships`, `ontology.synonyms`, `ontology.refset_members` | data + schema | ~9 GB raw / ~3 GB gz | RxNorm for DMARD/biologic canonicalization, LOINC for PROMIS T-score mappings, HPO for phenotype anchors, SNOMED for diagnosis dedup. All used by PTV enrichment. |
| **D. Guidelines** | `guidelines.va_docs`, `guidelines.va_sections` | data + schema | ~50 MB | Rheum-adjacent VA/DoD pain and MSK guidelines; useful for UC basis text. |
| **E. MKG slice** | `public.rag_corpus` **filtered** + `public.rag_corpus_chunks` | data, text-only (no embedding columns) | ~90 MB | See §3.2 below. |
| **F. Ethos canon** | covered by E (`source='eoh_canon_v6'`, 654 rows) | | | |

### 3.2 What does NOT ship

| Excluded | Size | Why |
|---|---|---|
| `public.rag_corpus` full (383 GB) | 383 GB | 99 % is MIMIC training text; not clinically useful for FORWARD. We slice. |
| `public.embedding_cache` (21 GB) | 21 GB | Rebuildable on demand; OpenAI-bound, pointless on an air-gapped box. |
| `ehr_mimic3.*`, `ehr_mimic4.*` | ~60 GB | Training / benchmark data. Not needed for FORWARD. |
| `text.mimic3_notes`, `text.mimiciv_notes`, `text.mimiciv_notes_hadm_map`, `text.n2c2_notes` | ~40 GB | Same. |
| `molecular.clinvar*`, `clingen.*` | ~18 GB | FORWARD has no biosamples/omics — `REPORT_FORWARD_KALEB_MICHAUD_PREP` §A.2 item 2 (the ceiling). |
| `norman_eric_roberts` rows in `rag_corpus` | 5.9 MB, 4223 rows | Patient-identifying — never ships off this Mac. |
| `rag_corpus` rows from MIMIC sources (`mimic4_note`, `mimic4_dx`, `mimic3_dx`, `mimic3_proc`, `mimic4_labitems`, `mimic3_labitems`) | ~370 GB | Training data; excluded by §3.3 filter. |

### 3.3 The rag_corpus filter (the only place it matters)

```sql
-- Sources that SHIP to 4090 (rheum + ontology crosswalks + guidelines canon + ethos)
SELECT id, source, source_id, title, text, ts, meta
FROM public.rag_corpus
WHERE source IN (
  -- Ontology rows (drug/lab/phenotype/ICD canonicalization)
  'rxnorm','loinc','hpo','snomed','icd10cm','icd11','orphanet','chv',
  -- Guidelines (rheum + pain + canon)
  'va_guidelines','acc_aha_valvular_2020',
  'ada_dm_2024',
  'kdigo_ckd_2021','kdigo_ckd_2024','kdigo_gn_ln_2021','kdigo_anemia_ckd_2023',
  'gold_copd_2023','gold_copd_2024','gina_asthma_2023',
  'cdc_opioid',
  -- Ethos canon
  'eoh_canon_v6','eoh_2025','eoh_gold_2025',
  -- NEW (Phase 2, FORWARD-specific): will be added
  'acr_eular','diagrules','pro_instruments','pubmd_rheum'
);
```

Row count estimate: ~1,052,000 rows, ~90 MB raw text (embeddings column **excluded** from the dump). On the 4090 we re-embed with BGE-base at ~5,000 rows/sec → ~4 minutes of GPU time.

Note: `acr_eular`, `diagrules`, `pubmd_rheum`, `pro_instruments` are not yet in `rag_corpus` (the MKG local-embeddings strategy flags them as Phase 2 ingests). We ship the slice now with whatever is present; those sources get ingested directly on the 4090 via new `mk/` targets (§7.3).

### 3.4 The actual dump commands

**Source of truth:** `scripts/mkg_dump_for_4090.sh` on the Mac origin. It writes `artifacts/forward_pilot_dump_<UTC>/` (override with `DUMP_ROOT=…`). Do not hand-copy older snippets from this report; they drifted.

**Guidelines (04):** the script runs `pg_dump --no-owner --no-acl --schema=guidelines`, which is the correct shape: **entire `guidelines` schema, DDL plus table data** (VA/WHO/CDC/NICE tables, diagnostic rules, and so on—not schema-only). The gzip is on the order of tens of MB compressed; if `04_guidelines.sql.gz` is tiny, the dump failed or pointed at the wrong database.

```bash
cd 2ndOpinionMD-MVP
export PGUSER=2ndopinionmd PGDATABASE=2ndopinionmd PGHOST=localhost PGPORT=5432
./scripts/mkg_dump_for_4090.sh
# Optional: DUMP_ROOT=$HOME/tmp/my_pilot_dump ./scripts/mkg_dump_for_4090.sh

# Ship the new folder to the 4090 (scp/tar if rsync is unavailable on Windows OpenSSH)
```

Total on-wire size: ~3.5 GB gzipped. At 100 Mbps LAN: ~5 min.

### 3.5 Restore on the 4090

**Preferred:** `scripts/portalnode4090_restore_mkg.sh` after `portalnode4090_install_postgres.sh` (stub SQL, load order, and `05b` column list match `mkg_dump_for_4090.sh`). Manual order below is only a sketch.

```bash
# ── Run on 4090 (dylan@192.168.0.245) ──────────────────────────────────────
DUMP=/opt/portalnode/forward_pilot_dump
sudo -u postgres createdb portalnode
psql -U portalnode -d portalnode -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -U portalnode -d portalnode -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

# Restore in order (schemas first, data second) — filenames from mkg_dump_for_4090.sh
zcat $DUMP/02_patient_substrate_schema.sql.gz | psql -U portalnode -d portalnode
zcat $DUMP/03_ontology.sql.gz                 | psql -U portalnode -d portalnode
zcat $DUMP/04_guidelines.sql.gz               | psql -U portalnode -d portalnode
zcat $DUMP/05a_rag_corpus_schema.sql.gz       | psql -U portalnode -d portalnode
zcat $DUMP/01_auth_seed.sql.gz                | psql -U portalnode -d portalnode

# Restore the rag_corpus slice (COPY binary; includes metadata column)
zcat $DUMP/05b_rag_corpus_slice.copy.gz | psql -U portalnode -d portalnode \
  -c "COPY public.rag_corpus(id, source, source_id, title, text, ts, meta, metadata) FROM STDIN WITH (FORMAT binary)"

# Integrity check: compare MANIFEST_slice_by_source.txt against on-4090 counts
diff <(cat $DUMP/MANIFEST_slice_by_source.txt) <(psql -U portalnode -d portalnode -tAc "
  SELECT source, count(*) FROM public.rag_corpus GROUP BY source ORDER BY source")
```

### 3.6 Embedding backfill (runs once, on 4090 GPU)

**Model (§4):** **`BAAI/bge-base-en-v1.5`**, **768-d**, `vector(768)` on `public.rag_corpus.embedding_local`. The runner adds `embedding_local` / `embedding_local_model` / `embedding_local_at` if missing (`server/scripts/embed_rag_corpus_local_slice.py`).

**WSL / Linux** (repo e.g. `/mnt/c/Users/dylan/2ndOpinionMD-MVP` or an ext4 checkout).

**PEP 668 (Ubuntu 24.04+ / Debian):** do not `pip install` into system Python. Use either **`source .BeatingHeart/bin/activate`** if that venv already has deps, or a one-time **`./scripts/portalnode4090_bootstrap_venv_embed.sh`** then **`source .venv_embed/bin/activate`**.

```bash
cd /mnt/c/Users/dylan/2ndOpinionMD-MVP   # or your checkout
git pull

# Pick ONE venv path:
#   source .BeatingHeart/bin/activate
#   OR (first time on a clean box):
./scripts/portalnode4090_bootstrap_venv_embed.sh && source .venv_embed/bin/activate

export SYNC_DATABASE_URL='postgresql://portalnode:PASSWORD@127.0.0.1:5432/portalnode'
# Or reuse restore env: same PGUSER PGDATABASE PGPASSWORD PGHOST → embed script builds DSN.
export LOCAL_EMBED_MODEL=BAAI/bge-base-en-v1.5   # default if unset
# export LOCAL_EMBED_DEVICE=cuda                  # optional; auto-picks cuda if available

./scripts/portalnode4090_embed_rag_slice.sh
# same as: python server/scripts/embed_rag_corpus_local_slice.py --batch-size 128
```

**Resume:** re-run the same command; only rows with `embedding_local IS NULL` are processed.

**App wiring:** set **`EMBED_BACKEND=local`** (and DB pointing at this Postgres) so retrieval uses `embedding_local` for the pilot; see `STRATEGY_MKG_LOCAL_EMBEDDINGS_20260421.md` for product flags.

Expected: ~1.05 M slice rows × ~200 tok avg × 768 dim @ batch 128 on a single 4090 ≈ **4–8 minutes** wall time, on the order of **~8 GB VRAM** during the pass (fits alongside an 8B LLM at q8_0).

---

## 4. Embedding model choice (decision = BGE-base, already blessed)

The MKG local-embeddings strategy already ran this analysis (`STRATEGY_MKG_LOCAL_EMBEDDINGS_20260421.md` §4). Restating for this pilot:

| Model | Dims | Size | 4090 throughput | Recommendation |
|---|---|---|---|---|
| **`BAAI/bge-base-en-v1.5`** | **768** | 440 MB | ~5000 rows/s | **Primary** — blessed, in-stack pattern from `PatientTimelineChart`. |
| `all-mpnet-base-v2` | 768 | 420 MB | ~4500 rows/s | Fallback for A/B. Well-understood failure modes. |
| `pritamdeka/S-PubMedBert-MS-MARCO` | 768 | 420 MB | ~3500 rows/s | Phase-2 A/B specifically on `pubmd_rheum` slice if BGE regresses. |
| `nomic-embed-text-v1.5` | 768 (matryoshka) | ~550 MB | via Ollama HTTP | Skipped — HTTP hop, weaker batch control. Ollama is for LLMs only. |
| `text-embedding-3-small` (OpenAI) | 1536 | cloud | — | **Skipped for FORWARD.** Cloud call on an on-prem pilot is a non-starter. |
| `bge-large-en-v1.5` | 1024 | 1.3 GB | ~2800 rows/s | Phase-3 upgrade candidate if the benchmark shows it matters. |

**All dim = 768**, so we can swap models without schema churn (the column is `vector(768)`). Patient-event embeddings (`ehr.patient_graph_chart`) stay on `all-MiniLM-L6-v2` (384-d) — existing production pattern, short texts, not worth re-embedding 37 MB for the pilot.

**Why not `text-embedding-3-small` at 768-d Matryoshka truncation?** OpenAI *does* ship truncatable embeddings, and mathematically the 768-d slice is competent. But every query embed would be an outbound API call — that breaks the whole "FORWARD data stays on premise" pitch. Not negotiable for the FORWARD pilot.

---

## 5. Architecture decision — is there a new FastAPI router on the 4090?

**Question:** *"I am assuming a FastAPI router on the 4090 build is needed as well, but maybe not."*

**Answer:** You don't need a **new router**. You need **the existing FastAPI stack, running on the 4090.** Same code, same routes. Three options were considered:

| Option | Shape | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A. Mac = origin, 4090 = service endpoint** (thin new router) | Mac runs full app; 4090 exposes only `/ocr/*`, `/embed`, `/llm`, remote-pg | minimal change | every request = 3 network hops; patient data still lands on Mac disk; Mac still a HIPAA surface | ❌ |
| **B. Mac = edge proxy, 4090 = full stack** (recommended) | Mac = nginx + TLS; 4090 runs Postgres + FastAPI + Ollama + OCR Forge; Mac proxies `/api/*` | matches PortalNode story; patient data never on Mac; air-gappable after setup; zero new code | requires new deploy unit on 4090; systemd units; firewall rules | ✅ |
| C. 4090 alone, kill the Mac | 4090 terminates TLS directly | simplest | Mac already has certs + DNS; unnecessary change for a pilot | ❌ |

**Option B is the path.** Zero new FastAPI code. We ship the **existing `server/`** directory to the 4090 and start it there. The only *additive* routers we write are:

1. **A tiny health/topology endpoint** — `GET /api/pilot/node_info` returning `{node: "portalnode-0", host: "192.168.0.245", gpu: "rtx-4090", forward_pilot: true, rag_corpus_rows: N, patient_count: N}`. ~30 LoC. Makes "the pilot is actually running on the 4090" legible to the frontend status line and the receipts.
2. **A FORWARD-specific ingestion router** — `POST /api/pilot/forward/ingest` that takes either `{events: [...]}` (structured PRO JSON per the DRS in `REPORT_FORWARD_PILOT_DATA_REQUEST_20260422.md`) or a Parquet upload, normalizes to PTV event shape, and feeds the existing `/api/timeline/{patient_id}/infer` pipeline. ~200 LoC. This is the *only* genuinely new router, and it's new because FORWARD's input format (semi-annual PRO questionnaires) isn't a PDF.

Everything else — OCR, 8B extraction, PTV build, graph enrichment, timeline query, journal storage, analytics — is **unchanged code running on a new host.**

---

## 6. The Mac's job (pilot-time)

1. **nginx reverse proxy.** `/api/*`, `/portal/*`, `/upload/*` → `http://192.168.0.245:8000`. `client_max_body_size 500m` unchanged. Static frontend continues to be served off Mac.
2. **TLS.** Let's Encrypt on `2ndopinionmd.ai` and `upload.2ndopinionmd.ai`. One renewal, one host.
3. **Upload relay.** Browser uploads hit the Mac (public IP), nginx proxies body to 4090. This means the PDF never touches the Mac filesystem — nginx streams it through.
4. **Retain the existing demo path.** Dylan's local dev (`dylan@2ndopinionmd.ai`, artifacts on Mac) stays exactly as-is. Pilot traffic is scoped under `/api/pilot/*` and `/portal/pilot/*` routes on the 4090 — completely separate DB namespace (different `database` entirely: `portalnode` vs `2ndopinionmd`).

### nginx delta (`/opt/homebrew/etc/nginx/servers/pilot.conf`, new file)

```nginx
# Pilot routes: forward to PortalNode-0 (4090 on LAN)
location /api/pilot/ {
    proxy_pass              http://192.168.0.245:8000;
    proxy_http_version      1.1;
    proxy_set_header        Host              $host;
    proxy_set_header        X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header        X-Forwarded-Proto $scheme;
    proxy_request_buffering off;
    proxy_buffering         off;
    client_max_body_size    500m;
    proxy_read_timeout      3600s;   # allow long OCR + PTV build
}
```

No existing route is touched. Rollback = `rm pilot.conf && nginx -s reload`.

---

## 7. The 4090 deployment plan

### 7.1 Host prep (one-time, ~30 min)

```bash
ssh dylan@192.168.0.245

# Prereqs
sudo apt update
sudo apt install -y postgresql-16 postgresql-16-pgvector postgresql-contrib \
                    python3.12 python3.12-venv build-essential poppler-utils \
                    tesseract-ocr ufw git

# Postgres 16 + pgvector (pilot DB on the local socket; port 5432 NOT exposed)
sudo -u postgres psql -c "CREATE ROLE portalnode WITH LOGIN PASSWORD 'set-via-.env';"
sudo -u postgres psql -c "ALTER ROLE portalnode CREATEDB;"
sudo -u postgres createdb -O portalnode portalnode

# Firewall: only what PortalNode-0 exposes
sudo ufw allow from 192.168.0.0/24 to any port 8000  proto tcp   # FastAPI (LAN)
sudo ufw allow from 192.168.0.0/24 to any port 8765  proto tcp   # OCR Forge (already open)
sudo ufw allow from 192.168.0.0/24 to any port 11434 proto tcp   # Ollama (LAN)
sudo ufw allow ssh
sudo ufw enable
```

The key posture: **Postgres is NOT on the LAN.** It only accepts local-socket connections from the FastAPI process. Patient data can't be queried by anything other than code the pilot runs.

### 7.2 Application deploy

```bash
sudo mkdir -p /opt/portalnode && sudo chown dylan /opt/portalnode
cd /opt/portalnode
git clone git@github.com:provenance-engines/PortalVision.git
cd PortalVision/2ndOpinionMD-MVP

# Python env (same SETUP_BEATING_HEART.sh script we already have)
./scripts/SETUP_BEATING_HEART.sh    # creates .BeatingHeart/ with all deps + ocrmac N/A on Linux

# Env file: PortalNode-0 specifics
cat > .env.portalnode <<'EOF'
POSTGRES_URL=postgresql://portalnode@/portalnode?host=/var/run/postgresql
SYNC_DATABASE_URL=postgresql://portalnode@/portalnode?host=/var/run/postgresql
EMBED_BACKEND=local
LOCAL_EMBED_MODEL=BAAI/bge-base-en-v1.5
OLLAMA_BASE_URL=http://localhost:11434
OCR_FORGE_URL=http://localhost:8765
EOH_LLAMA_MODEL=eoh-llama-8b
PORTALNODE_ID=portalnode-0
FORWARD_PILOT=true
CORS_ALLOW_ORIGINS=https://2ndopinionmd.ai,https://upload.2ndopinionmd.ai
LOG_LEVEL=INFO
EOF
```

### 7.3 systemd units (the three services)

One unit file per service, all `Restart=on-failure`, all log to journald.

```
/etc/systemd/system/portalnode-fastapi.service    → uvicorn server.api.app_postgres
/etc/systemd/system/portalnode-ollama.service     → ollama serve  (eoh-llama-8b primary)
/etc/systemd/system/portalnode-ocrforge.service   → server.ocr_service.app (port 8765, already existed)
```

Bring-up:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now portalnode-ollama portalnode-ocrforge portalnode-fastapi
sudo systemctl status portalnode-fastapi
```

### 7.4 Data ingest and enrichment Makefile targets (new on 4090)

The ACR/EULAR, PRO instruments, and rheum-PubMed sources don't exist in the Mac's `rag_corpus` yet. We add them **directly on the 4090** rather than shipping via pg_dump — this avoids round-tripping new data through the Mac and keeps the 4090 the canonical source for the pilot corpus.

```
mk/33_forward_pilot.mk              # new
  forward-pilot-mkg-acr           # ingest ACR/EULAR classification + treat-to-target
  forward-pilot-mkg-pro           # PROMIS, HAQ-II, RAPID3, MDHAQ item defs + MCID
  forward-pilot-mkg-pubmd-rheum   # PubMed rheum subset (MeSH-filtered, last 10y)
  forward-pilot-embed-slice       # re-embed rheum slice with bge-base-en-v1.5
  forward-pilot-refresh-mv        # refresh rag_corpus_forward materialized view
  forward-pilot-seed-users        # create the pilot PI users (Andras, Kaleb)
  forward-pilot-status            # row counts by source + embedding coverage
```

Each target is idempotent, follows the `mk/` house style, and writes a receipt to `artifacts/forward_pilot/`.

---

## 8. FORWARD-specific code surface (what we add to `server/`)

Minimal — we're applying the existing substrate to a new input shape.

```
server/
  api/
    pilot_forward_routes.py        # NEW  ~200 LoC (§5 #2 above)
    pilot_node_routes.py           # NEW  ~30 LoC   (§5 #1 above)
  timeline/
    forward_pro_builder.py         # NEW  ~300 LoC
                                   # - normalize FORWARD PRO JSON/Parquet into PTV events
                                   # - canonical_id: f"pro:{instrument}:{domain}:{date}"
                                   # - status_flags: {haq2_mcid_crossed, vas_mcid_crossed}
                                   # - connascence edges: pro_shift, flare_window
                                   # - delegates to existing PTV builder for commit
  eoh/
    forward_flare_detector.py      # NEW  ~400 LoC
                                   # - PRO-composite flare per REPORT_FORWARD_PILOT_DATA_REQUEST §4.2
                                   # - HAQ-II ≥ 0.22 worsening + VAS pain ≥ 20 + anchor
                                   # - emits UC via the Bayesian module (STRATEGY_BAYESIAN_PTV_UC)
                                   # - NO labs / imaging references (FORWARD ceiling)
scripts/
  forward_pilot_smoke.py           # NEW  ~150 LoC
                                   # - end-to-end: seeds 1 synthetic patient from
                                   #   artifacts/forward_exemplar_5pt/ptv_synth_P1*
                                   # - drives forward_ingest → PTV build → flare detect → UC emit
                                   # - asserts receipts exist; asserts zero OpenAI calls
```

**~1,100 LoC total.** No existing endpoint changes. No frontend changes required for Phase 1 of the pilot (data in, UC reports out via the existing dashboard — the "Your Timeline" view already reads from PTV and analytics, both of which work unchanged).

---

## 9. The FORWARD ceiling — enforced in code, not just in comment blocks

`REPORT_FORWARD_KALEB_MICHAUD_PREP` §A.4 tells us: *"Respect the FORWARD ceiling in code. Feature builders for FORWARD should fail fast if asked for a LOINC."*

Concrete enforcement:

```python
# server/timeline/forward_pro_builder.py  (sketch)
FORWARD_ALLOWED_EVENT_TYPES = {"pro", "medication", "therapy_episode",
                               "flare", "clinical_note", "symptom"}
FORWARD_FORBIDDEN_ENTITY_PREFIXES = ("loinc:", "snomed_procedure:", "cpt:",
                                     "biosample:", "omics:")

def validate_forward_event(evt: dict) -> None:
    if evt["event_type"] not in FORWARD_ALLOWED_EVENT_TYPES:
        raise ValueError(
            f"FORWARD ceiling: event_type={evt['event_type']!r} not in scope. "
            "FORWARD does not collect labs/imaging/biosamples; refusing to build."
        )
    for k in evt.get("entity_keys", []):
        if any(k.startswith(p) for p in FORWARD_FORBIDDEN_ENTITY_PREFIXES):
            raise ValueError(
                f"FORWARD ceiling: entity_key={k!r} is outside FORWARD's data surface."
            )
```

If someone accidentally pushes labs into the FORWARD stream, the builder fails fast with a human-readable message citing the report. This is the discipline Andras flagged.

---

## 10. Phased rollout

### Phase 0 — Handshake (same day, 2 hours)

- [ ] Mac: stash artifacts, confirm clean `main`, tag `v-forward-pilot-pre-deploy`.
- [ ] 4090: `apt install` prereqs, Postgres 16 up, pgvector, ufw.
- [ ] Run `pg_dump` pipeline (§3.4). Verify MANIFEST.
- [ ] `rsync` dump directory to 4090.
- [ ] Restore (§3.5). Integrity diff on MANIFEST.
- [ ] Run `make forward-pilot-embed-slice` once. Confirm `embedding_local IS NOT NULL` coverage ≥ 99 % on the slice.

**Gate:** `psql portalnode -c "SELECT source, COUNT(*) FILTER (WHERE embedding_local IS NOT NULL) FROM public.rag_corpus GROUP BY source"` returns all-non-zero on the rheum sources.

### Phase 1 — Services up (same day, 2 hours)

- [ ] 4090: deploy `/opt/portalnode/PortalVision`, run `scripts/SETUP_BEATING_HEART.sh`, write `.env.portalnode`.
- [ ] Install systemd units for fastapi / ollama / ocrforge.
- [ ] `curl http://192.168.0.245:8000/api/health` returns 200.
- [ ] `curl http://192.168.0.245:8000/api/pilot/node_info` returns `{node: "portalnode-0", ...}`.
- [ ] Mac: add `pilot.conf` to nginx. `nginx -t && nginx -s reload`.
- [ ] From outside: `curl -H "Accept: application/json" https://2ndopinionmd.ai/api/pilot/node_info` returns 200 through the proxy.

**Gate:** End-to-end health check from public DNS down to the 4090 Postgres.

### Phase 2 — Synthetic validation (next day, 1 day)

- [ ] `make forward-pilot-mkg-pro` — ingest PROMIS / HAQ-II / RAPID3 / MDHAQ item defs.
- [ ] Run `scripts/forward_pilot_smoke.py` using `artifacts/forward_exemplar_5pt/ptv_synth_P1_early_responder.json` as input.
- [ ] Assert: patient_graph_vision row created; `metadata.pro.source = "forward_synthetic"`; `metadata.synthetic = true`.
- [ ] Flare detector emits 1 UC on P2 (escalation_single_flare), 0 UC on P1 (early_responder). Confirm math matches `STRATEGY_BAYESIAN_PTV_UC`.
- [ ] Receipt count ≥ expected minimum (1 per OGrE mutation, 1 per UC emission).
- [ ] Zero outbound HTTP to OpenAI (verify via `tcpdump -i any host api.openai.com`).

**Gate:** All 5 synthetic exemplars ingest cleanly, flare detector produces the expected 0/1/2/1/0 flare counts (matches filename semantics), 100 % receipts present.

### Phase 3 — First FORWARD pull (week of DUA signature, 3–5 days)

- [ ] Receive FORWARD anonymized dataset per DRS §4.1–4.5 (Parquet/CSV).
- [ ] `POST /api/pilot/forward/ingest` with 5 real patients.
- [ ] Manual review: Andras inspects 5 PTV graphs in the dashboard — flare arcs sensible, UC bands reasonable.
- [ ] Iterate on threshold tuning (HAQ-II MCID, VAS anchor window) in `forward_flare_detector.py`.
- [ ] Scale to 50, then 500.

**Gate:** Andras signs off on the first 5; Kaleb's day-to-day contact confirms the ingest report (coverage matrix, missingness audit).

### Phase 4 — Paper-ready deliverables (week 4+)

- [ ] Cohort dashboard — trajectory clusters, flare-arc incidence, baseline phenotype.
- [ ] UC emission samples: 20 de-identified, calibration-metadata-annotated.
- [ ] Methods-note draft (statistical plan for Paper 2).
- [ ] Ingest report auto-regenerates on each new pull.

**Gate:** 500-patient graph lives on PortalNode-0, every edge receipted, zero cloud calls.

---

## 11. Security posture during pilot

| Layer | On Mac | On 4090 |
|---|---|---|
| TLS | Let's Encrypt, auto-renew | not exposed publicly |
| DB | `2ndopinionmd` DB unchanged | `portalnode` DB, local socket only |
| Patient data | none (nginx streams through) | air-gap-ready after initial model pull |
| Outbound HTTP | OpenAI only on legacy Mac routes | **zero** (Ollama + local embedder) |
| FORWARD data surface | never stored here | never written to disk outside Postgres |
| Receipts | existing ProvenanceEngine | same, with `node=portalnode-0` tag |

`POST /api/pilot/forward/ingest` additionally logs `{pilot: "forward", patient_hash: ..., received_at: ..., node: "portalnode-0"}` to the existing encrypted log channel. Nothing PHI-visible in the receipt stream.

---

## 12. What we're NOT doing (decisions stated for the record)

- **Not shipping `rag_corpus` full via pg_dump.** 383 GB, 99 % MIMIC, useless for FORWARD. We slice.
- **Not using OpenAI embeddings for FORWARD.** Cloud call breaks the pitch.
- **Not running Postgres on the LAN.** Local socket only. FastAPI is the only way in.
- **Not duplicating the `2ndopinionmd` DB.** New DB `portalnode`, new namespace, clean slate.
- **Not writing a new frontend.** "Your Timeline" view already reads from PTV/analytics; those endpoints serve the 4090 via the proxy without modification.
- **Not touching the existing Mac `main` deployment.** Pilot is scoped to `/api/pilot/*`. Rollback is a single `nginx -s reload` after removing one file.
- **Not embedding patient events with BGE-base (yet).** `ehr.patient_graph_chart` stays on `all-MiniLM-L6-v2` (384-d) — proven production pattern, short texts don't benefit from 768-d. Only the MKG corpus gets BGE-base.
- **Not implementing Option B (study-specific PRO graph schema) yet.** `REPORT_FORWARD_KALEB_MICHAUD_PREP` §3 recommends Option A for the pilot — PROs as `pro` nodes in the existing PTV. We stay there. Option B is a post-pilot decision.

---

## 13. Open questions (for Dylan + Andras)

1. **Does `dylan@192.168.0.245` have sudo?** If yes, systemd + ufw are free. If no, we run everything under `dylan`'s user with `systemctl --user` and bind to high ports — still works, 10 minutes of config delta.
2. **PostgreSQL major version on the 4090** — if it's already 14 or 15, we downgrade the pg_dump output with `--format=directory` and `pg_restore` with `--no-owner`. Fine either way.
3. **Ollama model inventory on the 4090 right now** — confirm `eoh-llama-8b` is pulled. 70B is Phase 3, not blocking.
4. **ACR/EULAR and PubMed-rheum ingestion sources.** STRATEGY_MKG_LOCAL_EMBEDDINGS §6.3 and REPORT_FORWARD_KALEB_MICHAUD_PREP §Q8 both assume we have these. The ingest is ~2 engineering days. Do we start before DUA (worth it — we need them regardless), or wait?
5. **Pilot PI seed users.** Default proposal: `dylan@2ndopinionmd.ai` (operator), `andras@2ndopinionmd.ai` (PI), plus one test user for Kaleb if he wants to see the dashboard without a DUA. Do we create Kaleb's account with synthetic data only, or defer?
6. **Cloudflare posture.** `upload.2ndopinionmd.ai` is currently grey-cloud (DNS only) per the earlier limit-fix. Do we keep it that way for pilot (large PDF passthrough is cleaner), or orange-cloud once we're sure uploads work? Grey recommended through Phase 3.

---

## 14. What this unlocks (the narrative)

- **For Kaleb / FORWARD:** "The data stays on a single appliance in our lab, airgappable, every inference receipted, PRO-composite flare detection live on your cohort within eight weeks of DUA signature." That is exactly the sentence the agenda PDF (`01_agenda_sent_to_kaleb.pdf`) is asking to hear, backed by a running node they can query.
- **For Andras's governance paper (Paper 1):** Every UC emission on the 4090 carries `node=portalnode-0, model=eoh-llama-8b, retrieval_model=bge-base-en-v1.5, retrieval_backend=local, receipts=[...]` — the "glass-box derivation" claim becomes empirically inspectable.
- **For the RISE pitch:** The exact same appliance pattern. FORWARD becomes the first deployed PortalNode. The VC deck's Q2 2026 milestone ("PortalNode-01 deployed") is literally this.
- **For the Mac:** stays a perfectly fine developer box. No clinical inference pressure on a MacBook. Mobile-first work can proceed in parallel without colliding with the pilot.
- **For cost:** OpenAI embedding cost on FORWARD traffic = $0. All 4090, all the time.

---

## 15. One-liner summary

> The 4090 at `192.168.0.245` becomes `PortalNode-0` — the FORWARD pilot lives there entirely. We ship a **~3.5 GB slice** of the MKG (ontology + guidelines + rheum/canon text — **not** `rag_corpus` in full, **not** MIMIC), re-embed it locally with **BGE-base-en-v1.5** (768-dim, ~4 min on GPU), stand up the **existing** FastAPI + Ollama + OCR Forge on systemd, add **~1,100 LoC** of FORWARD-specific ingest + flare detection, and have the Mac's nginx proxy `/api/pilot/*` to it. The Mac retains HTTPS and the demo path; the 4090 carries the patients.

---

*Filed 2026-04-24. Strategy for FORWARD pilot deployment on the RTX-4090 build — ship a minimal pg_dump (no rag_corpus, no MIMIC), re-embed locally with bge-base at 768-d, run the full existing stack on the 4090 under systemd, Mac is the public edge. Ready for Dylan's execution pass.*
