-- database/sql/chv_loaders.sql
CREATE SCHEMA IF NOT EXISTS ontology;

-- incorrect mappings
CREATE TABLE IF NOT EXISTS ontology.chv_incorrect_map (
  term_lower TEXT NOT NULL,
  cui        TEXT NOT NULL,
  term       TEXT,
  PRIMARY KEY (term_lower, cui)
);
CREATE INDEX IF NOT EXISTS chv_incorrect_cui_idx ON ontology.chv_incorrect_map(cui);

-- ngrams
CREATE TABLE IF NOT EXISTS ontology.chv_ngrams (
  term TEXT NOT NULL,
  cui  TEXT NOT NULL,
  PRIMARY KEY (term, cui)
);
CREATE INDEX IF NOT EXISTS chv_ngrams_term_trgm ON ontology.chv_ngrams USING gin (term gin_trgm_ops);
CREATE INDEX IF NOT EXISTS chv_ngrams_cui_idx  ON ontology.chv_ngrams(cui);

-- Expect psql variables: PROJECT_ROOT, STOP, INCOR, NGRAMS

\echo [CHV loaders] Using:
\echo   PROJECT_ROOT=:PROJECT_ROOT
\echo   STOP        =:STOP
\echo   INCOR       =:INCOR
\echo   NGRAMS      =:NGRAMS

\cd :PROJECT_ROOT
BEGIN;

-- ===== STOP CUIs (1st column is CUI; header present) =====
CREATE SCHEMA IF NOT EXISTS ontology;
CREATE TABLE IF NOT EXISTS ontology.chv_stop_cui (cui TEXT PRIMARY KEY);

DROP TABLE IF EXISTS chv_stop_raw;
CREATE TEMP TABLE chv_stop_raw (cui TEXT, note TEXT);

\copy chv_stop_raw FROM :'STOP' WITH (FORMAT csv, DELIMITER E'\t', HEADER true, NULL '', QUOTE E'\b')

TRUNCATE ontology.chv_stop_cui;
INSERT INTO ontology.chv_stop_cui(cui)
SELECT DISTINCT UPPER(TRIM(cui))
FROM chv_stop_raw
WHERE UPPER(TRIM(cui)) ~ '^C[0-9]{7}$'
ON CONFLICT DO NOTHING;

-- ===== Incorrect mappings (header: CUI, UMLS_PREF, INCORRECT) =====
CREATE TABLE IF NOT EXISTS ontology.chv_incorrect_map (
  term_lower TEXT NOT NULL,
  cui        TEXT NOT NULL,
  term       TEXT,
  PRIMARY KEY (term_lower, cui)
);
CREATE INDEX IF NOT EXISTS chv_incorrect_cui_idx ON ontology.chv_incorrect_map(cui);
CREATE INDEX IF NOT EXISTS chv_incorrect_term_cui_idx ON ontology.chv_incorrect_map(term_lower, cui);

DROP TABLE IF EXISTS chv_incorrect_map_raw;
CREATE TEMP TABLE chv_incorrect_map_raw (
  cui        TEXT,
  umls_pref  TEXT,
  incorrect  TEXT
);

\copy chv_incorrect_map_raw FROM :'INCOR' WITH (FORMAT csv, DELIMITER E'\t', HEADER true, NULL '', QUOTE E'\b')

INSERT INTO ontology.chv_incorrect_map (term_lower, term, cui)
SELECT LOWER(BTRIM(incorrect)), NULLIF(BTRIM(incorrect), ''), UPPER(BTRIM(cui))
FROM chv_incorrect_map_raw
WHERE BTRIM(incorrect) <> '' AND UPPER(cui) ~ '^C[0-9]{7}$'
ON CONFLICT DO NOTHING;

-- ===== N-grams (header: N-GRAM, META, MOD, DISPARAGED, MISSPELLED, COMMENT) =====
CREATE TABLE IF NOT EXISTS ontology.chv_ngrams (term TEXT PRIMARY KEY);

DROP TABLE IF EXISTS chv_ngrams_raw;
CREATE TEMP TABLE chv_ngrams_raw (
  ngram       TEXT,
  meta        TEXT,
  mod         TEXT,
  disparaged  TEXT,
  misspelled  TEXT,
  comment     TEXT
);

\copy chv_ngrams_raw FROM :'NGRAMS' WITH (FORMAT csv, DELIMITER E'\t', HEADER true, NULL 'null', QUOTE E'\b')

INSERT INTO ontology.chv_ngrams(term)
SELECT DISTINCT LOWER(BTRIM(ngram))
FROM chv_ngrams_raw
WHERE BTRIM(ngram) <> ''
ON CONFLICT DO NOTHING;

COMMIT;
\echo [CHV loaders] Done.
