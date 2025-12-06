-- VA/DoD guidelines: docs + sections
CREATE SCHEMA IF NOT EXISTS guidelines;

-- Docs (one per PDF/page)
CREATE TABLE IF NOT EXISTS guidelines.va_docs (
  id          BIGSERIAL PRIMARY KEY,
  slug        TEXT UNIQUE NOT NULL,                -- e.g., 'va_bzd_taper_clinician'
  url         TEXT NOT NULL,
  title       TEXT,
  raw_html    TEXT,                                -- for html pages (if any)
  raw_pdf     BYTEA,                               -- for PDFs
  text_plain  TEXT,                                -- optional denormalized full text
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS va_docs_slug_idx ON guidelines.va_docs(slug);

-- Sections (chunked from pdf/html)
CREATE TABLE IF NOT EXISTS guidelines.va_sections (
  section_id  BIGSERIAL PRIMARY KEY,
  doc_slug    TEXT NOT NULL REFERENCES guidelines.va_docs(slug) ON DELETE CASCADE,
  heading     TEXT,
  text_plain  TEXT NOT NULL,
  tags        TEXT[] DEFAULT '{}',
  rec_number  TEXT,                                -- optional (if we detect explicit “Recommendation x”)
  ts          TSVECTOR
);

CREATE INDEX IF NOT EXISTS va_sections_doc_idx  ON guidelines.va_sections(doc_slug);
CREATE INDEX IF NOT EXISTS va_sections_tags_idx ON guidelines.va_sections USING GIN (tags);
CREATE INDEX IF NOT EXISTS va_sections_fts_idx  ON guidelines.va_sections USING GIN (ts);

