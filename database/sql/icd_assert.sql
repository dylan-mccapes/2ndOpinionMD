DO $$
DECLARE missing10 int; missing11 int;
BEGIN
  SELECT COUNT(*) INTO missing10 FROM public.rag_corpus WHERE source='icd10cm' AND embedding IS NULL;
  IF missing10 > 0 THEN
    RAISE EXCEPTION 'Some ICD-10-CM rows missing embeddings: %', missing10;
  END IF;

  SELECT COUNT(*) INTO missing11 FROM public.rag_corpus WHERE source='icd11' AND embedding IS NULL;
  -- For now, only warn on ICD-11 if crawl not done yet:
  IF missing11 > 0 THEN
    RAISE NOTICE 'ICD-11 rows missing embeddings: %', missing11;
  END IF;
END$$;
