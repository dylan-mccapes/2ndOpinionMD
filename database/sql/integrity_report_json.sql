-- JSON integrity snapshot (single JSON row)
SELECT jsonb_build_object(
  'db', jsonb_build_object(
    'size_bytes', pg_database_size(current_database()),
    'size_pretty', pg_size_pretty(pg_database_size(current_database()))
  ),
  'rag', jsonb_build_object(
    'total', (SELECT count(*) FROM public.rag_corpus),
    'no_embed', (SELECT count(*) FROM public.rag_corpus WHERE embedding IS NULL),
    'by_source', (
      SELECT jsonb_object_agg(source, cnt)
        FROM (SELECT source, count(*) AS cnt FROM public.rag_corpus GROUP BY 1) s
    )
  ),
  'guidelines', jsonb_build_object(
    'cdc_docs', (SELECT count(*) FROM guidelines.cdc_docs),
    'cdc_sections', (SELECT count(*) FROM guidelines.cdc_sections),
    'va_docs', CASE WHEN to_regclass('guidelines.va_docs') IS NULL THEN 0
                    ELSE (SELECT count(*) FROM guidelines.va_docs) END,
    'va_sections', CASE WHEN to_regclass('guidelines.va_sections') IS NULL THEN 0
                        ELSE (SELECT count(*) FROM guidelines.va_sections) END
  ),
  'xref', jsonb_build_object(
    'cdc_section_codes', CASE WHEN to_regclass('guidelines.v_cdc_section_codes') IS NULL THEN 0
                              ELSE (SELECT count(*) FROM guidelines.v_cdc_section_codes) END,
    'va_section_codes', CASE WHEN to_regclass('guidelines.v_va_section_codes') IS NULL THEN 0
                             ELSE (SELECT count(*) FROM guidelines.v_va_section_codes) END
  ),
  'indexes', jsonb_build_object(
    'rag_corpus_embedding_ann_cdc', EXISTS (
      SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname='rag_corpus_embedding_ann_cdc'
    ),
    'rag_corpus_embedding_ann_va', EXISTS (
      SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname='rag_corpus_embedding_ann_va'
    )
  )
) AS report;

