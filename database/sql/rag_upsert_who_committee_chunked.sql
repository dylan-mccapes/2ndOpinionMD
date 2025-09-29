-- Chunk committee sections into ~2k-char blocks for embedding
WITH base AS (
  SELECT s.section_id,
         COALESCE(s.heading,'(untitled)') AS heading,
         s.text
  FROM guidelines.who_committee_sections s
),
para AS (
  SELECT section_id, heading, p, ord
  FROM base
  , regexp_split_to_table(text, E'\n{2,}') WITH ORDINALITY AS t(p, ord)
),
accum AS (
  SELECT section_id, heading, p, ord,
         SUM(length(p)) OVER (PARTITION BY section_id ORDER BY ord) AS runlen
  FROM para
),
grp AS (
  SELECT section_id, heading, p, ord,
         1 + FLOOR( GREATEST(runlen-1,0) / 2000.0 )::int AS chunk_id
  FROM accum
),
chunks AS (
  SELECT section_id, heading, chunk_id,
         string_agg(p, E'\n\n' ORDER BY ord) AS chunk_text
  FROM grp
  GROUP BY section_id, heading, chunk_id
)
INSERT INTO public.rag_corpus (source, title, text, ts)
SELECT 'who_committee',
       'WHO Committee 2025: ' || left(heading, 120) || ' [part '||chunk_id||']',
       chunk_text,
       to_tsvector('english', coalesce(heading,'')||' '||coalesce(chunk_text,''))
FROM chunks c
WHERE length(c.chunk_text) BETWEEN 200 AND 8000
  AND NOT EXISTS (
    SELECT 1 FROM public.rag_corpus rc
    WHERE rc.source='who_committee'
      AND rc.title='WHO Committee 2025: '||left(c.heading,120)||' [part '||c.chunk_id||']'
  );
