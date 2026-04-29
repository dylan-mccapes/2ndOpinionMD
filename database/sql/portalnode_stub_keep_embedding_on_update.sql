-- Mac MKG may attach BEFORE UPDATE triggers on public.rag_corpus that call this function.
-- pg_dump -t rag_corpus (05a) can emit trigger DDL without the standalone CREATE FUNCTION.
-- No-op is enough for pilot restore (slice is read-mostly); replace on origin if you need invalidation logic.

CREATE OR REPLACE FUNCTION public.keep_embedding_on_update()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public.keep_embedding_on_update() IS 'Pilot stub: satisfies rag_corpus triggers from 05a; see portalnode4090_restore_mkg.sh.';
