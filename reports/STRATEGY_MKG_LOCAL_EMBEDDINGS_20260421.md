# STRATEGY: Local Semantic Search for the MKG (FORWARD / RISE on-prem)

**Date:** 2026-04-21
**Author:** Dylan + Claude (architecture inspection)
**Scope:** How to give on-premise agents (PortalNode-01) semantic search over the Medical Knowledge Graph (`public.rag_corpus`, 500K+ docs) without calling OpenAI at query time, with study-scoped subsets for FORWARD (PROs / pharmacoepidemiology) and RISE (RA flare detection).
**Status:** Proposal — ready for review
**Companion docs:**
- `REPORT_PATIENT_TIMELINE_VISION_ARCHITECTURE_20260301.md` §5c (model choice comparison — prior art)
- `REPORT_PATIENT_TIMELINE_VISION_ARCHITECTURE_APPENSION_20260327.md` (explicit "don't use Ollama for embeddings" decision)
- `server/eoh/patient_timeline_chart.py` (the `PatientTimelineChart` pattern — already in production with `all-MiniLM-L6-v2`)
- `docs/2OPMD_TECHNICAL_ARCHITECTURE.md` (MKG inventory + current retrieval pipeline)

---

## 0. TL;DR

1. **Keep pgvector as the single production vector store.** Do not introduce ChromaDB to production — it would mean two indexes, two sync paths, two auth layers, for zero capability gain. pgvector with HNSW is already faster and is already the system of record.
2. **Add a second embedding column** (`embedding_local vector(768)`) to `public.rag_corpus` alongside the existing `embedding vector(1536)`. Cloud mode keeps using OpenAI's 1536-d column. On-prem mode uses the local 768-d column. Single table, two spaces, choose at query time.
3. **Use `sentence-transformers` in-process for the local column**, not Ollama. Our own prior architecture reports explicitly decided this — in-process avoids an HTTP hop and lets the agent control batch size. Recommended model: `BAAI/bge-base-en-v1.5` (768-d, strong on clinical text) with `all-mpnet-base-v2` as the fallback.
4. **Don't re-embed all 500K docs at once.** Embed **study-scoped subsets first** (FORWARD subset for the Kaleb meeting, RISE subset for the ACR pilot), then backfill the long tail overnight. This gets PortalNode operational in days, not weeks.
5. **ChromaDB has a role — in dev and in sandbox agents.** It's excellent for one-off prototypes, local-first notebooks, and agent memory stores. Use it in `sandbox/` and `scripts/`, keep it out of `server/`.
6. **Cache query embeddings** in `public.query_embedding_cache` so the same clinical query doesn't re-invoke sentence-transformers on every hit.
7. **Every vector has provenance:** `embedding_local_model`, `embedding_local_at`, `embedding_local_version`. No silent model swaps.

Footprint at completion: **one extra pgvector column, one extra HNSW index, one new Makefile module (`mk/32_local_embeddings.mk`), one thin `LocalEmbedder` class mirroring `PatientTimelineChart`'s pattern, no new services, no new ports.**

---

## 1. Clarifying the Starting State

### 1.1 "500GB" vs 500K docs — what's actually in `rag_corpus`

One worth clarifying before the meeting: the RAG corpus is **~500,000 documents**, not 500 GB. At `vector(1536)` with float32 that's roughly **3 GB of embedding data + a few GB of text + indexes** (call it 8–12 GB on disk). A local 768-d rebuild adds ~1.5 GB. This fits comfortably on the 8 TB NVMe in PortalNode-01 with room to spare for patient graphs and model weights.

### 1.2 Current production embedding pipeline

| Layer | Model | Dims | Where |
|---|---|---|---|
| **`public.rag_corpus` document embeddings** | `text-embedding-3-small` (OpenAI) | 1536 | `server/scripts/embed_rag_corpus.py` |
| **Query-time embedding** | `text-embedding-3-small` (OpenAI) | 1536 | `server/api/embeddings.py` |
| **Index** | ivfflat (200 lists, 8 probes) | cosine `<=>` / `<#>` | `mk/19_who.mk`, `mk/20_cdc.mk`, `mk/21_va.mk` (per-source ANN indexes) |
| **Fusion** | RRF over ANN + BM25 (tsvector) | — | `server/vectordb/hybrid_query.py` |
| **Patient graph chart** | `sentence-transformers/all-MiniLM-L6-v2` | 384 | `server/eoh/patient_timeline_chart.py`, `ehr.patient_graph_chart` |

