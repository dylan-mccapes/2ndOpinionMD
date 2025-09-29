-- database/schemas/setup_disgenet_schema.sql
BEGIN;

CREATE SCHEMA IF NOT EXISTS molecular;

-- Ensure table exists
CREATE TABLE IF NOT EXISTS molecular.disgenet_associations (
  assoc_id text  -- will be constrained unique (partial) below
);

-- Add any missing columns (safe to re-run)
ALTER TABLE molecular.disgenet_associations
  ADD COLUMN IF NOT EXISTS gene_ncbi_id integer,
  ADD COLUMN IF NOT EXISTS gene_symbol text,
  ADD COLUMN IF NOT EXISTS gene_ncbi_type text,
  ADD COLUMN IF NOT EXISTS gene_ensembl_ids text[],
  ADD COLUMN IF NOT EXISTS gene_dsi numeric,
  ADD COLUMN IF NOT EXISTS gene_dpi numeric,
  ADD COLUMN IF NOT EXISTS disease_name text,
  ADD COLUMN IF NOT EXISTS disease_type text,
  ADD COLUMN IF NOT EXISTS disease_umls_cui text,
  ADD COLUMN IF NOT EXISTS disease_vocabularies text[],
  ADD COLUMN IF NOT EXISTS disease_classes_do text[],
  ADD COLUMN IF NOT EXISTS disease_classes_hpo text[],
  ADD COLUMN IF NOT EXISTS disease_classes_msh text[],
  ADD COLUMN IF NOT EXISTS disease_classes_umls_st text[],
  ADD COLUMN IF NOT EXISTS disease_inheritance text,
  ADD COLUMN IF NOT EXISTS disease_prevalence_class text,
  ADD COLUMN IF NOT EXISTS disease_prevalence_geo_area text,
  ADD COLUMN IF NOT EXISTS disease_prevalence_type text,
  ADD COLUMN IF NOT EXISTS score numeric,
  ADD COLUMN IF NOT EXISTS num_pmids integer,
  ADD COLUMN IF NOT EXISTS num_ctsupporting_association integer,
  ADD COLUMN IF NOT EXISTS num_chems_included_in_evidences integer,
  ADD COLUMN IF NOT EXISTS num_pmids_with_chems_included_in_evidences integer,
  ADD COLUMN IF NOT EXISTS number_chems_filtered integer,
  ADD COLUMN IF NOT EXISTS number_pmids_with_chems_filtered integer,
  ADD COLUMN IF NOT EXISTS ei numeric,
  ADD COLUMN IF NOT EXISTS el text,
  ADD COLUMN IF NOT EXISTS year_initial integer,
  ADD COLUMN IF NOT EXISTS year_final integer;

-- Indexes
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Unique on assoc_id but allow legacy NULLs
CREATE UNIQUE INDEX IF NOT EXISTS disgenet_assoc_id_uidx
  ON molecular.disgenet_associations (assoc_id)
  WHERE assoc_id IS NOT NULL;

-- Helpful search indexes
CREATE INDEX IF NOT EXISTS disgenet_gene_sym_trgm
  ON molecular.disgenet_associations USING gin (gene_symbol gin_trgm_ops);

CREATE INDEX IF NOT EXISTS disgenet_dis_name_trgm
  ON molecular.disgenet_associations USING gin (disease_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS disgenet_gene_ncbi_id_idx
  ON molecular.disgenet_associations (gene_ncbi_id);

CREATE INDEX IF NOT EXISTS disgenet_score_idx
  ON molecular.disgenet_associations (score);

COMMIT;

