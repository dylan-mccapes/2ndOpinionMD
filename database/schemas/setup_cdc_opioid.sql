-- 2.1 Raw docs + normalized sections
CREATE SCHEMA IF NOT EXISTS guidelines;

CREATE TABLE IF NOT EXISTS guidelines.cdc_docs (
  doc_id         bigserial PRIMARY KEY,
  source_key     text NOT NULL,        -- 'cdc_opioid'
  slug           text NOT NULL,        -- 'mmwr_2022_full', 'pdmp', 'recommendations', ...
  url            text NOT NULL,
  title          text NOT NULL,
  pub_date       date,
  fetched_at     timestamptz NOT NULL DEFAULT now(),
  raw_html       text,
  raw_pdf        bytea,                -- if we capture PDF bytes
  checksum       text
);
CREATE UNIQUE INDEX IF NOT EXISTS cdc_docs_slug_idx ON guidelines.cdc_docs(source_key, slug);

CREATE TABLE IF NOT EXISTS guidelines.cdc_sections (
  section_id     bigserial PRIMARY KEY,
  doc_id         bigint NOT NULL REFERENCES guidelines.cdc_docs(doc_id) ON DELETE CASCADE,
  anchor         text,                 -- '#rec-01' etc.
  heading        text,
  section_order  int NOT NULL DEFAULT 0,
  text_plain     text NOT NULL,
  text_html      text,
  rec_number     text,                 -- 'Rec 1', 'Rec 2', ... when applicable
  tags           text[] DEFAULT '{}',  -- e.g., '{pdmp, linkage_to_care, tapering}'
  created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS cdc_sections_doc_idx ON guidelines.cdc_sections(doc_id);
CREATE INDEX IF NOT EXISTS cdc_sections_tags_idx ON guidelines.cdc_sections USING gin(tags);

-- 2.2 Structured “rules” (JSON) to gate RAG and power care-journey UX
CREATE TABLE IF NOT EXISTS guidelines.cdc_opioid_rules (
  rule_id        bigserial PRIMARY KEY,
  rec_number     text,                 -- 'R1'..'R12' or NULL if non-recommendation
  title          text,
  rule_json      jsonb NOT NULL,       -- JSON-logic: { "all": [ {">=": [{"var":"age"},18]}, ... ] }
  strength       text,                 -- Optional: 'guiding_principle'|'recommendation'
  tags           text[] DEFAULT '{}',  -- e.g., '{acute, chronic, pdmp, naloxone}'
  source_section bigint REFERENCES guidelines.cdc_sections(section_id),
  version        text DEFAULT '2022',
  created_at     timestamptz NOT NULL DEFAULT now()
);

-- 2.3 Push into RAG
-- We reuse public.rag_corpus (already in your stack)
-- Convention: source='cdc_opioid'
-- (No DDL needed if it already exists.)

