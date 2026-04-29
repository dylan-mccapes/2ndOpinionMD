-- Pilot / 4090 ONLY — replaying 05a_rag_corpus_schema.sql.gz after a partial apply fails with
-- "relation rag_corpus already exists". Drop these first, then re-run restore stubs + 05a + 05b
-- (do NOT re-run 01_auth_seed if users/sessions already loaded — duplicates keys).
-- Never run on the Mac origin MKG.

DROP TABLE IF EXISTS public.rag_corpus_chunks CASCADE;
DROP TABLE IF EXISTS public.rag_corpus CASCADE;
