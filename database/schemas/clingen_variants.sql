CREATE SCHEMA IF NOT EXISTS clingen;

CREATE TABLE IF NOT EXISTS clingen.variant_classifications (
  variation_id     text,         -- if present
  clingen_id       text,         -- if present
  gene_symbol      text,
  hgnc_id          text,
  condition        text,
  mondo_id         text,
  classification   text,         -- Pathogenic/Likely..., Benign/Likely..., VUS, etc.
  last_evaluated   date,
  review_status    text,
  source_url       text,
  raw              jsonb,        -- entire row (normalized header -> value)
  loaded_at        timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS clingen_var_gene_idx
  ON clingen.variant_classifications (gene_symbol);

CREATE INDEX IF NOT EXISTS clingen_var_mondo_idx
  ON clingen.variant_classifications (mondo_id);

CREATE INDEX IF NOT EXISTS clingen_var_raw_gin
  ON clingen.variant_classifications USING GIN (raw);

