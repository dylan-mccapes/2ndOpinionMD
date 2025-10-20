-- 17_neurolex_audit.sql
WITH
terms AS (
  SELECT COUNT(*)::int AS n_terms,
         COUNT(*) FILTER (WHERE label IS NULL OR label='')::int AS null_label,
         COUNT(*) FILTER (WHERE iri   IS NULL OR iri='')::int   AS null_iri,
         COUNT(*) FILTER (WHERE definition IS NULL OR definition='')::int AS null_definition,
         COUNT(*) FILTER (WHERE array_length(synonyms,1) IS NULL OR array_length(synonyms,1)=0)::int AS no_synonyms
  FROM ontology.neurolex
),
dupes AS (
  SELECT COALESCE(SUM(cnt) FILTER (WHERE cnt>1),0)::int AS ilx_dupes
  FROM (
    SELECT ilx_id, COUNT(*) AS cnt
    FROM ontology.neurolex
    GROUP BY 1
  ) d
),
ann AS (
  SELECT COUNT(*)::int AS n_ann
  FROM ontology.neurolex_annotations
),
syn_hist AS (
  SELECT COALESCE(array_length(synonyms,1),0)::int AS syn_count, COUNT(*)::int AS n
  FROM ontology.neurolex
  GROUP BY 1
  ORDER BY 1
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
  SELECT split_part(value,':',1) AS prefix, COUNT(*)::int AS n
  FROM ontology.neurolex_annotations
  WHERE prop_label='hasDbXref'
    AND COALESCE(value,'')<>''
  GROUP BY 1
  ORDER BY n DESC, prefix
  LIMIT 20
),
samples AS (
  SELECT ilx_id,
         label,
         COALESCE(array_length(synonyms,1),0)::int AS n_synonyms,
         LEFT(COALESCE(definition,''), 120) AS definition_snip
  FROM ontology.neurolex
  ORDER BY random()
  LIMIT 12
)
SELECT json_build_object(
  'presence', json_build_object(
      'has_terms', (SELECT n_terms>0 FROM terms),
      'has_ann',   (SELECT (n_ann>0) FROM ann),
      'n_terms',   (SELECT n_terms FROM terms),
      'n_ann',     (SELECT n_ann   FROM ann)
  ),
  'totals', json_build_object(
      'terms',          (SELECT n_terms       FROM terms),
      'null_label',     (SELECT null_label    FROM terms),
      'null_iri',       (SELECT null_iri      FROM terms),
      'null_definition',(SELECT null_definition FROM terms),
      'no_synonyms',    (SELECT no_synonyms   FROM terms)
  ),
  'duplicates', json_build_object(
      'ilx_dupes', (SELECT ilx_dupes FROM dupes)
  ),
  'synonyms_hist', (SELECT COALESCE(json_agg(row_to_json(syn_hist)), '[]'::json) FROM syn_hist),
  'top_labels',    (SELECT COALESCE(json_agg(row_to_json(top_labels)), '[]'::json) FROM top_labels),
  'top_annotation_props', (SELECT COALESCE(json_agg(row_to_json(top_props)), '[]'::json) FROM top_props),
  'xref_prefixes', (SELECT COALESCE(json_agg(row_to_json(xref_prefixes)), '[]'::json) FROM xref_prefixes),
  'samples',       (SELECT COALESCE(json_agg(row_to_json(samples)), '[]'::json) FROM samples)
) AS audit;
