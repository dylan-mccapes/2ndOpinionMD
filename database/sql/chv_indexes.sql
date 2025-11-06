-- database/sql/chv_indexes.sql
-- Build per-source ANN + partial GIN(ts) for CHV

CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_chv
ON public.rag_corpus
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 256)
WHERE source='chv';

CREATE INDEX IF NOT EXISTS rag_corpus_ts_chv_gin
ON public.rag_corpus
USING GIN (ts)
WHERE source='chv';

ANALYZE public.rag_corpus;
