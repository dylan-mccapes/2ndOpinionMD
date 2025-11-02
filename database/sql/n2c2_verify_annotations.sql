-- database/sql/n2c2_verify_annotations.sql

-- Presence flags
SELECT
  (to_regclass('text.n2c2_notes') IS NOT NULL)        AS has_notes,
  (to_regclass('text.n2c2_annotations') IS NOT NULL)  AS has_annotations;

-- Core counts (tolerates missing annotations)
WITH
n AS (SELECT COUNT(*)::bigint AS notes FROM text.n2c2_notes),
e AS (
  SELECT COUNT(*)::bigint AS entities
  FROM   text.n2c2_annotations
  WHERE  kind='entity'
), r AS (
  SELECT COUNT(*)::bigint AS relations
  FROM   text.n2c2_annotations
  WHERE  kind='relation'
), a AS (
  SELECT COUNT(*)::bigint AS attributes
  FROM   text.n2c2_annotations
  WHERE  kind='attribute'
)
SELECT 'notes' AS what, notes AS n FROM n
UNION ALL
SELECT 'entities',  COALESCE((SELECT entities FROM e), 0)
UNION ALL
SELECT 'relations', COALESCE((SELECT relations FROM r), 0)
UNION ALL
SELECT 'attributes',COALESCE((SELECT attributes FROM a), 0);

-- Track/split rollup
SELECT track, split,
       COUNT(*)::bigint AS notes,
       SUM(length(note_text))::bigint AS total_chars
FROM text.n2c2_notes
GROUP BY 1,2
ORDER BY 1,2;

-- Orphan check (only if annotations exist) — NOTE: explicit cast on join
DO $$
BEGIN
  IF to_regclass('text.n2c2_annotations') IS NOT NULL THEN
    RAISE NOTICE 'orphans_in_annotations: %',
      (SELECT COUNT(*)
         FROM text.n2c2_annotations a
         LEFT JOIN text.n2c2_notes n
           ON n.note_id::text = a.note_id
        WHERE n.note_id IS NULL);
  END IF;
END$$;

-- Span sanity if annotations exist — NOTE: explicit cast on join
DO $$
BEGIN
  IF to_regclass('text.n2c2_annotations') IS NOT NULL THEN
    RAISE NOTICE 'bad_bounds / mismatched_text: % / %',
      (SELECT COUNT(*)
         FROM text.n2c2_annotations a
         JOIN text.n2c2_notes n
           ON n.note_id::text = a.note_id
        WHERE a.kind='entity'
          AND (a.span_start<0
               OR a.span_end>length(n.note_text)
               OR a.span_start>=a.span_end)),
      (SELECT COUNT(*)
         FROM text.n2c2_annotations a
         JOIN text.n2c2_notes n
           ON n.note_id::text = a.note_id
        WHERE a.kind='entity'
          AND a.span_text IS NOT NULL
          AND substring(n.note_text FROM a.span_start+1 FOR (a.span_end-a.span_start))
              IS DISTINCT FROM a.span_text);
  END IF;
END$$;
