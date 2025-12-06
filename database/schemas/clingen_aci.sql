CREATE SCHEMA IF NOT EXISTS clingen;

-- Fresh install path
CREATE TABLE IF NOT EXISTS clingen.actionability_assertions (
  cohort            text NOT NULL,
  gene_symbol       text,
  hgnc_id           text,
  disease_name      text,
  disease_mondo_id  text,
  assertion         text,
  assertion_type    text,
  domain            text,
  intervention      text,
  outcome           text,
  score             int,
  rationale         text,
  report_date       date,
  source_url        text,
  loaded_at         timestamptz DEFAULT now()
);

-- Upgrade path: ensure all columns exist even if the table was created earlier
ALTER TABLE clingen.actionability_assertions
  ADD COLUMN IF NOT EXISTS assertion_type   text,
  ADD COLUMN IF NOT EXISTS domain           text,
  ADD COLUMN IF NOT EXISTS intervention     text,
  ADD COLUMN IF NOT EXISTS outcome          text,
  ADD COLUMN IF NOT EXISTS score            int,
  ADD COLUMN IF NOT EXISTS rationale        text,
  ADD COLUMN IF NOT EXISTS gene_symbol      text,
  ADD COLUMN IF NOT EXISTS hgnc_id          text,
  ADD COLUMN IF NOT EXISTS disease_name     text,
  ADD COLUMN IF NOT EXISTS disease_mondo_id text,
  ADD COLUMN IF NOT EXISTS assertion        text,
  ADD COLUMN IF NOT EXISTS report_date      date,
  ADD COLUMN IF NOT EXISTS source_url       text;

-- Make all content columns nullable; ACI rows are sometimes missing IDs
ALTER TABLE clingen.actionability_assertions
  ALTER COLUMN gene_symbol       DROP NOT NULL,
  ALTER COLUMN hgnc_id           DROP NOT NULL,
  ALTER COLUMN disease_name      DROP NOT NULL,
  ALTER COLUMN disease_mondo_id  DROP NOT NULL,
  ALTER COLUMN assertion         DROP NOT NULL,
  ALTER COLUMN assertion_type    DROP NOT NULL,
  ALTER COLUMN domain            DROP NOT NULL,
  ALTER COLUMN intervention      DROP NOT NULL,
  ALTER COLUMN outcome           DROP NOT NULL,
  ALTER COLUMN score             DROP NOT NULL,
  ALTER COLUMN rationale         DROP NOT NULL,
  ALTER COLUMN report_date       DROP NOT NULL,
  ALTER COLUMN source_url        DROP NOT NULL;
-- keep cohort NOT NULL; everything else can be sparse in source data

CREATE INDEX IF NOT EXISTS clingen_aci_gene_mondo_idx
  ON clingen.actionability_assertions (cohort, gene_symbol, disease_mondo_id);

CREATE INDEX IF NOT EXISTS clingen_aci_domain_idx
  ON clingen.actionability_assertions (domain);

-- (Re)create the latest-per-(cohort,gene/disease,domain) MV
DROP MATERIALIZED VIEW IF EXISTS clingen.v_actionability_latest;
CREATE MATERIALIZED VIEW clingen.v_actionability_latest AS
SELECT DISTINCT ON (
  cohort,
  COALESCE(NULLIF(hgnc_id,''), NULLIF(gene_symbol,'')),
  COALESCE(NULLIF(disease_mondo_id,''), NULLIF(disease_name,'')),
  domain
)
  cohort, gene_symbol, hgnc_id, disease_name, disease_mondo_id,
  assertion, assertion_type, domain, intervention, outcome,
  score, rationale, report_date, source_url
FROM clingen.actionability_assertions
ORDER BY
  cohort,
  COALESCE(NULLIF(hgnc_id,''), NULLIF(gene_symbol,'')),
  COALESCE(NULLIF(disease_mondo_id,''), NULLIF(disease_name,'')),
  domain,
  report_date DESC NULLS LAST;

CREATE UNIQUE INDEX IF NOT EXISTS v_actionability_latest_uniq
  ON clingen.v_actionability_latest (cohort, gene_symbol, hgnc_id, disease_name, disease_mondo_id, domain, report_date);
