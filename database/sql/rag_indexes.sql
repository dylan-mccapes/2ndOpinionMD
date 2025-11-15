-- Build ANN indexes; do them one-by-one to avoid deadlocks.
-- Tip: run when the cluster is otherwise idle.

-- Optional: bump memory for this session (adjust to your RAM)
-- SET maintenance_work_mem = '4096 MB';

-- HNSW
CREATE INDEX CONCURRENTLY IF NOT EXISTS rag_corpus_embedding_hnsw
ON rag_corpus USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 128)
WHERE embedding IS NOT NULL;

-- Light filters
CREATE INDEX CONCURRENTLY IF NOT EXISTS rag_corpus_source_idx
  ON rag_corpus (source);

CREATE INDEX CONCURRENTLY IF NOT EXISTS rag_corpus_metadata_year_idx
  ON rag_corpus ((metadata->>'year'))
  WHERE source = 'pubmd';

