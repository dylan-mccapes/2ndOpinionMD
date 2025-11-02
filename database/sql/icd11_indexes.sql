
CREATE INDEX IF NOT EXISTS rag_corpus_ts_gin
ON public.rag_corpus
USING gin(ts);

CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_icd11
ON public.rag_corpus
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100)
WHERE source = 'icd11' AND embedding IS NOT NULL;
