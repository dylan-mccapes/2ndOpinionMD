BEGIN;
CREATE SCHEMA IF NOT EXISTS ontology;

-- Drop whatever "chv_best" currently is (table, view, or matview) without aborting
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='ontology' AND c.relname='chv_best' AND c.relkind='r'
  ) THEN
    EXECUTE 'DROP TABLE ontology.chv_best';
  ELSIF EXISTS (
    SELECT 1 FROM pg_matviews WHERE schemaname='ontology' AND matviewname='chv_best'
  ) THEN
    EXECUTE 'DROP MATERIALIZED VIEW ontology.chv_best';
  ELSIF EXISTS (
    SELECT 1 FROM pg_views WHERE schemaname='ontology' AND viewname='chv_best'
  ) THEN
    EXECUTE 'DROP VIEW ontology.chv_best';
  END IF;
END$$;

CREATE TABLE ontology.chv_best (
  term_lower TEXT NOT NULL,
  term       TEXT NOT NULL,
  cui        TEXT NOT NULL,
  score      REAL NOT NULL,
  method     TEXT NOT NULL DEFAULT 'baseline'
);

-- Build from synonyms, excluding stop CUIs and explicit incorrect map entries
WITH src AS (
  SELECT lower(btrim(s.term)) AS term_lower, s.term, s.cui
  FROM ontology.synonyms s
  WHERE s.source='CHV'
    AND s.term IS NOT NULL AND btrim(s.term) <> ''
    AND s.cui ~ '^C[0-9]{7}$'
    AND NOT EXISTS (SELECT 1 FROM ontology.chv_stop_cui x WHERE x.cui = s.cui)
    AND NOT EXISTS (SELECT 1 FROM ontology.chv_incorrect_map m
                    WHERE m.cui = s.cui AND lower(m.term) = lower(btrim(s.term)))
),
picked AS (
  SELECT DISTINCT ON (term_lower)
         term_lower, term, cui,
         1.0::real AS score, 'exact'::text AS method
  FROM src
  ORDER BY term_lower,
           CASE WHEN position(term_lower IN lower(term))=1 THEN 0 ELSE 1 END,
           length(term), cui
)
INSERT INTO ontology.chv_best(term_lower, term, cui, score, method)
SELECT term_lower, term, cui, score, method
FROM picked;

CREATE INDEX IF NOT EXISTS chv_best_term_idx ON ontology.chv_best(term_lower);
CREATE INDEX IF NOT EXISTS chv_best_cui_idx  ON ontology.chv_best(cui);
COMMIT;