Current sources in `rag_corpus.source` (from `mk/` modules): `nice`, `cks`, `who_eml`, `who_committee`, `cdc_opioid`, `va_guidelines`, `ethos_model`, `pubmd`, `snomed`, `icd10cm`, `icd11`, `loinc`, `rxnorm`, `orphanet`, `hpo`, `disgenet`, `gwas`, `clinvar`, `clingen`, `panelapp`, `neurolex`, `chv`, plus the MIMIC note shards.

### 1.3 The on-prem constraint

PortalNode-01 is **air-gapped after initial setup** (the whole reason the RISE deck exists). The existing embedding path breaks the moment we pull the network cable:
- `server/api/embeddings.py` is an `AsyncOpenAI` call — **fails offline**.
- Document embeddings were computed via OpenAI too — they're in the DB, they work for ANN, **but we cannot embed a new query on-prem to search against them.**

Semantic search fundamentally requires query and document embeddings to be in the **same vector space**. That is the entire problem this strategy solves.

---

## 2. Design Principles

1. **Single source of truth (pgvector).** No parallel vector store in production. The whole platform is already built around PostgreSQL; every ingestion Make target already knows how to write to it; pgvector's HNSW is competitive with any dedicated vector DB for our read/write ratio.
2. **Two spaces, one table.** Keep OpenAI 1536-d (cloud mode, existing queries keep working). Add local 768-d (on-prem mode). `EMBED_BACKEND` env var picks the column at query time.
3. **Study-scoped first, corpus-wide later.** Re-embed the subset of `rag_corpus` that FORWARD or RISE actually need, ship, iterate. Don't block on a 500K re-embed.
4. **In-process embeddings.** Use `sentence-transformers` directly, not Ollama's embeddings API. This was already decided in `REPORT_PATIENT_TIMELINE_VISION_ARCHITECTURE_APPENSION_20260327.md` and it's the right call — no HTTP hop, tight batching, deterministic.
5. **Reserve Ollama for LLM inference.** 8B for reasoning, 70B for synthesis, 3.2 for routing. Embeddings are a `pip install sentence-transformers` and one GPU context, not a server.
6. **Provenance on every vector.** Model name, model version, embed_at timestamp, embed input text hash. If we ever change models, we can tell which rows are stale.
7. **Reproducibility.** Make targets, not notebooks. Everything in `mk/`. Subset views as materialized views we can rebuild on demand.

---

## 3. The Schema Change

### 3.1 Add the local embedding column

```sql
-- 1. Add the second embedding column (non-breaking; existing queries continue)
ALTER TABLE public.rag_corpus
  ADD COLUMN IF NOT EXISTS embedding_local       vector(768),
  ADD COLUMN IF NOT EXISTS embedding_local_model TEXT,
  ADD COLUMN IF NOT EXISTS embedding_local_at    TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS embedding_local_hash  TEXT;  -- sha256 of (title||'\n\n'||text) at embed time

-- 2. HNSW index on the local column (HNSW is better than ivfflat for write-heavy,
--    and we will be rewriting this column as we tune models)
CREATE INDEX IF NOT EXISTS rag_corpus_embedding_local_hnsw
  ON public.rag_corpus
  USING hnsw (embedding_local vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- 3. Source-scoped partial indexes for the FORWARD and RISE studies (smaller index, faster scan)
CREATE INDEX IF NOT EXISTS rag_corpus_embedding_local_forward
  ON public.rag_corpus
  USING hnsw (embedding_local vector_cosine_ops)
  WITH (m = 16, ef_construction = 64)
  WHERE source IN (
    'nice','cks','va_guidelines','pubmd','ethos_model',
    'diagrules','acr_eular','rxnorm','loinc','hpo'
  );

CREATE INDEX IF NOT EXISTS rag_corpus_embedding_local_rise
  ON public.rag_corpus
  USING hnsw (embedding_local vector_cosine_ops)
  WITH (m = 16, ef_construction = 64)
  WHERE source IN (
    'nice','acr_eular','diagrules','va_guidelines','rxnorm','loinc',
    'ethos_model','pubmd'
  );
```

### 3.2 Materialized views for study-scoped retrieval

