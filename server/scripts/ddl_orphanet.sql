CREATE SCHEMA IF NOT EXISTS ontology;

CREATE TABLE IF NOT EXISTS ontology.orphanet_diseases (
  orpha_code        TEXT PRIMARY KEY,        -- store canonical "ORPHA:803"
  orpha_num         INTEGER,                 -- numeric 803
  name              TEXT NOT NULL,
  disorder_type     TEXT,                    -- e.g., "Clinical entity"
  definition        TEXT,
  status            TEXT,                    -- e.g., "Active"
  expert_link       TEXT,                    -- Orphanet expert link if present
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ontology.orphanet_synonyms (
  orpha_code  TEXT REFERENCES ontology.orphanet_diseases(orpha_code) ON DELETE CASCADE,
  synonym     TEXT NOT NULL,
  lang        TEXT,                          -- e.g., "en", "fr"
  scope       TEXT,                          -- e.g., "preferred", "exact", "alt" if available
  PRIMARY KEY (orpha_code, synonym, COALESCE(lang, ''), COALESCE(scope,''))
);

CREATE TABLE IF NOT EXISTS ontology.orphanet_external_refs (
  orpha_code  TEXT REFERENCES ontology.orphanet_diseases(orpha_code) ON DELETE CASCADE,
  source      TEXT NOT NULL,                 -- e.g., "OMIM", "ICD10", "MeSH", "UMLS"
  ref         TEXT NOT NULL,
  url         TEXT,
  PRIMARY KEY (orpha_code, source, ref)
);

CREATE TABLE IF NOT EXISTS ontology.orphanet_gene_links (
  orpha_code        TEXT REFERENCES ontology.orphanet_diseases(orpha_code) ON DELETE CASCADE,
  gene_symbol       TEXT NOT NULL,
  entrez_id         TEXT,
  ensembl_id        TEXT,
  association_type  TEXT,                    -- e.g., "Disease-causing mutation", "Susceptibility"
  inheritance       TEXT,                    -- if present
  evidence          TEXT,                    -- if present
  PRIMARY KEY (orpha_code, gene_symbol, COALESCE(association_type,''))
);

CREATE TABLE IF NOT EXISTS ontology.orphanet_phenotype_links (
  orpha_code    TEXT REFERENCES ontology.orphanet_diseases(orpha_code) ON DELETE CASCADE,
  hpo_id        TEXT NOT NULL,               -- e.g., "HP:0001250"
  hpo_label     TEXT,
  frequency     TEXT,                        -- normalized string (Very frequent, Frequent, etc.)
  diagnostic    BOOLEAN,                     -- if marked as diagnostic criterion
  negated       BOOLEAN,                     -- if explicitly excluded
  PRIMARY KEY (orpha_code, hpo_id)
);

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS orphanet_dis_name_trgm ON ontology.orphanet_diseases USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS orphanet_syn_syn_trgm  ON ontology.orphanet_synonyms USING gin (synonym gin_trgm_ops);
CREATE INDEX IF NOT EXISTS orphanet_gene_symbol_idx ON ontology.orphanet_gene_links (gene_symbol);
