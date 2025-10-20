-- database/sql/17_neurolex_audit.sql
-- Emits one JSON row with overall + core stats.

WITH
presence AS (
  SELECT
    (to_regclass('ontology.neurolex') IS NOT NULL)        AS has_terms,
    (to_regclass('ontology.neurolex_annotations') IS NOT NULL) AS has_ann,
    COALESCE((SELECT COUNT(*) FROM ontology.neurolex),0)         AS n_terms,
    COALESCE((SELECT COUNT(*) FROM ontology.neurolex_annotations),0) AS n_ann
),
overall AS (
  SELECT
    COUNT(*)::int                                                AS terms,
    COUNT(*) FILTER (WHERE label IS NULL OR label='')::int       AS null_label,
    COUNT(*) FILTER (WHERE iri   IS NULL OR iri='')::int         AS null_iri,
    COUNT(*) FILTER (WHERE definition IS NULL OR definition='')::int AS null_definition,
    COUNT(*) FILTER (WHERE synonyms IS NULL OR array_length(synonyms,1)=0)::int AS no_synonyms
  FROM ontology.neurolex
),
core_src AS (
  SELECT to_regclass('ontology.neurolex_core') IS NOT NULL AS has_core
),
core AS (
  SELECT
    CASE WHEN (SELECT has_core FROM core_src) THEN
      (SELECT COUNT(*)::int FROM ontology.neurolex_core) ELSE 0 END AS terms,
    CASE WHEN (SELECT has_core FROM core_src) THEN
      (SELECT COUNT(*)::int FROM ontology.neurolex_core WHERE definition IS NULL OR definition='') ELSE 0 END AS null_definition,
    CASE WHEN (SELECT has_core FROM core_src) THEN
      (SELECT COUNT(*)::int FROM ontology.neurolex_core WHERE synonyms IS NULL OR array_length(synonyms,1)=0) ELSE 0 END AS no_synonyms
),
dupes AS (
  SELECT COUNT(*)::int AS ilx_dupes
  FROM (
    SELECT ilx_id, COUNT(*) FROM ontology.neurolex GROUP BY 1 HAVING COUNT(*)>1
  ) d
),
syn_hist AS (
  SELECT COALESCE(array_length(synonyms,1),0) AS syn_count, COUNT(*)::int AS n
  FROM ontology.neurolex
  GROUP BY 1
  ORDER BY 1
  LIMIT 60
),
top_labels AS (
  SELECT label, COUNT(*)::int AS n
  FROM ontology.neurolex
  GROUP BY 1
  HAVING COUNT(*)>1
  ORDER BY n DESC, label
  LIMIT 20
),
top_props AS (
  SELECT prop_label, COUNT(*)::int AS n
  FROM ontology.neurolex_annotations
  GROUP BY 1
  ORDER BY n DESC, prop_label
  LIMIT 20
),
xref_prefixes AS (
  -- count prefixes from annotation cross-refs (most informative)
  SELECT split_part(value, ':', 1) AS prefix, COUNT(*)::int AS n
  FROM ontology.neurolex_annotations
  WHERE prop_label='hasDbXref' AND COALESCE(value,'')<>''
  GROUP BY 1
  ORDER BY n DESC, prefix
  LIMIT 20
),
samples AS (
  SELECT
    ilx_id,
    label,
    LEFT(COALESCE(definition,''), 120) AS definition_snip,
    COALESCE(array_length(synonyms,1),0) AS n_synonyms
  FROM ontology.neurolex
  ORDER BY ilx_id
  LIMIT 12
)
SELECT jsonb_build_object(
  'presence',        (SELECT jsonb_build_object('has_terms',has_terms,'has_ann',has_ann,'n_terms',n_terms,'n_ann',n_ann) FROM presence),
  'totals',          (SELECT to_jsonb(overall) FROM overall),
  'core',            (SELECT to_jsonb(core)    FROM core),
  'duplicates',      (SELECT to_jsonb(dupes)   FROM dupes),
  'synonyms_hist',   (SELECT jsonb_agg(jsonb_build_object('syn_count',syn_count,'n',n)) FROM syn_hist),
  'top_labels',      (SELECT jsonb_agg(jsonb_build_object('label',label,'n',n)) FROM top_labels),
  'top_annotation_props', (SELECT jsonb_agg(jsonb_build_object('prop_label',prop_label,'n',n)) FROM top_props),
  'xref_prefixes',   (SELECT jsonb_agg(jsonb_build_object('prefix',prefix,'n',n)) FROM xref_prefixes),
  'samples',         (SELECT jsonb_agg(jsonb_build_object('ilx_id',ilx_id,'label',label,'definition_snip',definition_snip,'n_synonyms',n_synonyms)) FROM samples)
) AS json;