```sql
-- FORWARD subset: rheumatology-relevant ontologies + PRO instrument metadata +
-- rheum guidelines. Refresh cadence: weekly (whenever mk/ adds new docs).
CREATE MATERIALIZED VIEW IF NOT EXISTS public.rag_corpus_forward AS
SELECT id, source, source_id, title, text,
       embedding, embedding_local, ts, meta
FROM public.rag_corpus
WHERE source IN (
  'nice','cks','va_guidelines','acr_eular','diagrules',
  'ethos_model','pubmd','rxnorm','loinc','hpo',
  'pro_instruments'   -- new, see §6
)
  AND embedding_local IS NOT NULL;

CREATE INDEX IF NOT EXISTS rag_corpus_forward_hnsw
  ON public.rag_corpus_forward
  USING hnsw (embedding_local vector_cosine_ops);

-- RISE subset: same pattern, RA/autoimmune focused.
CREATE MATERIALIZED VIEW IF NOT EXISTS public.rag_corpus_rise AS
SELECT id, source, source_id, title, text,
       embedding, embedding_local, ts, meta
FROM public.rag_corpus
WHERE source IN (
  'acr_eular','diagrules','nice','va_guidelines','ethos_model',
  'pubmd','rxnorm','loinc','hpo'
)
  AND embedding_local IS NOT NULL;

CREATE INDEX IF NOT EXISTS rag_corpus_rise_hnsw
  ON public.rag_corpus_rise
  USING hnsw (embedding_local vector_cosine_ops);
```

### 3.3 Query-embedding cache (critical for agent workloads)

An OGrE agent will ask many similar questions in a session. Don't re-embed the same query twice.

```sql
CREATE TABLE IF NOT EXISTS public.query_embedding_cache (
  query_hash     TEXT PRIMARY KEY,        -- sha256(query||model)
  query_text     TEXT NOT NULL,
  model          TEXT NOT NULL,
  embedding      vector(768) NOT NULL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_used_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  hit_count      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS qec_last_used ON public.query_embedding_cache (last_used_at);
```

A `server/utils/query_embedding_cache.py` wrapper: hit cache → return; miss → embed → insert → return. TTL-based eviction via a Make target.

---

## 4. Model Choice

We've already done this analysis once (`REPORT_PATIENT_TIMELINE_VISION_ARCHITECTURE_20260301.md` §5c). Updated for the MKG use case:

| Model | Dims | Size | Speed on 4090 | Medical text quality | Notes |
|---|---|---|---|---|---|
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | 80 MB | very fast | OK for short text | Already in use for `PatientTimelineChart`; too small for guidelines |
| `sentence-transformers/all-mpnet-base-v2` | 768 | 420 MB | fast | Good general; decent medical | Safe default; proven |
| **`BAAI/bge-base-en-v1.5`** | **768** | **440 MB** | **fast** | **Strong on clinical and scientific** | **Recommended primary** |
| `BAAI/bge-large-en-v1.5` | 1024 | 1.3 GB | moderate | Strongest quality | Option for a second pass on dense medical content |
| `nomic-embed-text` via Ollama | 768 | pull once | slower (HTTP) | Good | Adds HTTP hop — not recommended for corpus build |
| `mxbai-embed-large` via Ollama | 1024 | pull once | moderate | Very strong | Same HTTP-hop drawback |
| `pritamdeka/S-PubMedBert-MS-MARCO` | 768 | 420 MB | fast | Excellent on biomedical | Worth benchmarking on a guideline slice |

**Decision matrix:**
- **Primary:** `BAAI/bge-base-en-v1.5` — best quality/size ratio, strong on the kinds of text we actually have (NICE chunks, VA guidelines, ACR/EULAR rules).
- **Fallback / A-B baseline:** `all-mpnet-base-v2` — because it's been around forever and its failure modes are well understood.
- **Candidate upgrade (Phase 2):** `pritamdeka/S-PubMedBert-MS-MARCO` for the `pubmd` and `diagrules` slices specifically, if the Phase 1 benchmark shows BGE struggling on dense biomedical prose.

**Rule:** keep dimensions = 768 across candidate models so we can swap without schema churn. Only bump to 1024 if the benchmark (§8) shows it matters.

---

## 5. ChromaDB — yes, in the right place

Framing this clearly because the question comes up a lot:

