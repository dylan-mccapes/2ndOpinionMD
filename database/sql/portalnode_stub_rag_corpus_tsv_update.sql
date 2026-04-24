-- Mac MKG: BEFORE trigger on public.rag_corpus calls this to refresh ts (tsvector) from title+text.
-- pg_dump 05a includes the trigger but not always the function. Requires public.simple_unaccent (stub before this file in restore order).

CREATE OR REPLACE FUNCTION public.rag_corpus_tsv_update()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.ts := to_tsvector(
    'public.simple_unaccent'::regconfig,
    COALESCE(NEW.title, '') || ' ' || COALESCE(NEW.text, '')
  );
  RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public.rag_corpus_tsv_update() IS 'Pilot stub: matches Mac rag_corpus FTS trigger; uses simple_unaccent. See portalnode4090_restore_mkg.sh.';
