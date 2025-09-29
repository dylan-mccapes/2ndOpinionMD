CREATE SCHEMA IF NOT EXISTS ontology;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Core diseases table
CREATE TABLE IF NOT EXISTS ontology.orphanet_diseases (
  orpha_code   TEXT PRIMARY KEY,                -- canonical "ORPHA:803"
  orpha_num    INTEGER,                         -- numeric 803
  name         TEXT NOT NULL,
  disorder_type TEXT,
  definition   TEXT,
  status       TEXT,
  expert_link  TEXT,
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS orphanet_diseases_name_trgm
  ON ontology.orphanet_diseases USING gin (name gin_trgm_ops);

-- Synonyms: make nullable fields NOT NULL with default '' so they can be in PK
CREATE TABLE IF NOT EXISTS ontology.orphanet_synonyms (
  orpha_code TEXT NOT NULL REFERENCES ontology.orphanet_diseases(orpha_code) ON DELETE CASCADE,
  synonym    TEXT NOT NULL,
  lang       TEXT NOT NULL DEFAULT '',
  scope      TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (orpha_code, synonym, lang, scope)
);

CREATE INDEX IF NOT EXISTS orphanet_synonyms_syn_trgm
  ON ontology.orphanet_synonyms USING gin (synonym gin_trgm_ops);

-- External refs
CREATE TABLE IF NOT EXISTS ontology.orphanet_external_refs (
  orpha_code TEXT NOT NULL REFERENCES ontology.orphanet_diseases(orpha_code) ON DELETE CASCADE,
  source     TEXT NOT NULL,
  ref        TEXT NOT NULL,
  url        TEXT,
  PRIMARY KEY (orpha_code, source, ref)
);

CREATE INDEX IF NOT EXISTS orphanet_xref_source_ref_idx
  ON ontology.orphanet_external_refs (source, ref);

-- Gene links: make association_type NOT NULL with default '' for PK
CREATE TABLE IF NOT EXISTS ontology.orphanet_gene_links (
  orpha_code       TEXT NOT NULL REFERENCES ontology.orphanet_diseases(orpha_code) ON DELETE CASCADE,
  gene_symbol      TEXT NOT NULL,
  entrez_id        TEXT,
  ensembl_id       TEXT,
  association_type TEXT NOT NULL DEFAULT '',
  inheritance      TEXT,
  evidence         TEXT,
  PRIMARY KEY (orpha_code, gene_symbol, association_type)
);

CREATE INDEX IF NOT EXISTS orphanet_gene_symbol_idx
  ON ontology.orphanet_gene_links (gene_symbol);

-- Phenotype links (HPO)
CREATE TABLE IF NOT EXISTS ontology.orphanet_phenotype_links (
  orpha_code  TEXT NOT NULL REFERENCES ontology.orphanet_diseases(orpha_code) ON DELETE CASCADE,
  hpo_id      TEXT NOT NULL,      -- e.g. HP:0001250
  hpo_label   TEXT,
  frequency   TEXT,
  diagnostic  BOOLEAN,
  negated     BOOLEAN,
  PRIMARY KEY (orpha_code, hpo_id)
);

CREATE INDEX IF NOT EXISTS orphanet_phenotype_hpo_idx
  ON ontology.orphanet_phenotype_links (hpo_id);