| Question | Answer |
|---|---|
| "Should we run ChromaDB in production on PortalNode alongside pgvector?" | **No.** Two vector stores doubles sync burden, operational surface, and query-path complexity for no capability gain. Pgvector HNSW is already doing what ChromaDB would do. |
| "Should we use ChromaDB in sandbox and agent-scratchpad scripts?" | **Yes.** Excellent Python-native ergonomics, zero ops, persists to a local directory, fits the `sandbox/` and `scripts/` pattern. |
| "Should we use ChromaDB as an **in-process** agent memory layer (per-session vector store spun up and torn down)?" | **Optional.** For an agent that needs a scratchpad of 500–5,000 items scoped to a single reasoning session, ChromaDB's `PersistentClient(path=...)` is fine. But `numpy + sentence-transformers` (the `PatientTimelineChart` pattern) is even lighter and already present — prefer it for consistency. |

**Concrete policy:**
- `server/` (production) → pgvector only.
- `sandbox/`, `scripts/`, notebooks → ChromaDB allowed for exploration, explicitly not for anything an agent in production depends on.
- Any ChromaDB index that becomes useful graduates to a pgvector table via a `mk/` target.

---

## 6. Study-Scoped Subset Corpora — the FORWARD and RISE Plan

This is the actual path to the Kaleb meeting deliverable. We do **not** need all 500K rows re-embedded to give FORWARD a working on-prem semantic search. We need the ~20–40K rows relevant to rheumatology PROs + guidelines + Ethos canon.

### 6.1 FORWARD subset target (for the longitudinal PRO study)

| Slice | Source tag | Est. rows | Why |
|---|---|---|---|
| NICE rheum + related guidelines | `nice` (filtered by meta.topic) | ~5–8k | RA, PsA, AS, SLE, fibromyalgia, polymyalgia |
| VA/DoD guidelines (pain, MSK) | `va_guidelines` | ~1k | Chronic pain, PTSD (PRO-adjacent) |
| ACR/EULAR diagnostic rules | `acr_eular`, `diagrules` | ~2–5k | Core classification criteria for the study cohort |
| Ethos of Health canon | `ethos_model` | ~2k | Our own reasoning framework; needs to be locally retrievable |
| PubMed abstracts (rheum subset) | `pubmd` filtered by MeSH | ~5–15k | Evidence base; filter to last 10y |
| RxNorm (DMARDs, biologics, steroids) | `rxnorm` filtered | ~3–5k | Drug-response correlation targets |
| LOINC (rheum labs + PRO T-scores) | `loinc` filtered | ~2–3k | ESR, CRP, anti-CCP, RF, PROMIS panel codes |
| HPO (rheumatology phenotypes) | `hpo` filtered | ~1–2k | Symptom-level crosswalks |
| **NEW: PRO instruments** | `pro_instruments` | ~500 | PROMIS domains, HAQ-II, RAPID3, MDHAQ, PGA item definitions + MCID thresholds |
| **Total FORWARD slice** | | **~22–40k rows** | **~30–50 MB embeddings at 768-d** |

### 6.2 RISE subset target (for the computable flare detection pilot)

Similar shape, tighter to RA/autoimmune flare signatures. `acr_eular`, `diagrules`, `nice` (RA-only), `va_guidelines`, `ethos_model`, `pubmd` (RA flare MeSH), `rxnorm` (DMARDs + biologics), `loinc` (RA labs), `hpo` (autoimmune phenotypes). **~15–25k rows**.

### 6.3 The `pro_instruments` source (new, for FORWARD)

A new `mk/XX_pro_instruments.mk` module that ingests:
- PROMIS item bank definitions (domains, T-score → raw-score tables, MCID thresholds)
- HAQ-II items
- RAPID3 items
- MDHAQ fragments
- Mappings to LOINC panel codes

Each instrument item becomes a `rag_corpus` row with `source='pro_instruments'`, `meta={'instrument': 'PROMIS', 'domain': 'Pain Interference', 'version': '1.0', 'mcid': 3}`. Then it's retrievable like anything else.

This is ~2 days of work and directly unlocks the FORWARD study.

---

## 7. Implementation — Code Layout

### 7.1 New files (minimal surface area)

