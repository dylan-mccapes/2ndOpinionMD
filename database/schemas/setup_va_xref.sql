-- Per-VA mapping table
CREATE TABLE IF NOT EXISTS guidelines.va_section_code_map (
  section_id  BIGINT NOT NULL,         -- FK-ish to guidelines.va_sections.section_id (no hard FK for flexibility)
  system      TEXT   NOT NULL,         -- 'SNOMED' | 'ICD10' | 'RxNorm' | 'LOINC' | etc.
  code        TEXT   NOT NULL,
  display     TEXT,
  how_derived TEXT DEFAULT 'curated',
  confidence  NUMERIC DEFAULT 0.9,
  PRIMARY KEY (section_id, system, code)
);

CREATE INDEX IF NOT EXISTS va_section_code_map_sys_code_idx
  ON guidelines.va_section_code_map(system, code);

-- View joining mappings to VA sections for quick browse
CREATE OR REPLACE VIEW guidelines.v_va_section_codes AS
SELECT s.section_id, s.heading, s.tags,
       m.system, m.code, m.display, m.how_derived, m.confidence
FROM guidelines.va_sections s
JOIN guidelines.va_section_code_map m USING (section_id);

