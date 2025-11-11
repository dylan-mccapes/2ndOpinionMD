-- database/sql/mimic_indexes.sql
-- BM25 GIN over ts per-source
CREATE INDEX IF NOT EXISTS rag_corpus_ts_m4dx_gin   ON public.rag_corpus USING GIN (ts) WHERE source='mimic4_dx';
CREATE INDEX IF NOT EXISTS rag_corpus_ts_m4proc_gin ON public.rag_corpus USING GIN (ts) WHERE source='mimic4_proc';
CREATE INDEX IF NOT EXISTS rag_corpus_ts_m4lab_gin  ON public.rag_corpus USING GIN (ts) WHERE source='mimic4_labitems';
CREATE INDEX IF NOT EXISTS rag_corpus_ts_m3dx_gin   ON public.rag_corpus USING GIN (ts) WHERE source='mimic3_dx';
CREATE INDEX IF NOT EXISTS rag_corpus_ts_m3proc_gin ON public.rag_corpus USING GIN (ts) WHERE source='mimic3_proc';
CREATE INDEX IF NOT EXISTS rag_corpus_ts_m3lab_gin  ON public.rag_corpus USING GIN (ts) WHERE source='mimic3_labitems';

-- Helpful TRGM on title
CREATE INDEX IF NOT EXISTS rag_corpus_title_trgm ON public.rag_corpus USING GIN (title gin_trgm_ops);

-- ANN per-source (ivfflat on pgvector)
-- tune lists as needed; start with 256, bump for larger sources
CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_m4dx    ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) WITH (lists=256) WHERE source='mimic4_dx';
CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_m4proc  ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) WITH (lists=256) WHERE source='mimic4_proc';
CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_m4lab   ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) WITH (lists=256) WHERE source='mimic4_labitems';
CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_m3dx    ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) WITH (lists=256) WHERE source='mimic3_dx';
CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_m3proc  ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) WITH (lists=256) WHERE source='mimic3_proc';
CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_m3lab   ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) WITH (lists=256) WHERE source='mimic3_labitems';

-- BM25/GiN (ts was computed at upsert time)
CREATE INDEX IF NOT EXISTS rag_corpus_ts_mimic_gin
  ON public.rag_corpus USING GIN (ts)
  WHERE source ILIKE 'mimic%';

-- IVFFLAT — choose lists ~ sqrt(N) (rounded up); use CONCURRENTLY
-- MIMIC-III diagnoses (~651k)
CREATE INDEX CONCURRENTLY IF NOT EXISTS rag_corpus_embedding_ann_m3_dx
  ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 1024)
  WHERE source='mimic3_dx' AND embedding IS NOT NULL;

-- MIMIC-III procedures (~240k)
CREATE INDEX CONCURRENTLY IF NOT EXISTS rag_corpus_embedding_ann_m3_proc
  ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 512)
  WHERE source='mimic3_proc' AND embedding IS NOT NULL;

-- MIMIC-IV diagnoses (very large; often 4–5M rows)
CREATE INDEX CONCURRENTLY IF NOT EXISTS rag_corpus_embedding_ann_m4_dx
  ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 2048)
  WHERE source='mimic4_dx' AND embedding IS NOT NULL;

-- MIMIC-IV labitems (small)
CREATE INDEX CONCURRENTLY IF NOT EXISTS rag_corpus_embedding_ann_m4_labitems
  ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 256)
  WHERE source='mimic4_labitems' AND embedding IS NOT NULL;

ANALYZE public.rag_corpus;
