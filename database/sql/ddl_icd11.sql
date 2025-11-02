
CREATE TABLE IF NOT EXISTS ontology.icd11 (
  code TEXT NOT NULL,
  title TEXT,
  definition TEXT,
  parent_code TEXT,
  foundation BOOLEAN DEFAULT FALSE,
  linearization TEXT NOT NULL DEFAULT 'mms',
  release TEXT NOT NULL,
  effective_year INT,
  source_file TEXT,
  PRIMARY KEY (code, release, linearization)
);

CREATE INDEX IF NOT EXISTS icd11_parent_idx ON ontology.icd11(parent_code);

CREATE INDEX IF NOT EXISTS icd11_release_idx ON ontology.icd11(release);

CREATE INDEX IF NOT EXISTS icd11_linearization_idx ON ontology.icd11(linearization);

CREATE INDEX IF NOT EXISTS icd11_release_linearization_idx ON ontology.icd11(release, linearization);

COMMENT ON TABLE ontology.icd11 IS 'ICD-11 MMS (Mortality and Morbidity Statistics) linearization from WHO API v2';
COMMENT ON COLUMN ontology.icd11.code IS 'ICD-11 code (e.g., 1A00, 1A00.0)';
COMMENT ON COLUMN ontology.icd11.title IS 'Entity title';
COMMENT ON COLUMN ontology.icd11.definition IS 'Entity definition';
COMMENT ON COLUMN ontology.icd11.parent_code IS 'Parent code for hierarchy';
COMMENT ON COLUMN ontology.icd11.foundation IS 'Whether this is a foundation entity';
COMMENT ON COLUMN ontology.icd11.linearization IS 'Linearization type (mms, etc.)';
COMMENT ON COLUMN ontology.icd11.release IS 'Release version (e.g., 2024-01)';
COMMENT ON COLUMN ontology.icd11.effective_year IS 'Effective year';
COMMENT ON COLUMN ontology.icd11.source_file IS 'Source file or API endpoint';
