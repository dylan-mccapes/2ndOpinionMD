BEGIN;

-- Single row per ORPHA: aggregate definition + synonyms + genes + HPO into one text blob
WITH d AS (
  SELECT
    orpha_code,
    name,
    NULLIF(definition,'') AS definition,
    disorder_type,
    status,
    expert_link
  FROM ontology.orphanet_diseases
),
syn AS (
  SELECT orpha_code, array_agg(DISTINCT synonym ORDER BY synonym) AS synonyms
  FROM ontology.orphanet_synonyms
  GROUP BY orpha_code
),
genes AS (
  SELECT orpha_code, array_agg(DISTINCT gene_symbol ORDER BY gene_symbol) AS genes
  FROM ontology.orphanet_gene_links
  GROUP BY orpha_code
),
hpo AS (
  SELECT orpha_code, array_agg(DISTINCT hpo_id ORDER BY hpo_id) AS hpos
  FROM ontology.orphanet_phenotype_links
  GROUP BY orpha_code
),
joined AS (
  SELECT
    d.orpha_code,
    d.name,
    d.definition,
    d.disorder_type,
    d.status,
    d.expert_link,
    COALESCE(s.synonyms, '{}') AS synonyms,
    COALESCE(g.genes,    '{}') AS genes,
    COALESCE(h.hpos,     '{}') AS hpos
  FROM d
  LEFT JOIN syn   s USING (orpha_code)
  LEFT JOIN genes g USING (orpha_code)
  LEFT JOIN hpo   h USING (orpha_code)
),
rows AS (
  SELECT
    'orphanet'::text                       AS source,
    j.orpha_code::text                     AS source_id,
    COALESCE(NULLIF(j.name,''), j.orpha_code)::text AS title,
    -- Compose readable payload
    TRIM(BOTH ' ' FROM
      CONCAT_WS(' | ',
        NULLIF(j.definition,''),
        CASE WHEN array_length(j.synonyms,1) > 0
             THEN 'Synonyms: '||array_to_string(j.synonyms, '; ')
        END,
        CASE WHEN array_length(j.genes,1) > 0
             THEN 'Genes: '||array_to_string(j.genes, ', ')
        END,
        CASE WHEN array_length(j.hpos,1) > 0
             THEN 'HPO: '||array_to_string(j.hpos, ', ')
        END
      )
    )::text                                 AS text,
    jsonb_strip_nulls(jsonb_build_object(
      'type', j.disorder_type,
      'status', j.status,
      'expert_link', j.expert_link,
      'n_synonyms', COALESCE(array_length(j.synonyms,1),0),
      'n_genes',    COALESCE(array_length(j.genes,1),0),
      'n_hpo',      COALESCE(array_length(j.hpos,1),0)
    ))                                       AS metadata
  FROM joined j
)
INSERT INTO public.rag_corpus (source, source_id, title, text, metadata)
SELECT
  source,
  source_id,
  COALESCE(NULLIF(title,''), source_id),
  COALESCE(NULLIF(text,''), title, source_id),
  COALESCE(metadata, '{}'::jsonb)
FROM rows
ON CONFLICT (source, source_id)
DO UPDATE SET
  title    = EXCLUDED.title,
  text     = EXCLUDED.text,
  metadata = EXCLUDED.metadata;

ANALYZE public.rag_corpus;

COMMIT;
