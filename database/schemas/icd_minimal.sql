-- Create schemas/tables only if missing (no drops).
CREATE SCHEMA IF NOT EXISTS ontology;

-- --- ICD-10-CM (minimal) ---
DO $$
BEGIN
  IF to_regclass('ontology.icd10cm') IS NULL THEN
    CREATE TABLE ontology.icd10cm (
      code            text PRIMARY KEY,
      title           text,
      long_description text
    );
    CREATE INDEX ON ontology.icd10cm (code);
  END IF;
END$$;

-- --- ICD-11 (minimal) ---
DO $$
BEGIN
  IF to_regclass('ontology.icd11') IS NULL THEN
    CREATE TABLE ontology.icd11 (
      code           text PRIMARY KEY,
      title          text,
      definition     text,
      parent_code    text,
      chapter        text,
      section        text,
      class_kind     text,
      foundation_uri text,
      linearization_uri text,
      depth          int
    );
    CREATE INDEX ON ontology.icd11 (code);
    CREATE INDEX ON ontology.icd11 (parent_code);
  END IF;
END$$;

