-- Text search index for CDC sections (lexical search performance)
CREATE INDEX IF NOT EXISTS cdc_sections_text_gin
ON guidelines.cdc_sections
USING GIN (to_tsvector('english', text_plain));

