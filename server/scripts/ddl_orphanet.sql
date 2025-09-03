CREATE SCHEMA IF NOT EXISTS ontology;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS ontology.orphanet_diseases (
  orpha_code       INTEGER PRIMARY KEY,
  name             TEXT NOT NULL,
  disorder_type    TEXT,
  definition       TEXT,
  prevalence_note  TEXT,
  inheritance_note TEXT,
  ingested_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS orphanet_diseases_name_trgm
  ON ontology.orphanet_diseases USING gin (name gin_trgm_ops);

CREATE TABLE IF NOT EXISTS ontology.orphanet_synonyms (
  orpha_code INTEGER NOT NULL,
  synonym    TEXT NOT NULL,
  lang       TEXT,
  PRIMARY KEY(orpha_code, synonym, COALESCE(lang,'')),
  FOREIGN KEY(orpha_code) REFERENCES ontology.orphanet_diseases(orpha_code) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS orphanet_synonyms_syn_trgm
  ON ontology.orphanet_synonyms USING gin (synonym gin_trgm_ops);

CREATE TABLE IF NOT EXISTS ontology.orphanet_external_refs (
  orpha_code INTEGER NOT NULL,
  source     TEXT NOT NULL,
  ref        TEXT NOT NULL,
  PRIMARY KEY(orpha_code, source, ref),
  FOREIGN KEY(orpha_code) REFERENCES ontology.orphanet_diseases(orpha_code) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS orphanet_xref_source_ref_idx
  ON ontology.orphanet_external_refs (source, ref);

CREATE TABLE IF NOT EXISTS ontology.orphanet_gene_links (
  orpha_code      INTEGER NOT NULL,
  gene_symbol     TEXT,
  entrez_id       TEXT,
  ensembl_id      TEXT,
  association     TEXT,  -- e.g., disease-causing, modifier
  inheritance     TEXT,
  evidence        TEXT,
  PRIMARY KEY(orpha_code, COALESCE(gene_symbol,''), COALESCE(entrez_id,''), COALESCE(ensembl_id,''), COALESCE(association,'')),
  FOREIGN KEY(orpha_code) REFERENCES ontology.orphanet_diseases(orpha_code) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS orphanet_gene_symbol_idx ON ontology.orphanet_gene_links (gene_symbol);

CREATE TABLE IF NOT EXISTS ontology.orphanet_phenotype_links (
  orpha_code   INTEGER NOT NULL,
  hpo_id       TEXT NOT NULL,   -- e.g., HP:0000001
  hpo_label    TEXT,
  frequency    TEXT,            -- e.g., Frequent, Occasional, %, etc.
  diagnostic   BOOLEAN,         -- diagnostic criterion flag if present
  negated      BOOLEAN,         -- if explicitly excluded
  PRIMARY KEY(orpha_code, hpo_id),
  FOREIGN KEY(orpha_code) REFERENCES ontology.orphanet_diseases(orpha_code) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS orphanet_phenotype_hpo_idx ON ontology.orphanet_phenotype_links (hpo_id);
