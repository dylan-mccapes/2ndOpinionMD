-- Safety re-creates
CREATE INDEX IF NOT EXISTS va_sections_tags_idx ON guidelines.va_sections USING GIN (tags);
CREATE INDEX IF NOT EXISTS va_sections_fts_idx  ON guidelines.va_sections USING GIN (ts);
-- ANN (already covered by va-ann target)
CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_va
  ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 64)
  WHERE source='va_guidelines';

