CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_who_committee
  ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 200)
  WHERE source='who_committee';
ANALYZE public.rag_corpus;
