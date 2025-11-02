SELECT jsonb_build_object(
  'presence', jsonb_build_object(
    'has_rag', EXISTS(SELECT 1 FROM public.rag_corpus WHERE source IN ('icd10cm','icd11'))
  ),
  'icd10cm', jsonb_build_object(
    'rows',     (SELECT COUNT(*) FROM public.rag_corpus WHERE source='icd10cm'),
    'no_embed', (SELECT COUNT(*) FROM public.rag_corpus WHERE source='icd10cm' AND embedding IS NULL),
    'ann',      (SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE indexname ILIKE '%rag_corpus_embedding_ann_icd10cm%'))
  ),
  'icd11', jsonb_build_object(
    'rows',     (SELECT COUNT(*) FROM public.rag_corpus WHERE source='icd11'),
    'no_embed', (SELECT COUNT(*) FROM public.rag_corpus WHERE source='icd11' AND embedding IS NULL),
    'ann',      (SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE indexname ILIKE '%rag_corpus_embedding_ann_icd11%'))
  )
) AS icd_overview;
