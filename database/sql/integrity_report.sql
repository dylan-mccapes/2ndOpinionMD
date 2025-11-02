-- Human-readable integrity snapshot (one result set)
WITH m AS (
  SELECT 'db'::text section, 'size_pretty'::text metric,
         pg_size_pretty(pg_database_size(current_database()))::text AS value, NULL::text AS extra
  UNION ALL
  SELECT 'db','tables', count(*)::text, NULL
    FROM information_schema.tables
   WHERE table_schema NOT IN ('pg_catalog','information_schema')
  UNION ALL
  SELECT 'rag','rows_total', count(*)::text, NULL
    FROM public.rag_corpus
  UNION ALL
  SELECT 'rag','rows_by_source',
         string_agg(source||':'||cnt, ', ' ORDER BY source), NULL
    FROM (SELECT source, count(*)::text AS cnt
            FROM public.rag_corpus GROUP BY 1) s
  UNION ALL
  SELECT 'rag','rows_no_embedding', count(*)::text, NULL
    FROM public.rag_corpus WHERE embedding IS NULL
  UNION ALL
  SELECT 'guidelines','cdc_docs', count(*)::text, NULL
    FROM guidelines.cdc_docs
  UNION ALL
  SELECT 'guidelines','cdc_sections', count(*)::text, NULL
    FROM guidelines.cdc_sections
  UNION ALL
  SELECT 'guidelines','va_docs',
         CASE WHEN to_regclass('guidelines.va_docs') IS NULL THEN 'MISSING'
              ELSE (SELECT count(*)::text FROM guidelines.va_docs) END, NULL
  UNION ALL
  SELECT 'guidelines','va_sections',
         CASE WHEN to_regclass('guidelines.va_sections') IS NULL THEN 'MISSING'
              ELSE (SELECT count(*)::text FROM guidelines.va_sections) END, NULL
  UNION ALL
  SELECT 'xref','cdc_section_codes',
         CASE WHEN to_regclass('guidelines.v_cdc_section_codes') IS NULL THEN 'MISSING'
              ELSE (SELECT count(*)::text FROM guidelines.v_cdc_section_codes) END, NULL
  UNION ALL
  SELECT 'xref','va_section_codes',
         CASE WHEN to_regclass('guidelines.v_va_section_codes') IS NULL THEN 'MISSING'
              ELSE (SELECT count(*)::text FROM guidelines.v_va_section_codes) END, NULL
  UNION ALL
  SELECT 'index','rag_corpus_embedding_ann_cdc',
         CASE WHEN EXISTS (
           SELECT 1 FROM pg_indexes
            WHERE schemaname='public' AND indexname='rag_corpus_embedding_ann_cdc'
         ) THEN 'present' ELSE 'missing' END, NULL
  UNION ALL
  SELECT 'index','rag_corpus_embedding_ann_va',
         CASE WHEN EXISTS (
           SELECT 1 FROM pg_indexes
            WHERE schemaname='public' AND indexname='rag_corpus_embedding_ann_va'
         ) THEN 'present' ELSE 'missing' END, NULL
)
SELECT section, metric, value, COALESCE(extra,'') AS extra
  FROM m
 ORDER BY section, metric;

