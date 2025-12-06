-- VA/DOD cross-indexing table + view

CREATE TABLE IF NOT EXISTS guidelines.va_section_code_map (
    section_id   INTEGER NOT NULL
        REFERENCES guidelines.va_sections(section_id) ON DELETE CASCADE,
    system       TEXT    NOT NULL,  -- e.g., SNOMED | RxNorm | ICD10CM | ICD11 | LOINC
    code         TEXT    NOT NULL,
    display      TEXT,
    how_derived  TEXT    DEFAULT 'curated',
    confidence   NUMERIC(3,2) DEFAULT 0.90,
    CONSTRAINT va_section_code_map_pkey PRIMARY KEY (section_id, system, code)
);

CREATE INDEX IF NOT EXISTS va_section_code_map_system_code_idx
  ON guidelines.va_section_code_map (system, code);

-- Keep column names/order stable to avoid replacement errors
DROP VIEW IF EXISTS guidelines.v_va_section_codes;
CREATE VIEW guidelines.v_va_section_codes AS
SELECT
    s.section_id,
    s.heading,
    s.tags,
    m.system,
    m.code,
    m.display,
    m.how_derived,
    m.confidence
FROM guidelines.va_sections s
JOIN guidelines.va_section_code_map m
  ON m.section_id = s.section_id;

