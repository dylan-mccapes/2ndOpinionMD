WITH
docs AS (SELECT * FROM guidelines.cdc_docs),
sections AS (SELECT * FROM guidelines.cdc_sections),
rag AS (SELECT * FROM public.rag_corpus WHERE source = 'cdc_opioid'),
xref AS (SELECT * FROM guidelines.section_code_map),
by_tag AS (
  SELECT tag, COUNT(*)::bigint AS n
  FROM (SELECT unnest(tags) AS tag FROM guidelines.cdc_sections) t
  GROUP BY tag
  ORDER BY n DESC, tag ASC
),
by_rec AS (
  SELECT rec_number, COUNT(*)::bigint AS n
  FROM guidelines.cdc_sections
  WHERE rec_number IS NOT NULL AND rec_number <> ''
  GROUP BY rec_number
  ORDER BY rec_number ASC
),
by_system AS (
  SELECT system, COUNT(*)::bigint AS n
  FROM guidelines.section_code_map
  GROUP BY system
  ORDER BY n DESC, system ASC
),
idx AS (
  SELECT
    EXISTS (
      SELECT 1 FROM pg_indexes
      WHERE schemaname='guidelines' AND tablename='cdc_sections'
        AND indexdef ILIKE '%USING GIN%' AND indexdef ILIKE '%to_tsvector%text_plain%'
    ) AS cdc_sections_text_gin,
    EXISTS (
      SELECT 1 FROM pg_indexes
      WHERE schemaname='guidelines' AND tablename='cdc_sections'
        AND indexdef ILIKE '%USING gin%' AND indexdef ILIKE '%(tags)%'
    ) AS cdc_sections_tags_gin
),
-- Replace your current ann_idx CTE with this:
ann_idx AS (
  SELECT
    i.indexrelid::regclass::text AS indexname,
    pg_get_indexdef(i.indexrelid)          AS indexdef,
    pg_get_expr(i.indpred, i.indrelid)     AS predicate,
    COALESCE( (regexp_match(pg_get_indexdef(i.indexrelid), 'WITH\s*\(.*lists\s*=\s*([0-9]+).*?\)'))[1]::int
            , NULL)                         AS lists
  FROM pg_index i
  JOIN pg_class t   ON t.oid = i.indrelid
  JOIN pg_namespace n ON n.oid = t.relnamespace
  WHERE n.nspname = 'public'
    AND t.relname = 'rag_corpus'
    AND pg_get_indexdef(i.indexrelid) ILIKE '%USING ivfflat%'
    AND (pg_get_expr(i.indpred, i.indrelid) ILIKE '%source = ''cdc_opioid''%'
         OR pg_get_expr(i.indpred, i.indrelid) ILIKE '%source=''cdc_opioid''%')
  LIMIT 1
)
SELECT
  jsonb_build_object(
    'has_docs',        (SELECT COUNT(*)>0 FROM docs),
    'has_sections',    (SELECT COUNT(*)>0 FROM sections),
    'has_rag',         (SELECT COUNT(*)>0 FROM rag),
    'has_xref',        (SELECT COUNT(*)>0 FROM xref)
  ) AS presence,
  jsonb_build_object(
    'docs',                 (SELECT COUNT(*) FROM docs),
    'sections',             (SELECT COUNT(*) FROM sections),
    'sections_empty',       (SELECT COUNT(*) FROM sections WHERE text_plain IS NULL OR length(text_plain)=0),
    'sections_no_heading',  (SELECT COUNT(*) FROM sections WHERE COALESCE(heading,'')=''),
    'sections_with_rec',    (SELECT COUNT(*) FROM sections WHERE COALESCE(rec_number,'')<> ''),
    'rag_rows',             (SELECT COUNT(*) FROM rag),
    'rag_no_embed',         (SELECT COUNT(*) FROM rag WHERE embedding IS NULL),
    'xref_mappings',        (SELECT COUNT(*) FROM xref),
    'xref_sections_mapped', (SELECT COUNT(DISTINCT section_id) FROM xref)
  ) AS totals,
  (SELECT jsonb_agg(x) FROM by_tag    x) AS by_tag,
  (SELECT jsonb_agg(x) FROM by_rec    x) AS by_rec,
  (SELECT jsonb_agg(x) FROM by_system x) AS by_system,
  (SELECT jsonb_build_object(
      'cdc_sections_text_gin', (SELECT cdc_sections_text_gin FROM idx),
      'cdc_sections_tags_gin', (SELECT cdc_sections_tags_gin FROM idx),
      'rag_cdc_ann',           (SELECT COUNT(*)>0 FROM ann_idx),
      'rag_cdc_ann_name',      (SELECT indexname FROM ann_idx),
      'rag_cdc_ann_lists',     (SELECT lists FROM ann_idx)
   )) AS indexes,
  jsonb_build_object(
    'rag_rows',       (SELECT COUNT(*) FROM rag),
    'rag_no_embed',   (SELECT COUNT(*) FROM rag WHERE embedding IS NULL),
    'rag_embed_pct',  CASE WHEN (SELECT COUNT(*) FROM rag)=0
                           THEN 0
                           ELSE round(
                             100.0 * (SELECT COUNT(*) FROM rag WHERE embedding IS NOT NULL)::numeric
                             / (SELECT COUNT(*) FROM rag)
                           , 2)
                      END
  ) AS embed;
