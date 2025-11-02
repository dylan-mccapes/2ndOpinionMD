DO $$
DECLARE
  has_docs    boolean;
  has_secs    boolean;
  rag_rows    int;
  no_embed    int;
  has_ann     boolean;
BEGIN
  SELECT (SELECT COUNT(*)>0 FROM guidelines.va_docs),
         (SELECT COUNT(*)>0 FROM guidelines.va_sections),
         (SELECT COUNT(*) FROM public.rag_corpus WHERE source='va_guidelines'),
         (SELECT COUNT(*) FROM public.rag_corpus WHERE source='va_guidelines' AND embedding IS NULL)
  INTO has_docs, has_secs, rag_rows, no_embed;

  IF NOT has_docs THEN
    RAISE EXCEPTION 'No VA/DoD docs found';
  END IF;
  IF NOT has_secs THEN
    RAISE EXCEPTION 'No VA/DoD sections found';
  END IF;
  IF rag_rows = 0 THEN
    RAISE EXCEPTION 'No VA/DoD rows in rag_corpus (source=va_guidelines)';
  END IF;
  IF no_embed > 0 THEN
    RAISE EXCEPTION 'VA/DoD rows missing embeddings: %', no_embed;
  END IF;

  SELECT EXISTS(
    SELECT 1
    FROM pg_index i
    JOIN pg_class t ON t.oid=i.indrelid
    JOIN pg_namespace n ON n.oid=t.relnamespace
    WHERE n.nspname='public' AND t.relname='rag_corpus'
      AND pg_get_indexdef(i.indexrelid) ILIKE '%USING ivfflat%'
      AND (pg_get_expr(i.indpred, i.indrelid) ILIKE '%source = ''va_guidelines''%'
           OR pg_get_expr(i.indpred, i.indrelid) ILIKE '%source=''va_guidelines''%')
  ) INTO has_ann;

  IF NOT has_ann THEN
    RAISE EXCEPTION 'ANN index for source=va_guidelines missing';
  END IF;
END $$;

