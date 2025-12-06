CREATE SCHEMA IF NOT EXISTS clingen;

-- Core summary (what your routes file reads)
CREATE TABLE IF NOT EXISTS clingen.actionability_summary (
  cohort                  text NOT NULL,             -- 'Adult' | 'Pediatric'
  gene_symbol             text,
  hgnc_id                 text,
  disease_name            text,
  disease_mondo_id        text,
  actionability_assertion text,
  report_date             date,
  source_url              text,
  loaded_at               timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS clingen_act_sum_cohort_gene_idx
  ON clingen.actionability_summary (cohort, gene_symbol);
CREATE INDEX IF NOT EXISTS clingen_act_sum_mondo_idx
  ON clingen.actionability_summary (disease_mondo_id);

-- Minimal “quick” matview so /quick works immediately
CREATE MATERIALIZED VIEW IF NOT EXISTS clingen.v_actionability_quick AS
SELECT
  cohort,
  gene_symbol,
  hgnc_id,
  disease_name,
  disease_mondo_id,
  -- stable-ish composite key
  (cohort || '|' || COALESCE(gene_symbol,'') || '|' || COALESCE(disease_mondo_id,'')) AS disease_key,
  actionability_assertion,
  NULL::int  AS score,          -- placeholder, pending scoring source
  NULL::text AS evidence_type,  -- placeholder
  report_date
FROM clingen.actionability_summary;

-- Unique index so your /refresh endpoint can CONCURRENTLY refresh
CREATE UNIQUE INDEX IF NOT EXISTS v_actionability_quick_uniq
  ON clingen.v_actionability_quick (cohort, gene_symbol, disease_mondo_id, report_date);
