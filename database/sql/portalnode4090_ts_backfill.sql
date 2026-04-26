-- Diagnose and backfill public.rag_corpus.ts on the 4090 PortalNode.
--
-- Why this is needed:
--   The ts column is normally populated by a BEFORE INSERT/UPDATE trigger
--   (rag_corpus_tsv_update) using public.simple_unaccent text search config.
--   If rows were loaded via binary COPY from a Mac dump where ts was already
--   populated, the data comes across intact.  But if the dump ts values were NULL
--   (trigger added after original insert, or simple_unaccent not yet configured at
--   dump time), ts will be NULL on the 4090 and all FTS queries return 0 rows.
--
-- Run this once after restore to check + fix:
--   psql -v ON_ERROR_STOP=1 -f database/sql/portalnode4090_ts_backfill.sql
--
-- Safe to re-run: UPDATE WHERE ts IS NULL is a no-op when ts is already set.

-- ── 1. Diagnostics ──────────────────────────────────────────────────────────
\echo '==> rag_corpus ts population check'
SELECT
  count(*)          AS total_rows,
  count(ts)         AS ts_populated,
  count(*) - count(ts) AS ts_null,
  round(100.0 * count(ts) / NULLIF(count(*), 0), 2) AS pct_populated
FROM public.rag_corpus;

\echo '==> ts-null breakdown by source (top 20 sources)'
SELECT source,
       count(*) AS total,
       count(ts) AS populated,
       count(*) - count(ts) AS missing
FROM public.rag_corpus
GROUP BY source
ORDER BY missing DESC, total DESC
LIMIT 20;

-- ── 2. Backfill ts where NULL ────────────────────────────────────────────────
-- Uses public.simple_unaccent (same config the trigger uses) so that
-- existing GIN indexes and queries remain consistent.
-- On a large corpus this may take several minutes; run during low-traffic window.
\echo '==> Backfilling ts where NULL (may take a few minutes on large corpora)'

UPDATE public.rag_corpus
SET ts = to_tsvector(
    'public.simple_unaccent'::regconfig,
    COALESCE(title, '') || ' ' || COALESCE(text, '')
)
WHERE ts IS NULL;

\echo '==> Post-backfill ts population check'
SELECT
  count(*)          AS total_rows,
  count(ts)         AS ts_populated,
  count(*) - count(ts) AS ts_still_null
FROM public.rag_corpus;

-- ── 3. Ensure GIN index exists ───────────────────────────────────────────────
-- A global GIN index over all sources covers the pilot slice without requiring
-- partial per-source indexes.  CONCURRENTLY avoids locking reads; safe on live DB.
\echo '==> Ensuring global GIN index on ts (rag_corpus_ts_gin)'
CREATE INDEX CONCURRENTLY IF NOT EXISTS rag_corpus_ts_gin
  ON public.rag_corpus USING gin (ts);

\echo '==> Done.  TS lane should now return results in mkg_retrieval_harness.py.'
