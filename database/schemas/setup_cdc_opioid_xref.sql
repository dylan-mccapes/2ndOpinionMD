-- Cross-indexing for CDC opioid sections → standard codes
-- Creates a mapping table + a convenience view.

CREATE TABLE IF NOT EXISTS guidelines.section_code_map (
  section_id   bigint NOT NULL REFERENCES guidelines.cdc_sections(section_id) ON DELETE CASCADE,
  system       text   NOT NULL,                -- 'SNOMED','ICD-10-CM','HPO','RxNorm', etc.
  code         text   NOT NULL,
  display      text,                           -- human label for UI
  how_derived  text   NOT NULL,                -- 'curated','auto_ner','lex_map','ontology_join'
  confidence   numeric CHECK (confidence BETWEEN 0 AND 1),
  PRIMARY KEY (section_id, system, code)
);

CREATE INDEX IF NOT EXISTS section_code_map_system_code_idx
  ON guidelines.section_code_map (system, code);

CREATE OR REPLACE VIEW guidelines.v_cdc_section_codes AS
SELECT s.section_id,
       s.heading,
       s.tags,
       m.system,
       m.code,
       m.display,
       m.how_derived,
       m.confidence
FROM guidelines.cdc_sections s
JOIN guidelines.section_code_map m USING (section_id);