```
server/
  embeddings/
    __init__.py
    local_embedder.py          # NEW: sentence-transformers wrapper, batched, GPU-aware
    backend.py                 # NEW: EmbeddingBackend enum + get_embedder() factory
    query_embedding_cache.py   # NEW: hit-or-embed with DB-backed cache
  api/
    embeddings.py              # EXISTING: extend to route via get_embedder()
  scripts/
    embed_rag_corpus_local.py  # NEW: sibling of embed_rag_corpus.py, local backend
    embed_rag_slice.py         # NEW: embed a single source tag (FORWARD/RISE subsets)
    bench_embed_quality.py     # NEW: quality regression harness (§8)
mk/
  32_local_embeddings.mk       # NEW: Make targets for backfill + slices + bench
database/sql/
  2026xxxx_add_embedding_local.sql  # schema migration (§3.1)
  2026xxxx_query_embedding_cache.sql (§3.3)
  2026xxxx_rag_corpus_forward_rise_mv.sql (§3.2)
```

### 7.2 `LocalEmbedder` shape (thin wrapper — mirrors `PatientTimelineChart` patterns)

```python
# server/embeddings/local_embedder.py
from __future__ import annotations
import hashlib
from typing import List
import numpy as np

class LocalEmbedder:
    """In-process sentence-transformers embedder.

    Mirrors the lazy-init pattern in PatientTimelineChart. Not a service.
    """
    DEFAULT_MODEL = "BAAI/bge-base-en-v1.5"
    DIM = 768

    def __init__(self, model_name: str = DEFAULT_MODEL, device: str | None = None):
        self.model_name = model_name
        self._device = device  # "cuda", "cpu", or None (auto)
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=self._device)
        return self._model

    def encode(self, texts: List[str], batch_size: int = 64,
               normalize: bool = True) -> np.ndarray:
        model = self._get_model()
        embs = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=normalize,
            show_progress_bar=len(texts) > 200,
            convert_to_numpy=True,
        )
        return embs.astype(np.float32)

    def encode_one(self, text: str) -> np.ndarray:
        return self.encode([text])[0]

    @staticmethod
    def text_hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
```

### 7.3 Backend factory (backend selection)

```python
# server/embeddings/backend.py
import os
from enum import Enum
from typing import Protocol, List
import numpy as np

class EmbeddingBackend(str, Enum):
    OPENAI = "openai"   # cloud mode, 1536-d text-embedding-3-small
    LOCAL  = "local"    # on-prem, 768-d sentence-transformers

class Embedder(Protocol):
    dim: int
    model_name: str
    def encode(self, texts: List[str], **kw) -> np.ndarray: ...
    def encode_one(self, text: str) -> np.ndarray: ...

def get_embedder() -> Embedder:
    backend = EmbeddingBackend(os.getenv("EMBED_BACKEND", "openai").lower())
    if backend is EmbeddingBackend.LOCAL:
        from .local_embedder import LocalEmbedder
        return LocalEmbedder(os.getenv("LOCAL_EMBED_MODEL", LocalEmbedder.DEFAULT_MODEL))
    from .openai_embedder import OpenAIEmbedder
    return OpenAIEmbedder(os.getenv("EMBED_MODEL_QUERY",
                                    os.getenv("EMBED_MODEL", "text-embedding-3-small")))

def embedding_column() -> str:
    """Which pgvector column this backend writes/reads."""
    backend = EmbeddingBackend(os.getenv("EMBED_BACKEND", "openai").lower())
    return "embedding_local" if backend is EmbeddingBackend.LOCAL else "embedding"
```

All existing RAG query code calls `embedding_column()` once, substitutes it into the SQL, and works unchanged. One code path, two backends.

### 7.4 `server/vectordb/hybrid_query.py` — the minimum change

```python
# Before:
# SELECT id, ... FROM rag_corpus ORDER BY embedding <=> $1::vector LIMIT $2;

# After:
col = embedding_column()  # "embedding" or "embedding_local"
sql = f"SELECT id, ... FROM rag_corpus ORDER BY {col} <=> $1::vector LIMIT $2"
```

No logic change. Column is static-safe (enum-driven, not user-controlled).

---

## 8. Quality Regression — the Step We Don't Skip

Before we ship local embeddings to anyone, we must prove they don't regress retrieval quality vs the OpenAI baseline on our actual corpus.

### 8.1 Benchmark harness (`server/scripts/bench_embed_quality.py`)

