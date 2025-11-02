WITH
docs AS (SELECT COUNT(*)::int AS n FROM guidelines.va_docs),
secs AS (SELECT COUNT(*)::int AS n FROM guidelines.va_sections),
rag AS (
  SELECT
    COUNT(*)::int AS n,
    COUNT(*) FILTER (WHERE embedding IS NULL)::int AS no_embed
  FROM public.rag_corpus
  WHERE source='va_guidelines'
),
tags AS (
  SELECT t.tag, COUNT(*)::int AS n
  FROM (SELECT unnest(tags) AS tag FROM guidelines.va_sections) t
  GROUP BY 1
  ORDER BY n DESC, tag ASC
),
bydoc AS (
  SELECT doc_slug, COUNT(*)::int AS n
  FROM guidelines.va_sections
  GROUP BY 1
  ORDER BY n DESC, doc_slug ASC
  LIMIT 20
),
ann AS (
  SELECT
    i.indexrelid::regclass::text AS name,
    pg_get_indexdef(i.indexrelid) AS def,
    pg_get_expr(i.indpred, i.indrelid) AS predicate
  FROM pg_index i
  JOIN pg_class t ON t.oid = i.indrelid
  JOIN pg_namespace n ON n.oid = t.relnamespace
  WHERE n.nspname='public' AND t.relname='rag_corpus'
),
rag_va AS (
  SELECT
    EXISTS(
      SELECT 1 FROM ann
      WHERE def ILIKE '%USING ivfflat%'
        AND (
          predicate ILIKE '%source = ''va_guidelines''%'
          OR predicate ILIKE '%source=''va_guidelines''%'
        )
    ) AS has_ann,
    (SELECT name FROM ann
      WHERE def ILIKE '%USING ivfflat%'
        AND (predicate ILIKE '%source = ''va_guidelines''%' OR predicate ILIKE '%source=''va_guidelines''%')
      LIMIT 1) AS ann_name,
    (SELECT NULLIF(regexp_replace(def, '.*lists\\s*=\\s*([0-9]+).*', '\\1'), def)::int
       FROM ann
      WHERE def ILIKE '%USING ivfflat%'
        AND (predicate ILIKE '%source = ''va_guidelines''%' OR predicate ILIKE '%source=''va_guidelines''%')
      LIMIT 1) AS ann_lists
),
va_idx AS (
  SELECT
    EXISTS (
      SELECT 1 FROM pg_indexes
      WHERE schemaname='guidelines' AND tablename='va_sections'
        AND indexdef ILIKE '%USING gin%' AND indexdef ILIKE '%(tags)%'
    ) AS va_sections_tags_gin,
    EXISTS (
      SELECT 1 FROM pg_indexes
      WHERE schemaname='guidelines' AND tablename='va_sections'
        AND indexdef ILIKE '%USING gin%' AND indexdef ILIKE '%TO_TSVECTOR%'
    ) AS va_sections_ts_gin
)
SELECT
  jsonb_build_object(
    'has_docs',     (SELECT n>0 FROM docs),
    'has_sections', (SELECT n>0 FROM secs),
    'has_rag',      (SELECT n>0 FROM rag)
  ) AS presence,
  jsonb_build_object(
    'docs',      (SELECT n FROM docs),
    'sections',  (SELECT n FROM secs),
    'rag_rows',  (SELECT n FROM rag),
    'rag_no_embed', (SELECT no_embed FROM rag)
  ) AS totals,
  (SELECT COALESCE(jsonb_agg(x), '[]'::jsonb) FROM (SELECT * FROM tags) x) AS by_tag,
  (SELECT COALESCE(jsonb_agg(x), '[]'::jsonb) FROM (SELECT * FROM bydoc) x) AS by_doc,
  jsonb_build_object(
    'rag_va_ann',         (SELECT has_ann FROM rag_va),
    'rag_va_ann_name',    (SELECT ann_name FROM rag_va),
    'rag_va_ann_lists',   (SELECT ann_lists FROM rag_va),
    'va_sections_tags_gin', (SELECT va_sections_tags_gin FROM va_idx),
    'va_sections_ts_gin',   (SELECT va_sections_ts_gin FROM va_idx)
  ) AS indexes,
  jsonb_build_object(
    'rag_rows',     (SELECT n FROM rag),
    'rag_no_embed', (SELECT no_embed FROM rag),
    'rag_embed_pct',
      CASE WHEN (SELECT n FROM rag) = 0
           THEN 0.0
           ELSE round(100.0 * ((SELECT n FROM rag) - (SELECT no_embed FROM rag)) / NULLIF((SELECT n FROM rag),0), 2)
      END
  ) AS embed;

