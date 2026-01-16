CREATE SCHEMA IF NOT EXISTS molecular;

-- Base table only; columns are added on-the-fly by the ingester.
CREATE TABLE IF NOT EXISTS molecular.clinvar_summary (
  loaded_at      timestamptz DEFAULT now(),
  source_path    text,
  source_version text
);