- Fixed set of **50 clinical queries** drawn from real EoHD sessions and the VC-deck examples ("Why hasn't his MG responded to treatment?", "flare risk for RA patient on methotrexate", etc.).
- For each query: run top-20 retrieval with `embedding` (OpenAI 1536-d) and `embedding_local` (candidate model).
- Compute: Recall@10, Recall@20 overlap, NDCG@10 treating OpenAI top-10 as proxy-gold, plus spot-check of top-5 by a human.
- Report delta per source tag (is `bge-base` worse on `nice` than on `ethos_model`?).

### 8.2 Pass criteria

- Recall@10 overlap ≥ 0.6 against the OpenAI baseline on the rheum-relevant query set.
- No single source tag with < 0.5 overlap (flag for model A/B or dedicated medical-tuned model).
- Qualitative: top-1 for ≥ 40/50 queries is "clearly on-topic" to a clinician (Andras-reviewable).

### 8.3 What we do if it fails

- Try `pritamdeka/S-PubMedBert-MS-MARCO` on the failing source tags.
- Consider dim upgrade to `bge-large` (1024-d) — schema accommodates (we'd add `embedding_local_1024` as a second column).
- If a specific source is irredeemable, keep it on OpenAI for cloud queries and exclude it from the on-prem subset with a `meta.on_prem_excluded=true` flag.

---

## 9. Makefile Integration (`mk/32_local_embeddings.mk`)

Follows the house style. Every target is idempotent, dry-run-safe, and reports rows touched.

```make
# =========================
# 32) Local embeddings (sentence-transformers) for on-prem semantic search
# =========================

PY   ?= server/venv312/bin/python
PSQL ?= psql "$${SYNC_DATABASE_URL:-postgresql://2ndopinionmd@localhost:5432/2ndopinionmd}"

LOCAL_EMBED_MODEL ?= BAAI/bge-base-en-v1.5
LOCAL_EMBED_BATCH ?= 128

# -----------------------------------------------------------
# Schema
# -----------------------------------------------------------
local-embed-schema:
	@$(PSQL) -f database/sql/2026xxxx_add_embedding_local.sql
	@$(PSQL) -f database/sql/2026xxxx_query_embedding_cache.sql

local-embed-mv:
	@$(PSQL) -f database/sql/2026xxxx_rag_corpus_forward_rise_mv.sql

local-embed-refresh-mv:
	@$(PSQL) -c "REFRESH MATERIALIZED VIEW CONCURRENTLY public.rag_corpus_forward;"
	@$(PSQL) -c "REFRESH MATERIALIZED VIEW CONCURRENTLY public.rag_corpus_rise;"

# -----------------------------------------------------------
# Embed a single source tag (study-scoped first)
# -----------------------------------------------------------
local-embed-source:  ## SOURCE=nice make local-embed-source
	@test -n "$(SOURCE)" || (echo "Usage: make local-embed-source SOURCE=<tag>"; exit 1)
	@$(PY) server/scripts/embed_rag_slice.py \
	    --source "$(SOURCE)" \
	    --model  "$(LOCAL_EMBED_MODEL)" \
	    --batch  $(LOCAL_EMBED_BATCH) \
	    --column embedding_local

local-embed-forward:
	@for src in nice cks va_guidelines acr_eular diagrules ethos_model pubmd rxnorm loinc hpo pro_instruments; do \
	    $(MAKE) local-embed-source SOURCE=$$src; \
	done
	@$(MAKE) local-embed-refresh-mv

local-embed-rise:
	@for src in acr_eular diagrules nice va_guidelines ethos_model pubmd rxnorm loinc hpo; do \
	    $(MAKE) local-embed-source SOURCE=$$src; \
	done
	@$(MAKE) local-embed-refresh-mv

# -----------------------------------------------------------
# Full backfill (long-running; use after study slices are live)
# -----------------------------------------------------------
local-embed-all:
	@$(PY) server/scripts/embed_rag_corpus_local.py \
	    --model "$(LOCAL_EMBED_MODEL)" \
	    --batch $(LOCAL_EMBED_BATCH) \
	    --where "embedding_local IS NULL"

# -----------------------------------------------------------
# Stats + ANN health
# -----------------------------------------------------------
local-embed-stats:
	@$(PSQL) -c "SELECT source, COUNT(*) AS n, \
	              COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS n_openai, \
	              COUNT(*) FILTER (WHERE embedding_local IS NOT NULL) AS n_local \
	              FROM public.rag_corpus GROUP BY source ORDER BY source;"

local-embed-bench:
	@$(PY) server/scripts/bench_embed_quality.py \
	    --queries server/scripts/bench_queries.json \
	    --k 20
```

---

## 10. Phased Rollout

### Phase 1 — Foundation (week 1, ~3 days of work)

- [ ] Add `embedding_local` column + HNSW index + materialized views (§3)
- [ ] Add `query_embedding_cache` table
- [ ] Ship `LocalEmbedder` + `get_embedder()` factory
- [ ] Thread `embedding_column()` through `server/vectordb/hybrid_query.py` and `server/api/rag_routes.py`
- [ ] Stand up benchmark harness (`bench_embed_quality.py`) with 50 curated queries

**Gate:** Running `EMBED_BACKEND=local` against an empty `embedding_local` column returns clean "no results" (not a crash). Running with a tiny manually-embedded test row returns that row.

### Phase 2 — FORWARD subset (week 1–2, ~2 days)

- [ ] Build the `pro_instruments` ingestion (`mk/XX_pro_instruments.mk`) for PROMIS, HAQ-II, RAPID3, MDHAQ
- [ ] `make local-embed-forward` — embeds the ~22–40K FORWARD slice
- [ ] Benchmark (§8) against OpenAI on the rheum-relevant query set
- [ ] Andras spot-checks top-5 retrieval on 10 PRO-related queries
- [ ] Refresh `rag_corpus_forward` materialized view

**Gate:** Recall@10 ≥ 0.6 vs OpenAI baseline, Andras approves top-1 on ≥ 8/10 queries.

### Phase 3 — On-prem enablement (week 2, ~2 days)

- [ ] Wire `EMBED_BACKEND=local` into PortalNode deployment manifest
- [ ] Remove OpenAI dependency from the on-prem container (or keep it as optional)
- [ ] Integrate with `PatientTimelineChart` patient graphs (they already use `all-MiniLM-L6-v2` — keep that; the **corpus** query path is the one that needs swapping)
- [ ] End-to-end test: agent on PortalNode asks "What does ACR/EULAR say about anti-CCP positivity in early RA?" → local query embedding → pgvector HNSW hit on local column → citation to NICE/ACR section.

**Gate:** Full EoHD session runs on PortalNode with network cable unplugged. Every retrieval cites its source. Receipt log shows `embedding_backend=local, model=BAAI/bge-base-en-v1.5, cache_hit=true|false`.

### Phase 4 — RISE subset + full backfill (week 2–3, background)

- [ ] `make local-embed-rise`
- [ ] Start `make local-embed-all` as an overnight job (estimated ~4–8 hours on a single 4090 for 500K docs at batch 128 with bge-base)
- [ ] Add nightly `local-embed-stats` receipt
- [ ] Add model-version provenance to OGrE mutations (every edge proposal records which embedding model was used for its semantic retrieval)

**Gate:** Full `rag_corpus` has `embedding_local IS NOT NULL` for ≥ 99% of rows. Bench suite runs green on both subsets.

### Phase 5 — Hardening (ongoing)

- [ ] Add `pritamdeka/S-PubMedBert-MS-MARCO` as a second local column (`embedding_pubmed`) for A/B on biomedical-heavy sources.
- [ ] Add `embed_model_version` to the B2B usage events table so enterprise customers can audit which model answered which query.
- [ ] Promote `query_embedding_cache` to include per-tenant namespacing when B2B traffic starts.
- [ ] Add a `model_retire(old_model, new_model)` Make target that re-embeds everything under a new model name with zero downtime (new column → dual-write → cut over → drop old).

---

## 11. Specific Answers to the Questions Asked

> *"Could we use sentence-transformers and ChromaDB?"*

- **Sentence-transformers: yes, absolutely.** It's already in our stack (`PatientTimelineChart`) and both prior architecture reports independently recommended it over Ollama embeddings for the exact same reasons (in-process, no HTTP hop, deterministic batching). Recommendation: `BAAI/bge-base-en-v1.5` as the primary, `all-mpnet-base-v2` as the safety fallback.
- **ChromaDB: yes in dev, no in production.** pgvector already serves the role ChromaDB would serve, on the same database the rest of the app talks to, with a production-grade HNSW. Adding ChromaDB to PortalNode doubles the operational surface for nothing. Use ChromaDB happily in `sandbox/` and throwaway agent scripts.

> *"Can we use the 500GB [sic: 500K docs] rag_corpus with text-embedding-3-small?"*

- **You already are, in cloud mode.** That column is populated and indexed.
- **You cannot use it in air-gapped mode** because you'd need OpenAI to embed queries. The strategy above adds a second column embedded locally so the same corpus serves both modes.
- **We are not re-embedding 500K rows to unblock FORWARD.** We re-embed the ~30K-row rheum-relevant slice first. The long tail backfills overnight, post-meeting.

---

## 12. Provenance — Say What We Did

Every retrieval that feeds a clinical reasoning step gets a receipt:

```json
{
  "retrieval_event": "mkg_semantic_search",
  "embedding_backend": "local",
  "embedding_model": "BAAI/bge-base-en-v1.5",
  "embedding_dim": 768,
  "corpus_slice": "rag_corpus_forward",
  "query_hash": "sha256:…",
  "query_cache_hit": true,
  "top_k": 10,
  "cited_ids": ["rag:nice:NG100#sec4.2", "rag:acr_eular:ra-classif-2010", …],
  "retrieved_at": "2026-04-21T…Z"
}
```

Written to the ProvenanceEngine report. The ARGL module (M67) will refuse to accept a reasoning step whose retrieval provenance is missing or unverifiable. This is not theoretical — `server/eoh/validators.py` already enforces SSE event ordering on the detective; this is the same discipline applied to retrieval.

---

## 13. What This Unlocks

- **FORWARD / Kaleb:** Air-gapped semantic search over rheum guidelines + PRO instruments + Ethos canon on the PortalNode sitting in the FORWARD data center. Agents cite NICE, VA/DoD, and ACR/EULAR without a single outbound HTTP call.
- **RISE:** Same, scoped to RA flare-detection knowledge. The 8B OGrE agent can enrich patient graphs against the rheum subset continuously, overnight, with full receipt trail.
- **Public/internal:** Cloud mode (OpenAI embeddings) continues unchanged for `2ndopinionmd.ai` traffic, so nothing regresses for the consumer path.
- **B2B API (Phase 2 of `STRATEGY_B2B_API_MKG_PTV_20260331.md`):** Tenants pick their backend via API key scope. Enterprise/HIPAA-only tenants get `local`; cost-tolerant tenants get `openai`. Same endpoints.
- **Cost:** Per-query embedding cost drops from `~$0.0001` to `$0`. At 100k queries/month (the RISE deck's benchmark), that's small money by itself — but when combined with the LLM savings (already ~90% per `REPORT_PATIENT_TIMELINE_VISION_ARCHITECTURE_20260301.md` §8), total on-prem query cost is just electricity.

---

## 14. What We're Not Doing (and why)

- **Not building a custom vector DB.** pgvector HNSW on a 4090-adjacent Postgres is more than fast enough for this corpus size.
- **Not using Ollama for embeddings.** Prior architecture decision, revalidated. HTTP hop + batching constraints + no quality benefit over in-process sentence-transformers.
- **Not re-embedding the whole 500K corpus to ship FORWARD.** Study-scoped subsets first. Full backfill is background work.
- **Not dropping the OpenAI column.** Cloud mode is still our primary consumer path. The column stays. Dual-space is the whole point.
- **Not quantizing vectors (yet).** pgvector supports half-precision; we'll consider it if/when we index >5M rows. Not for this corpus.

---

## 15. Open Questions for the Team

1. **BGE vs PubMedBERT on `pubmd`/`diagrules` slices** — I'm calling BGE as primary but the benchmark harness could reverse that. Want to run it before committing.
2. **Do we want a third 1024-d column** (`embedding_local_large` with `bge-large`) for the final-synthesis reduce step on the 70B? Marginal quality gain, clear cost. Probably Phase 5.
3. **Query-embedding cache TTL** — proposal is 30 days with LRU eviction above 100k entries. Open to tighter.
4. **`pro_instruments` ingestion source** — which PROMIS release do we take? (April 2026 if possible.) Do we have licensed access to HAQ-II items, or do we ingest only public-domain instruments? → conversation to have with Nate and FORWARD legal.
5. **Does Kaleb want this ingestion scripted against FORWARD-provided instrument metadata?** If yes, that's a `mk/` target we write with FORWARD; it becomes their control plane for what's retrievable.

---

*Filed 2026-04-21. Strategy for MKG local semantic search — single pgvector table, two spaces, study-scoped subsets first, sentence-transformers in-process, ChromaDB in dev, Ollama for LLM inference only. Ready for review.*
