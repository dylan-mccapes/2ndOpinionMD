-- database/schemas/setup_rxnorm_schema.sql
CREATE SCHEMA IF NOT EXISTS ontology;

-- RxNorm CONSO (from RXNCONSO.RRF; pipe-delimited, no header)
-- Minimal, high-signal columns for search/RAG
CREATE TABLE IF NOT EXISTS ontology.rxnorm_conso (
  rxcui    TEXT NOT NULL,
  tty      TEXT,                  -- Term Type (SCD, SBD, IN, PIN, BN, DF, etc.)
  str      TEXT,                  -- Display string
  sab      TEXT,                  -- Source (RXNORM, MTHSPL, etc.)
  code     TEXT,                  -- Source code
  suppress TEXT,                  -- 'O','E','Y','N' (suppression)
  ingested_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS rxnorm_conso_rxcui_idx ON ontology.rxnorm_conso (rxcui);
CREATE INDEX IF NOT EXISTS rxnorm_conso_tty_idx   ON ontology.rxnorm_conso (tty);
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS rxnorm_conso_str_trgm  ON ontology.rxnorm_conso USING gin (str gin_trgm_ops);

-- RxNorm NDC map (from RXNSAT.RRF where ATN like 'NDC%')
CREATE TABLE IF NOT EXISTS ontology.rxnorm_ndc (
  rxcui TEXT NOT NULL,
  ndc   TEXT NOT NULL,
  atn   TEXT,     -- NDC/NDC11/NDC12/etc.
  sab   TEXT,
  ingested_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (rxcui, ndc)
);
CREATE INDEX IF NOT EXISTS rxnorm_ndc_rxcui_idx ON ontology.rxnorm_ndc (rxcui);

