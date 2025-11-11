-- database/sql/mimic_keys.sql
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname='public' AND indexname='rag_corpus_src_id_uniq_idx'
  ) THEN
    CREATE UNIQUE INDEX rag_corpus_src_id_uniq_idx
      ON public.rag_corpus(source, source_id);
  END IF;
END$$;

