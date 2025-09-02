CREATE SCHEMA IF NOT EXISTS ontology;

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS ontology.rxnorm_conso (
  rxcui TEXT,
  lat TEXT,
  ts TEXT,
  lui TEXT,
  stt TEXT,
  sui TEXT,
  ispref TEXT,
  rxaui TEXT PRIMARY KEY,
  saui TEXT,
  scui TEXT,
  sdui TEXT,
  sab TEXT,
  tty TEXT,
  code TEXT,
  str TEXT,
  srl TEXT,
  suppress TEXT,
  cvf TEXT,
  ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS rxnorm_conso_rxcui_idx ON ontology.rxnorm_conso (rxcui);
CREATE INDEX IF NOT EXISTS rxnorm_conso_tty_str_idx ON ontology.rxnorm_conso (tty, str);
CREATE INDEX IF NOT EXISTS rxnorm_conso_str_gin_idx ON ontology.rxnorm_conso USING gin (str gin_trgm_ops);

CREATE TABLE IF NOT EXISTS ontology.rxnorm_rel (
  rxcui1 TEXT,
  rxaui1 TEXT,
  stype1 TEXT,
  rel TEXT,
  rxcui2 TEXT,
  rxaui2 TEXT,
  stype2 TEXT,
  rela TEXT,
  rui TEXT PRIMARY KEY,
  srui TEXT,
  sab TEXT,
  sl TEXT,
  rg TEXT,
  dir TEXT,
  suppress TEXT,
  cvf TEXT,
  ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS rxnorm_rel_rxcui1_idx ON ontology.rxnorm_rel (rxcui1);
CREATE INDEX IF NOT EXISTS rxnorm_rel_rxcui2_idx ON ontology.rxnorm_rel (rxcui2);
CREATE INDEX IF NOT EXISTS rxnorm_rel_rel_idx ON ontology.rxnorm_rel (rel);
CREATE INDEX IF NOT EXISTS rxnorm_rel_rela_idx ON ontology.rxnorm_rel (rela);

CREATE TABLE IF NOT EXISTS ontology.rxnorm_sat (
  rxcui TEXT,
  lui TEXT,
  sui TEXT,
  rxaui TEXT,
  stype TEXT,
  code TEXT,
  atui TEXT PRIMARY KEY,
  satui TEXT,
  atn TEXT,
  sab TEXT,
  atv TEXT,
  suppress TEXT,
  cvf TEXT,
  ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS rxnorm_sat_atn_idx ON ontology.rxnorm_sat (atn);
CREATE INDEX IF NOT EXISTS rxnorm_sat_ndc_idx ON ontology.rxnorm_sat (atn) WHERE atn = 'NDC';

CREATE TABLE IF NOT EXISTS ontology.rxnorm_ndc (
  ndc_norm TEXT,
  ndc_raw TEXT,
  rxcui TEXT,
  atui TEXT,
  sab TEXT,
  PRIMARY KEY(ndc_norm, rxcui),
  ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS rxnorm_ndc_norm_idx ON ontology.rxnorm_ndc (ndc_norm);
CREATE INDEX IF NOT EXISTS rxnorm_ndc_rxcui_idx ON ontology.rxnorm_ndc (rxcui);
CREATE INDEX IF NOT EXISTS rxnorm_conso_label_pick_idx ON ontology.rxnorm_conso (rxcui, sab, ispref, tty, str);
