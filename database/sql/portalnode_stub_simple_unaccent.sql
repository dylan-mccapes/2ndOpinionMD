-- Mac MKG defines public.simple_unaccent for rag_corpus FTS (GIN on to_tsvector(...)).
-- pg_dump 05a includes the index DDL but not necessarily this TEXT SEARCH CONFIGURATION.
-- Apply before 05a_rag_corpus_schema.sql.gz (restore script order).

CREATE EXTENSION IF NOT EXISTS unaccent;

DO $do$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_ts_config c
    JOIN pg_namespace n ON n.oid = c.cfgnamespace
    WHERE n.nspname = 'public' AND c.cfgname = 'simple_unaccent'
  ) THEN
    RETURN;
  END IF;

  CREATE TEXT SEARCH CONFIGURATION public.simple_unaccent ( COPY = pg_catalog.simple );

  ALTER TEXT SEARCH CONFIGURATION public.simple_unaccent
    ALTER MAPPING FOR asciihword, asciiword, hword, hword_asciipart, hword_numpart, hword_part,
                      numhword, numword, sfloat, word
    WITH unaccent, simple;
END
$do$;

COMMENT ON TEXT SEARCH CONFIGURATION public.simple_unaccent IS 'Pilot stub: matches Mac MKG rag_corpus GIN; see portalnode4090_restore_mkg.sh.';
