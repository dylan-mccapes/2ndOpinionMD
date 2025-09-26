-- database/schemas/molecular_gwas_schema.sql

BEGIN;

-- Extensions (safe if already installed)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Schema
CREATE SCHEMA IF NOT EXISTS molecular;

-- Main table: GWAS associations filtered to autoimmune traits
CREATE TABLE IF NOT EXISTS molecular.gwas_hits (
  id BIGSERIAL PRIMARY KEY,
  study_accession           TEXT,
  pubmed_id                 TEXT,
  disease_trait             TEXT,
  mapped_trait              TEXT,
  mapped_trait_uri          TEXT,
  snps                      TEXT,
  strongest_snp_risk_allele TEXT,
  p_value                   DOUBLE PRECISION,
  or_beta                   TEXT,
  ci_95                     TEXT,
  risk_allele_frequency     TEXT,
  reported_genes            TEXT,
  mapped_gene               TEXT,
  chr                       TEXT,
  chr_pos                   BIGINT,
  initial_sample_size       TEXT,
  replication_sample_size   TEXT,
  date_added                DATE,
  raw                       JSONB
);

-- Natural de-dup (expression-based): tolerate NULLs by coalescing to ''
CREATE UNIQUE INDEX IF NOT EXISTS gwas_hits_nat_uniq
  ON molecular.gwas_hits (
    COALESCE(study_accession,''), COALESCE(snps,''), COALESCE(disease_trait,'')
  );

-- Helpful indexes
CREATE INDEX IF NOT EXISTS gwas_trait_trgm
  ON molecular.gwas_hits USING gin (disease_trait gin_trgm_ops);

CREATE INDEX IF NOT EXISTS gwas_mapped_trait_trgm
  ON molecular.gwas_hits USING gin (mapped_trait gin_trgm_ops);

CREATE INDEX IF NOT EXISTS gwas_snps_idx
  ON molecular.gwas_hits (snps);

CREATE INDEX IF NOT EXISTS gwas_pval_idx
  ON molecular.gwas_hits (p_value);

CREATE INDEX IF NOT EXISTS gwas_date_added_idx
  ON molecular.gwas_hits (date_added);

-- Optional: raw studies “catch-all” table for provenance
CREATE TABLE IF NOT EXISTS molecular.gwas_studies_raw (
  id BIGSERIAL PRIMARY KEY,
  line JSONB NOT NULL
);

COMMIT;

