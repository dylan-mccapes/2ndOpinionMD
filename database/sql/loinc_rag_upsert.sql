-- Upsert LOINC terms into rag_corpus
-- Requires UNIQUE INDEX on (source, source_id) — ensured by make rag-uniq-index
WITH base AS (
  SELECT
    loinc_num,
    COALESCE(NULLIF(shortname,''), long_common_name) AS title,
    CONCAT_WS(' | ',
      NULLIF(long_common_name,''),
      NULLIF(component,''),
      NULLIF(property,''),
      NULLIF(time_aspct,''),
      NULLIF(system,''),
      NULLIF(scale_typ,''),
      NULLIF(method_typ,''),
      NULLIF(class,'')
    ) AS body
  FROM ontology.loinc_terms
),
prep AS (
  SELECT
    'loinc'::text AS source,
    loinc_num     AS source_id,
    title,
    body          AS text,
    to_tsvector('english', CONCAT_WS(' ', title, body)) AS ts
  FROM base
)
INSERT INTO public.rag_corpus (source, source_id, title, text, ts)
SELECT source, source_id, title, text, ts
FROM prep
ON CONFLICT (source, source_id) DO UPDATE
SET title = EXCLUDED.title,
    text  = EXCLUDED.text,
    ts    = EXCLUDED.ts;
