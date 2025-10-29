DO $$
DECLARE
  miss      int;
  ann       boolean;
  no_embed  int;
BEGIN
  -- R1..R12 present?
  SELECT COUNT(*) INTO miss
  FROM (SELECT unnest(ARRAY['R1','R2','R3','R4','R5','R6','R7','R8','R9','R10','R11','R12']) AS rec) req
  LEFT JOIN (
    SELECT DISTINCT rec_number
    FROM guidelines.cdc_sections
    WHERE rec_number IS NOT NULL
  ) have
    ON req.rec = have.rec_number
  WHERE have.rec_number IS NULL;

  -- ANN index exists with predicate on CDC?
  SELECT EXISTS(
    SELECT 1
    FROM pg_index i
    JOIN pg_class t      ON t.oid = i.indrelid
    JOIN pg_namespace n  ON n.oid = t.relnamespace
    WHERE n.nspname='public'
      AND t.relname='rag_corpus'
      AND pg_get_indexdef(i.indexrelid) ILIKE '%USING ivfflat%'
      AND (pg_get_expr(i.indpred, i.indrelid) ILIKE '%source = ''cdc_opioid''%'
           OR pg_get_expr(i.indpred, i.indrelid) ILIKE '%source=''cdc_opioid''%')
  ) INTO ann;

  -- Embeddings complete?
  SELECT COUNT(*) INTO no_embed
  FROM public.rag_corpus
  WHERE source='cdc_opioid' AND embedding IS NULL;

  IF NOT ann THEN
    RAISE EXCEPTION 'ANN index for CDC missing';
  END IF;
  IF no_embed > 0 THEN
    RAISE EXCEPTION 'CDC rows missing embeddings: %', no_embed;
  END IF;
  IF miss > 0 THEN
    RAISE EXCEPTION 'Missing recommendations: %', miss;
  END IF;
END $$;

